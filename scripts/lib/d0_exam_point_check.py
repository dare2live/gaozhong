"""D0 考点 canonical 维度校验 (从 data_accuracy_check 抽出, 避 god-module Rule 8).

件2 考点 canonical + 4路桥(theme_aligns) + 学情薄弱环节考点化 纳入 D0 100% 强校验。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B


def check_exam_point(con: duckdb.DuckDBPyConnection, check) -> None:
    """考点边/4路桥/薄弱环节 5 项 D0 校验 (新数据落地必入强校验)."""
    print("\n=== (22) 考点 canonical 维度 + 4路追溯 ===")
    n_ep = con.execute("SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point'").fetchone()[0]
    check("tests_exam_point 边 ≥ 300", n_ep >= B('exam_point_min'), f"{n_ep}")
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
    _check_passage_dim_granularity(con, check)
    _check_evidence_json_valid(con, check)


def _check_passage_dim_granularity(con: duckdb.DuckDBPyConnection, check) -> None:
    """RC1#6 防回归 (后端审计 2026-06-27): genre/theme/theme_l2 是**篇章级**维度(整篇1个体裁/主题),
    eol 2021/2022 按子题存 → 分布/共现必须排除子题级源(source_repo LIKE 'eol_xgkii%'), 否则 1 篇 N 子题
    记 N 次失真(记叙文 55.8% 子题膨胀, 篇章级真值~30%; "命题迁移+24pt"伪迁移)。
    断言: 分布数的 genre/theme 边 == 非子题级源 genre/theme 边(证明滤生效; 回归则分布数虚高 → FAIL)。"""
    from backend.services.exam_point.loader import exam_point_distribution
    dist = exam_point_distribution(con)
    dist_n = sum(x["n"] for era in dist.values()
                 for d in ("genre", "theme_context", "theme_l2") for x in era.get(d, []))
    truth_n = con.execute(
        "SELECT COUNT(*) FROM edges e "
        "JOIN exam_questions q ON ('question:'||q.question_id)=e.src_id AND q.province LIKE '辽宁%' "
        "WHERE e.relation='tests_exam_point' "
        "AND json_extract_string(e.evidence_json,'$.dimension') IN ('genre','theme_context','theme_l2') "
        "AND q.source_repo NOT LIKE 'eol_xgkii%'").fetchone()[0]
    check("genre/theme 分布=篇章级口径 (排除子题级eol源; 防记叙文子题膨胀+伪迁移回归)",
          dist_n == truth_n, f"分布数{dist_n} ≠ 篇章级真值{truth_n}")


def _check_evidence_json_valid(con: duckdb.DuckDBPyConnection, check) -> None:
    """RC1#5 防回归: 全边 evidence_json 须合法 JSON (手拼含 \\x7f/制表符=非法, 全表 json_extract 崩)。"""
    bad = con.execute(
        "SELECT COUNT(*) FROM edges WHERE evidence_json IS NOT NULL "
        "AND TRIM(evidence_json) <> '' AND NOT json_valid(evidence_json)").fetchone()[0]
    check("全边 evidence_json 合法JSON (防手拼控制字符致全表json_extract崩)", bad == 0, f"{bad} 非法")


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
