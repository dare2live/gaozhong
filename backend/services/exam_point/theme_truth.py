"""Theme 交叉验证诚实披露 + 人工课标核验升档.

- analysis 显式「主题/话题是…」仍≈0 → 不走 analysis cross_verified
- human_curriculum_verified: 人工对照语篇内容 × 课标10主题群, curated jsonl 升档
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
_CURATED = ROOT / "data/structured/exam_point/theme_human_verified.jsonl"
_THEME_EXPLICIT_RE = re.compile(
    r"(?:本文|文章|本篇)?(?:的)?(?:主题|话题)(?:是|为|：|:)\s*([^\n。；;]{2,40})"
)
_OFFICIAL_L2 = frozenset({
    "生活与学习", "做人与做事", "社会服务与人际沟通", "文学、艺术与体育",
    "历史、社会与文化", "科学与技术", "自然生态", "环境保护", "灾害防范", "宇宙探索",
})
PROV_HUMAN = "human_curriculum_verified"


def _curated() -> dict[str, dict]:
    if not _CURATED.exists():
        return {}
    out = {}
    for ln in _CURATED.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            out[r["question_id"]] = r
    return out


def analysis_theme_crosscheck(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT question_id, analysis FROM exam_questions "
        "WHERE province LIKE '辽宁%' AND analysis IS NOT NULL AND TRIM(analysis) <> ''"
    ).fetchall()
    n_explicit = sum(1 for _, a in rows if _THEME_EXPLICIT_RE.search(a or ""))
    n_theme = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json, '$.dimension') = 'theme_l2'"
    ).fetchone()[0]
    n_cross = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json, '$.dimension') = 'theme_l2' "
        "AND json_extract_string(evidence_json, '$.provenance') = 'cross_verified'"
    ).fetchone()[0]
    n_human = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json, '$.dimension') = 'theme_l2' "
        f"AND json_extract_string(evidence_json, '$.provenance') = '{PROV_HUMAN}'"
    ).fetchone()[0]
    # 诚实: 不许假 analysis-cross; 人工核验≥15 即达标
    ok = (n_cross == 0) and (n_human >= 15 or n_human == 0)
    # 若已有人工核验则必须 ≥15
    if n_human > 0:
        ok = n_cross == 0 and n_human >= 15
    status = "human_verified_partial" if n_human else "dual_model_only"
    if n_human >= 15:
        status = "human_curriculum_verified"
    return {
        "n_analysis_with_any_text": len(rows),
        "n_analysis_explicit_theme": n_explicit,
        "n_theme_l2_edges": n_theme,
        "n_cross_verified_edges": n_cross,
        "n_human_verified_edges": n_human,
        "pass": ok,
        "status": status,
        "note": (
            "theme_l2: analysis 无可映射显式主题句故不升 cross_verified; "
            f"人工课标核验 {n_human} 边 (目标≥15). 其余仍 dual_model_agree 方向性."
        ),
    }


def upgrade_human_verified(con: duckdb.DuckDBPyConnection) -> dict:
    """对照 curated jsonl 升档 theme_l2 边 provenance; label 不一致时改挂正确官方 L2 节点."""
    cur = _curated()
    n_ok = n_skip = n_relabel = 0
    for qid, row in cur.items():
        label = row["theme_l2"]
        if label not in _OFFICIAL_L2:
            n_skip += 1
            continue
        src = f"question:{qid}"
        edge = con.execute(
            "SELECT e.dst_id, e.evidence_json, e.weight FROM edges e "
            "WHERE e.src_id=? AND e.relation='tests_exam_point' "
            "AND json_extract_string(e.evidence_json,'$.dimension')='theme_l2'",
            [src],
        ).fetchone()
        if not edge:
            n_skip += 1
            continue
        dst, ev, weight = edge
        edge_label = dst.split("exam_point:theme_l2:")[-1]
        new_dst = f"exam_point:theme_l2:{label}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [new_dst]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [new_dst, "exam_point", label, json.dumps({"dimension": "theme_l2"}, ensure_ascii=False)],
            )
        evj = json.loads(ev or "{}")
        evj["provenance"] = PROV_HUMAN
        evj["truth_source"] = "human_passage_vs_curriculum_theme_l2"
        evj["human_note"] = row.get("note")
        if edge_label != label:
            evj["relabeled_from"] = edge_label
            con.execute(
                "DELETE FROM edges WHERE src_id=? AND relation='tests_exam_point' "
                "AND json_extract_string(evidence_json,'$.dimension')='theme_l2'",
                [src],
            )
            con.execute(
                "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?,?,?,?,?)",
                [src, new_dst, "tests_exam_point", weight or 1.0, json.dumps(evj, ensure_ascii=False)],
            )
            n_relabel += 1
        else:
            con.execute(
                "UPDATE edges SET evidence_json=? WHERE src_id=? AND relation='tests_exam_point' "
                "AND json_extract_string(evidence_json,'$.dimension')='theme_l2'",
                [json.dumps(evj, ensure_ascii=False), src],
            )
        n_ok += 1
    return {"upgraded_or_kept": n_ok, "skipped": n_skip, "relabeled": n_relabel, "curated_n": len(cur)}
