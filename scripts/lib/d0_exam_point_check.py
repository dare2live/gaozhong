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
    _check_no_theme_l3(con, check)


def _check_no_theme_l3(con: duckdb.DuckDBPyConnection, check) -> None:
    """防回归锁 (2026-06-21 真值核验): 课标主题语境官方仅 L1/L2 可枚举, 无"第三级子主题"。
    曾有 35 个杜撰 theme_l3(extract_curriculum _reader 不读PDF 直接塞 + dual_model 贴标签) → 已废。
    正向断言三件套 (坑1: 锁住'无', 防 extract 重建静默塞回; 配 ThemeTruthChecker 真值锚)。"""
    n_l3_edge = con.execute(
        "SELECT COUNT(*) FROM edges WHERE dst_id LIKE 'exam_point:theme_l3:%' "
        "OR src_id LIKE 'exam_point:theme_l3:%'").fetchone()[0]
    check("无杜撰 theme_l3 边 (官方主题语境仅L1/L2; 亲验PDF表2)", n_l3_edge == 0, f"{n_l3_edge} 残留")
    n_l3_ctx = con.execute(
        "SELECT COUNT(*) FROM theme_contexts WHERE level3 IS NOT NULL AND TRIM(level3)<>''").fetchone()[0]
    check("theme_contexts.level3 全空 (官方无可枚举第三级)", n_l3_ctx == 0, f"{n_l3_ctx} 残留")
    # theme 叶节点不得有 depth2 (2斜杠 = 杜撰子主题命名空间)
    n_l3_node = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='theme' "
        "AND length(concept_id)-length(replace(concept_id,'/',''))>=2").fetchone()[0]
    check("无 theme depth2 叶节点 (杜撰子主题命名空间已废)", n_l3_node == 0, f"{n_l3_node} 残留")
