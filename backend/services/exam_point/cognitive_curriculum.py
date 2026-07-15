"""课标/考纲对齐的设问技能纠正 — 补教辅 explicit_label 把态度粗并入推断/细节的缺口.

真相源层级:
  1) 官方7技能定义 (exam_point_taxonomy.yaml / 陈康等2019)
  2) cognitive_skill_curriculum_rules.yaml 题干操作化判据
  3) cognitive_curriculum_labels.jsonl 人工核验后的逐题 curated 纠正

不做: 无题干证据自动把四选一改标为结构; 结构桶由七选五 task 映射承载 (见 cognitive_seven_choose_five.py)。
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import duckdb
import yaml

from backend.services.lineage import stamp

ROOT = Path(__file__).resolve().parents[3]
_RULES = ROOT / "backend" / "config" / "cognitive_skill_curriculum_rules.yaml"
_LABELS = ROOT / "data" / "structured" / "exam_point" / "cognitive_curriculum_labels.jsonl"
DIMENSION = "cognitive_skill"
PROVENANCE = "curriculum_aligned_stem"


@lru_cache(maxsize=1)
def _load_rules() -> dict:
    return yaml.safe_load(_RULES.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def load_curriculum_labels() -> dict[str, dict]:
    """src_id → curated row. 加载时用 rules 校验 stem 命中目标技能, 防 drift."""
    rules = (_load_rules().get("skills") or {})
    out: dict[str, dict] = {}
    for ln in _LABELS.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        skill, stem = row["skill"], row["stem"]
        pats = (rules.get(skill) or {}).get("stem_any") or []
        if not any(re.search(p, stem) for p in pats):
            raise ValueError(
                f"curriculum label {row['src_id']}: stem 未命中 rules[{skill}].stem_any — {stem!r}"
            )
        out[row["src_id"]] = row
    return out


def skill_for(src_id: str) -> str | None:
    row = load_curriculum_labels().get(src_id)
    return row["skill"] if row else None


def apply_curriculum_overrides(con: duckdb.DuckDBPyConnection) -> dict:
    """对已入图子题: 删旧 cognitive_skill 边, 写入课标对齐边 (每子题一技能)."""
    labels = load_curriculum_labels()
    n_replaced = n_missing_node = 0
    for src_id, row in labels.items():
        qnode = f"question:{src_id}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [qnode]).fetchone():
            n_missing_node += 1
            continue
        skill = row["skill"]
        pnode = f"exam_point:{DIMENSION}:{skill}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [pnode]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [pnode, "exam_point", skill, json.dumps({"dimension": DIMENSION}, ensure_ascii=False)],
            )
        con.execute(
            "DELETE FROM edges WHERE src_id=? AND relation='tests_exam_point' "
            "AND json_extract_string(evidence_json,'$.dimension')=?",
            [qnode, DIMENSION],
        )
        year = int(row["year"])
        lineage = stamp(
            con, source_year=year, source_qid=src_id, provenance=PROVENANCE,
            derived_by="cognitive_curriculum@v1",
            version_kinds={"exam_paper": "liaoning_gaokao", "curriculum": "gaozhong"},
        )
        evidence = {
            "dimension": DIMENSION,
            "provenance": PROVENANCE,
            "prior_analysis_label": row.get("prior_analysis_label"),
            "prior_skill": row.get("prior_skill"),
            "stem": row.get("stem"),
            "curriculum_ref": row.get("curriculum_ref"),
            "exam_stage": "gaokao",
            "lineage": lineage,
        }
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
            [qnode, pnode, "tests_exam_point", 1.0, json.dumps(evidence, ensure_ascii=False)],
        )
        n_replaced += 1
    return {"curriculum_overrides": n_replaced, "missing_question_node": n_missing_node,
            "n_labels": len(labels)}
