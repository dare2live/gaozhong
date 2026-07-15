"""text_continuity 冷启动 — 课标连续/非连续语篇标注.

curated jsonl → tests_exam_point dimension=text_continuity;
provenance ∈ {agent_curriculum_verified, human_curriculum_verified}.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
_CURATED = ROOT / "data/structured/exam_point/text_continuity_labels.jsonl"
DIM = "text_continuity"
LABELS = frozenset({"连续性文本", "非连续性文本"})
PROV_OK = frozenset({"agent_curriculum_verified", "human_curriculum_verified"})
REL = "tests_exam_point"


def _load() -> list[dict]:
    if not _CURATED.exists():
        return []
    out = []
    for ln in _CURATED.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


def load_text_continuity(con: duckdb.DuckDBPyConnection) -> dict:
    """替换 dim=text_continuity 边; 保证官方 L2 节点存在."""
    curated = _load()
    con.execute(
        "DELETE FROM edges WHERE relation=? "
        "AND json_extract_string(evidence_json,'$.dimension')=?",
        [REL, DIM],
    )
    for lab in LABELS:
        cid = f"exam_point:{DIM}:{lab}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?,?,?,?)",
                [
                    cid,
                    "exam_point",
                    lab,
                    json.dumps({"dimension": DIM}, ensure_ascii=False),
                ],
            )
    n_ok = n_skip = 0
    for row in curated:
        qid = row.get("question_id")
        lab = row.get("label") or row.get("text_continuity")
        prov = row.get("method") or row.get("provenance") or "agent_curriculum_verified"
        if not qid or lab not in LABELS or prov not in PROV_OK:
            n_skip += 1
            continue
        src = f"question:{qid}"
        if not con.execute(
            "SELECT 1 FROM nodes WHERE concept_id=? AND node_type='question'", [src]
        ).fetchone():
            n_skip += 1
            continue
        dst = f"exam_point:{DIM}:{lab}"
        ev = {
            "dimension": DIM,
            "provenance": prov,
            "truth_source": "curriculum_text_continuity",
            "note": row.get("note"),
        }
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?,?,?,?,?)",
            [src, dst, REL, 1.0, json.dumps(ev, ensure_ascii=False)],
        )
        n_ok += 1
    return {
        "dimension": DIM,
        "n_curated": len(curated),
        "n_edges": n_ok,
        "n_skipped": n_skip,
        "provenance_allowlist": sorted(PROV_OK),
    }


def text_continuity_summary(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT SUBSTR(dst_id, LENGTH(?) + 1) AS lab, "
        "json_extract_string(evidence_json,'$.provenance') AS prov, COUNT(*) "
        "FROM edges WHERE relation=? "
        "AND json_extract_string(evidence_json,'$.dimension')=? "
        "GROUP BY 1, 2 ORDER BY 1, 2",
        [f"exam_point:{DIM}:", REL, DIM],
    ).fetchall()
    n = sum(r[2] for r in rows)
    bad_prov = [r for r in rows if r[1] not in PROV_OK]
    return {
        "n_edges": n,
        "by_label_prov": [{"label": a, "provenance": b, "n": c} for a, b, c in rows],
        "pass": n > 0 and not bad_prov,
        "min_expected": 1,
    }
