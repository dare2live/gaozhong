"""课标学业质量标准入图 (L1 事实 + 卷级对齐水平二).

真相源: 普通高中英语课程标准(2017/2020) §五 表12-14 + §五(三)考试评价关系.
禁止: 自动建 题目/空 → quality_desc 细边 (判断发明 = theme_l3 同构风险).
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
_DESC = ROOT / "data/structured/curriculum/quality_descriptors.jsonl"
_META = ROOT / "data/structured/curriculum/quality_levels.json"


def load_quality_standards(con: duckdb.DuckDBPyConnection) -> dict:
    meta = json.loads(_META.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in _DESC.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_node = n_edge = 0
    # level nodes
    for lv in meta["levels"]:
        cid = f"quality_level:{lv['level']}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [cid, "quality_level", lv["label"], json.dumps({
                    "level": lv["level"], "exam_role": lv["exam_role"],
                    "curriculum_ref": meta["curriculum_ref"],
                }, ensure_ascii=False)],
            )
            n_node += 1
    # descriptor nodes
    for r in rows:
        cid = f"quality_desc:{r['descriptor_id']}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [cid, "quality_desc", r["descriptor_id"], json.dumps({
                    "quality_level": r["quality_level"], "text": r["text"],
                    "curriculum_ref": r["curriculum_ref"],
                }, ensure_ascii=False)],
            )
            n_node += 1
        parent = f"quality_level:{r['quality_level']}"
        exists = con.execute(
            "SELECT 1 FROM edges WHERE src_id=? AND dst_id=? AND relation='has_descriptor'",
            [parent, cid],
        ).fetchone()
        if not exists:
            con.execute(
                "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?,?,?,?,?)",
                [parent, cid, "has_descriptor", 1.0, json.dumps({
                    "provenance": "curriculum_transcript",
                    "curriculum_ref": r["curriculum_ref"],
                }, ensure_ascii=False)],
            )
            n_edge += 1
    # paper-level: 辽宁新高考II → 水平二 (PDF 显式)
    paper = "exam_scope:liaoning_gaokao_xgkii"
    if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [paper]).fetchone():
        con.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?)",
            [paper, "exam_scope", "辽宁新高考II卷", json.dumps({
                "province": "辽宁", "paper_type": "新高考全国II", "from_year": 2021,
            }, ensure_ascii=False)],
        )
        n_node += 1
    dst = f"quality_level:{meta['gaokao_aligned_level']}"
    if not con.execute(
        "SELECT 1 FROM edges WHERE src_id=? AND dst_id=? AND relation='aligned_to_quality_level'",
        [paper, dst],
    ).fetchone():
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?,?,?,?,?)",
            [paper, dst, "aligned_to_quality_level", 1.0, json.dumps({
                "provenance": "curriculum_explicit",
                "quote": meta["paper_mapping_quote"],
                "curriculum_ref": meta["curriculum_ref"],
                "grain": "paper_era",  # 禁止误读为 per-question
            }, ensure_ascii=False)],
        )
        n_edge += 1
    return {
        "quality_nodes": n_node, "quality_edges": n_edge,
        "n_descriptors": len(rows), "gaokao_level": meta["gaokao_aligned_level"],
    }


def quality_standards_summary(con: duckdb.DuckDBPyConnection) -> dict:
    meta = json.loads(_META.read_text(encoding="utf-8"))
    n_desc = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='quality_desc'"
    ).fetchone()[0]
    n_lvl = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='quality_level'"
    ).fetchone()[0]
    edge = con.execute(
        "SELECT evidence_json FROM edges WHERE relation='aligned_to_quality_level' LIMIT 1"
    ).fetchone()
    return {
        "n_quality_levels": n_lvl,
        "n_descriptors": n_desc,
        "expected_descriptors": meta["n_descriptors"],
        "gaokao_aligned_level": meta["gaokao_aligned_level"],
        "paper_mapping_quote": meta["paper_mapping_quote"],
        "aligned_edge_present": bool(edge),
        "forbid_item_level_edges": True,
        "note": meta["note"],
    }
