"""GET /api/exam_point/{distribution,cooccurrence} — 辽宁考点分布 + 关联性 (按卷制 era 分层).

单一计算点 (Rule 1): 复用 backend.services.exam_point 的 service, API 只读不重算。
分层非平均 (用户纠偏): {era: {dimension: [{label,n,pct}]}}; era ∈ {2021+_新高考II, 2015-2020_旧课标II}。
样本诚实 (件1): sufficiency 透传 scope.diagnose 的 distribution_eligible, 前端可标"样本不足"。
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.exam_point import (cloze_answer_word_stage, cloze_collocation_structural_subset,
                                          cognitive_skill_by_content, cognitive_skill_distribution,
                                          exam_point_cooccurrence, exam_point_distribution,
                                          exam_point_shift, grammar_structural_coverage,
                                          joint_attribution_by_passage, junior_senior_grammar_bridge,
                                          phrase_pattern_exam_relevance)
from backend.services.trend import scope


def _era_sufficiency(con, by_era=None) -> dict:
    """各 era 分布充足度 (单点取自 scope.diagnose, 与趋势同源); 供前端透出诚实标注.

    后端审计#5: by_era 是 era **子题池**总数(新卷制142), 对 cognitive_skill(子题级维度)正确;
    但 genre/theme 是**篇章级**维度, 样本量应按该(era,dim)的篇章数(distribution 的 n 之和, ~19-30),
    用142会虚高~4.5x 并误判 theme_l2(n=19<30)为充足。故加 by_era_dim 给前端按显示维度取真样本量。
    """
    diag = scope.diagnose(con)
    suff = {
        era: {
            "n_total": seg["total"],
            "distribution_eligible": seg["distribution_eligible"],
            "years": seg.get("years") or {},
            "adequate_year_share": seg.get("adequate_year_share"),
            "weight_dominated_by_early_full_years": seg.get(
                "weight_dominated_by_early_full_years", False),
            "composition_note": seg.get("composition_note"),
            "thin_years": seg.get("thin_years") or {},
        }
        for era, seg in diag["by_segment"].items()
    }
    by_dim: dict = {}
    for era, dims in (by_era or {}).items():
        by_dim[era] = {dim: {"n_total": sum(r["n"] for r in rows),
                             "distribution_eligible": sum(r["n"] for r in rows) >= scope.MIN_DISTRIBUTION_SAMPLE}
                       for dim, rows in dims.items()}
    return {
        "by_era": suff,
        "by_era_dim": by_dim,
        "distribution_reliable": diag["distribution_reliable"],
        "composition_notes": diag.get("composition_notes") or {},
    }


def api_exam_point_distribution(qs: dict) -> dict:
    """考点分布, 按 era 分层 + 占比; ?dimension=genre|theme_context|theme_l2 可过滤.
    theme 另附 theme_layers(human/dual 物理拆分, mixed_forbidden)。"""
    dimension = (qs.get("dimension", [None]) or [None])[0]
    con = db_ro()
    try:
        by_era = exam_point_distribution(con, dimension=dimension)
        eras = sorted(by_era, reverse=True)  # 新高考II 在前
        dims = sorted({d for era in by_era.values() for d in era})
        from backend.services.exam_point.loader import theme_distribution_layers
        from backend.services.exam_point.theme_truth import analysis_theme_crosscheck
        layers = theme_distribution_layers(con)
        if dimension in ("theme_l2", "theme_context"):
            layers = {e: {dimension: v[dimension]} for e, v in layers.items() if dimension in v}
        return {
            "province_scope": "辽宁卷",
            "layered_by": "卷制 era (PIT §3.1, 非全历史平均)",
            "provenance": "genre/theme: dual_model_agree+human_curriculum_verified; theme 禁止混算",
            "eras": eras,
            "dimensions": dims,
            "distribution": by_era,
            "theme_layers": layers,
            "theme_honesty": analysis_theme_crosscheck(con),
            "shift": exam_point_shift(con),
            "sufficiency": _era_sufficiency(con, by_era),
        }
    finally:
        con.close()


def api_exam_point_cooccurrence(qs: dict) -> dict:
    """考点关联性 (第三条腿): 同题跨轴共现对, 按 era 分层; ?min_co=2 可调阈."""
    try:
        min_co = max(2, int((qs.get("min_co", ["2"]) or ["2"])[0]))
    except (TypeError, ValueError):
        min_co = 2
    con = db_ro()
    try:
        return exam_point_cooccurrence(con, min_co=min_co)
    finally:
        con.close()


def api_exam_point_cognitive_skill(qs: dict) -> dict:
    """设问类型分布 (KG-A1; 高考口径) + 结构 L2 空位功能披露."""
    con = db_ro()
    try:
        out = cognitive_skill_distribution(con)
        from backend.services.exam_point.cognitive_seven_choose_five import (
            structure_subtype_distribution,
        )
        out["structure_subtypes"] = structure_subtype_distribution(con, "gaokao")
        out["structure_subtypes_zhongkao"] = structure_subtype_distribution(con, "zhongkao")
        return out
    finally:
        con.close()


def api_exam_point_structure_subtypes(qs: dict) -> dict:
    """理解文章结构类型 L2 空位功能分布. ?stage=gaokao|zhongkao"""
    stage = (qs.get("stage", ["gaokao"]) or ["gaokao"])[0] or "gaokao"
    if stage not in ("gaokao", "zhongkao"):
        return {"error": "stage must be gaokao|zhongkao"}
    con = db_ro()
    try:
        from backend.services.exam_point.cognitive_seven_choose_five import (
            structure_subtype_distribution,
        )
        return structure_subtype_distribution(con, stage)
    finally:
        con.close()


def api_exam_point_cognitive_by_content(qs: dict) -> dict:
    """设问技能×题材/主题 交叉 (2015-20截面; 老师"哪类语篇考哪种思维"分流). ?by=genre|theme_l2|theme_context."""
    by = (qs.get("by", ["genre"])[0] or "genre")
    con = db_ro()
    try:
        return cognitive_skill_by_content(con, by=by)
    except ValueError as e:
        return {"error": str(e)}
    finally:
        con.close()


def api_exam_point_joint_attribution(qs: dict) -> dict:
    """语篇级联合归因(词汇学段×设问思维), 2015-20截面; 回答"推断题多的文章是否词汇也更难"。"""
    con = db_ro()
    try:
        return joint_attribution_by_passage(con)
    finally:
        con.close()


def api_exam_point_cloze_answer_word_stage(qs: dict) -> dict:
    """完形填空得分点词学段分布, 分era对比全篇基线; 回答"得分点是初中词汇还是高中词汇"。"""
    con = db_ro()
    try:
        return cloze_answer_word_stage(con)
    finally:
        con.close()


def api_exam_point_grammar_structural_coverage(qs: dict) -> dict:
    """语法填空+短文改错 结构性(零主观判断成本)语法点覆盖; 回答"考查的高中知识点(语法)占比"。"""
    con = db_ro()
    try:
        return grammar_structural_coverage(con)
    finally:
        con.close()


def api_exam_point_phrase_pattern_relevance(qs: dict) -> dict:
    """短语/句型/表达(高中教材)与辽宁真题文本共现; 不做初高中对比(STEP1缺口, 见服务层docstring)。"""
    con = db_ro()
    try:
        return phrase_pattern_exam_relevance(con)
    finally:
        con.close()


def api_exam_point_cloze_collocation_subset(qs: dict) -> dict:
    """完形填空 结构规则可确认的"像固定搭配"子集(下限, 非真实占比)。"""
    con = db_ro()
    try:
        return cloze_collocation_structural_subset(con)
    finally:
        con.close()


def api_exam_point_k12_grammar_bridge(qs: dict) -> dict:
    """初中语法点→高中深化(deepens)→高考exam_status+中考真题印证情况 (Phase E5 K12衔接视图)。"""
    con = db_ro()
    try:
        return junior_senior_grammar_bridge(con)
    finally:
        con.close()


def api_exam_point_grammar_point_rollup(qs: dict) -> dict:
    """语法九桶只读派生 (←tests_grammar); 非独立考查维."""
    from backend.services.exam_point.grammar_point_rollup import grammar_point_rollup
    con = db_ro()
    try:
        return grammar_point_rollup(con)
    finally:
        con.close()


def api_exam_point_quality_standards(qs: dict) -> dict:
    """课标学业质量水平(3+42描述) + 辽宁高考卷级对齐水平二."""
    from backend.services.exam_point.quality_standards import quality_standards_summary
    con = db_ro()
    try:
        return quality_standards_summary(con)
    finally:
        con.close()


ROUTES = {
    "/api/exam_point/distribution": api_exam_point_distribution,
    "/api/exam_point/cooccurrence": api_exam_point_cooccurrence,
    "/api/exam_point/cognitive_skill": api_exam_point_cognitive_skill,
    "/api/exam_point/structure_subtypes": api_exam_point_structure_subtypes,
    "/api/exam_point/cognitive_by_content": api_exam_point_cognitive_by_content,  # 技能×题材交叉(2015-20)
    "/api/exam_point/joint_attribution": api_exam_point_joint_attribution,  # 词汇×设问思维语篇级联合归因
    "/api/exam_point/cloze_answer_word_stage": api_exam_point_cloze_answer_word_stage,  # 完形得分点词学段
    "/api/exam_point/grammar_structural_coverage": api_exam_point_grammar_structural_coverage,  # 高中语法知识点覆盖
    "/api/exam_point/phrase_pattern_relevance": api_exam_point_phrase_pattern_relevance,  # 短语句型真题共现
    "/api/exam_point/cloze_collocation_subset": api_exam_point_cloze_collocation_subset,  # 完形搭配结构下限
    "/api/exam_point/k12_grammar_bridge": api_exam_point_k12_grammar_bridge,  # 初中→高中语法衔接+中考印证
    "/api/exam_point/grammar_point_rollup": api_exam_point_grammar_point_rollup,  # 九桶只读派生
    "/api/exam_point/quality_standards": api_exam_point_quality_standards,
}
