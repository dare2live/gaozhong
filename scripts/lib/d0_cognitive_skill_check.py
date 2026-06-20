"""D0 设问类型 cognitive_skill 金矿校验 (KG层 A1; 坑16/坑17, docs/kg_layer_design §5).

锁: 边数对账 authoritative(30 阅读子题, 非拍脑袋数) + 推断≈50%(对账教研解析真相源, 防回退
inference 错估15%) + 全 explicit_label provenance + 全带血缘(version_ids + source_year)。
"""
from __future__ import annotations

import duckdb

_DIM = "json_extract_string(evidence_json,'$.dimension')='cognitive_skill'"


def check_cognitive_skill(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (30) 设问类型 cognitive_skill 金矿 (子题级 explicit_label, 坑16) ===")
    n_edge = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM}").fetchone()[0]
    check("cognitive_skill 边 == 30 (authoritative 阅读子题 explicit_label; 非~29拍脑袋)",
          n_edge == 30, f"{n_edge}")

    from backend.services.exam_point import cognitive_skill_distribution
    allp = [p for pts in cognitive_skill_distribution(con)["by_era"].values() for p in pts]
    tot = sum(p["n"] for p in allp)
    td = sum(p["n"] for p in allp if p["label"] == "推断")
    pct = round(100 * td / tot, 1) if tot else 0
    check("推断占比≈50% (对账教研解析真相源; 防回退 inference 错估15%, 坑16)",
          abs(pct - 50.0) <= 5, f"推断 {pct}%")

    bad_prov = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        "AND json_extract_string(evidence_json,'$.provenance')<>'explicit_label'").fetchone()[0]
    check("cognitive_skill 全 explicit_label (教研显式标签非inference)", bad_prov == 0, f"{bad_prov}")

    bad_lin = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND ("
        "json_extract_string(evidence_json,'$.lineage.version_ids.exam_paper') IS NULL "
        "OR json_extract_string(evidence_json,'$.lineage.source_year') IS NULL)").fetchone()[0]
    check("cognitive_skill 边全带血缘 (version_ids.exam_paper + source_year; stamp 写边即带)",
          bad_lin == 0, f"{bad_lin} 缺血缘")
