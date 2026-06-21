"""D0 设问类型 cognitive_skill 金矿校验 (KG层 A1; 坑16/坑17/§7, docs/kg_layer_design §5).

2026-06-20 纠偏: 源 subquestions 2021 经 ≥2 独立源证实是**全国甲卷**(Take a view), 非辽宁II卷 →
真值锚交叉(truth_anchor_protocol)在 loader 剔除, cognitive_skill 现纯 2023 真辽宁II卷(15边, n小诚实标)。
锁: 边数==15 + 无源误标年(全2023, 甲卷已剔§7) + 推断为最高频(坑16) + explicit_label + 血缘。
"""
from __future__ import annotations

import duckdb

_DIM = "json_extract_string(evidence_json,'$.dimension')='cognitive_skill'"


def check_cognitive_skill(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (30) 设问类型 cognitive_skill 金矿 (2023真辽宁II卷, 真值锚剔2021甲卷, 坑16/§7) ===")
    n_edge = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM}").fetchone()[0]
    check("cognitive_skill 边 == 15 (2023真辽宁II卷; 真值锚交叉剔2021甲卷源误标)", n_edge == 15, f"{n_edge}")

    # §7: 全 2023, 无误标年混入 (2021甲卷已被真值锚交叉剔除)
    bad_year = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        "AND json_extract_string(evidence_json,'$.lineage.source_year')<>'2023'").fetchone()[0]
    check("无源误标年混入 (全2023真II卷; 甲卷冒辽宁已剔, §7真值锚交叉)", bad_year == 0, f"{bad_year} 非2023")

    from backend.services.exam_point import cognitive_skill_distribution
    allp = [p for pts in cognitive_skill_distribution(con)["by_era"].values() for p in pts]
    tot = sum(p["n"] for p in allp)
    top = max(allp, key=lambda p: p["n"]) if allp else {"label": "?"}
    check("推断为最高频技能 (坑16: 设问表面像细节实考推断; n=15 小样本诚实标)",
          top["label"] == "推断", f"最高频={top['label']} (n={tot})")

    bad_prov = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        "AND json_extract_string(evidence_json,'$.provenance')<>'explicit_label'").fetchone()[0]
    check("cognitive_skill 全 explicit_label (教研显式标签非inference)", bad_prov == 0, f"{bad_prov}")

    bad_lin = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND ("
        "json_extract_string(evidence_json,'$.lineage.version_ids.exam_paper') IS NULL "
        "OR json_extract_string(evidence_json,'$.lineage.source_year') IS NULL)").fetchone()[0]
    check("cognitive_skill 边全带血缘 (version_ids.exam_paper + source_year)", bad_lin == 0, f"{bad_lin} 缺血缘")
