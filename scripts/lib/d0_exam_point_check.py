"""D0 考点 canonical 维度校验 (从 data_accuracy_check 抽出, 避 god-module Rule 8).

件2 考点 canonical + 4路桥(theme_aligns) + 学情薄弱环节考点化 纳入 D0 100% 强校验。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import duckdb


def check_exam_point(con: duckdb.DuckDBPyConnection, check) -> None:
    """考点边/4路桥/薄弱环节 5 项 D0 校验 (新数据落地必入强校验)."""
    print("\n=== (22) 考点 canonical 维度 + 4路追溯 ===")
    n_ep = con.execute("SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point'").fetchone()[0]
    check("tests_exam_point 边 ≥ 300", n_ep >= 300, f"{n_ep}")
    bad_ep = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='tests_exam_point' AND ("
        "NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id=e.src_id AND n.node_type='question') "
        "OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id=e.dst_id AND n.node_type='exam_point'))"
    ).fetchone()[0]
    check("考点边两端有效 (无悬挂)", bad_ep == 0, f"{bad_ep} 悬挂")
    bad_prov = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json,'$.provenance') NOT IN ('dual_model_agree','explicit_label')"
    ).fetchone()[0]
    check("考点边 provenance ∈ {dual_model_agree, explicit_label} (无弱provenance; cognitive_skill=教研显式标签)",
          bad_prov == 0, f"{bad_prov} 弱provenance")
    bad_ta = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='theme_aligns' AND ("
        "e.src_id NOT LIKE 'exam_point:theme%' OR e.dst_id NOT LIKE 'theme:%')").fetchone()[0]
    check("theme_aligns 桥两端有效", bad_ta == 0, f"{bad_ta} 错连")
    bad_wk = con.execute(
        "SELECT COUNT(*) FROM student_weakness WHERE concept_id NOT LIKE 'exam_point:%'").fetchone()[0]
    check("薄弱环节维度=exam_point真考点 (非word token)", bad_wk == 0, f"{bad_wk} 非考点")
    _check_theme_l3(con, check)


def _check_theme_l3(con: duckdb.DuckDBPyConnection, check) -> None:
    """课标第三级 35 子主题 (颗粒度对齐官方最深层) — province 锚定 + 桥完整 (坑17 新维度入强校验)."""
    n_l3 = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND dst_id LIKE 'exam_point:theme_l3:%'").fetchone()[0]
    check("theme_l3(课标第三级) 边 ≥ 80", n_l3 >= 80, f"{n_l3}")
    # province 锚定: theme_l3 边全来自辽宁卷 (标注源即辽宁; §7 不混外省)
    non_ln = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN exam_questions q ON 'question:'||q.question_id=e.src_id "
        "WHERE e.relation='tests_exam_point' AND e.dst_id LIKE 'exam_point:theme_l3:%' "
        "AND q.province NOT LIKE '辽宁%'").fetchone()[0]
    check("theme_l3 边全辽宁卷 (§7)", non_ln == 0, f"{non_ln} 非辽宁")
    # 每个 theme_l3 节点桥到教材 theme (4路追溯不断缝)
    unbridged = con.execute(
        "SELECT COUNT(*) FROM nodes n WHERE n.concept_id LIKE 'exam_point:theme_l3:%' "
        "AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.src_id=n.concept_id AND e.relation='theme_aligns')"
    ).fetchone()[0]
    check("theme_l3 节点全桥到教材theme (4路追溯)", unbridged == 0, f"{unbridged} 未桥")
