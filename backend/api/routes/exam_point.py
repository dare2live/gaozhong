"""GET /api/exam_point/{distribution,cooccurrence} — 辽宁考点分布 + 关联性 (按卷制 era 分层).

单一计算点 (Rule 1): 复用 backend.services.exam_point 的 service, API 只读不重算。
分层非平均 (用户纠偏): {era: {dimension: [{label,n,pct}]}}; era ∈ {2021+_新高考II, 2015-2020_旧课标II}。
样本诚实 (件1): sufficiency 透传 scope.diagnose 的 distribution_eligible, 前端可标"样本不足"。
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.exam_point import (cognitive_skill_by_content, cognitive_skill_distribution,
                                          exam_point_cooccurrence, exam_point_distribution,
                                          exam_point_shift)
from backend.services.trend import scope


def _era_sufficiency(con, by_era=None) -> dict:
    """各 era 分布充足度 (单点取自 scope.diagnose, 与趋势同源); 供前端透出诚实标注.

    后端审计#5: by_era 是 era **子题池**总数(新卷制142), 对 cognitive_skill(子题级维度)正确;
    但 genre/theme 是**篇章级**维度, 样本量应按该(era,dim)的篇章数(distribution 的 n 之和, ~19-30),
    用142会虚高~4.5x 并误判 theme_l2(n=19<30)为充足。故加 by_era_dim 给前端按显示维度取真样本量。
    """
    diag = scope.diagnose(con)
    suff = {era: {"n_total": seg["total"], "distribution_eligible": seg["distribution_eligible"]}
            for era, seg in diag["by_segment"].items()}
    by_dim: dict = {}
    for era, dims in (by_era or {}).items():
        by_dim[era] = {dim: {"n_total": sum(r["n"] for r in rows),
                             "distribution_eligible": sum(r["n"] for r in rows) >= scope.MIN_DISTRIBUTION_SAMPLE}
                       for dim, rows in dims.items()}
    return {"by_era": suff, "by_era_dim": by_dim, "distribution_reliable": diag["distribution_reliable"]}


def api_exam_point_distribution(qs: dict) -> dict:
    """考点分布, 按 era 分层 + 占比; ?dimension=genre|theme_context|theme_l2 可过滤."""
    dimension = (qs.get("dimension", [None]) or [None])[0]
    con = db_ro()
    try:
        by_era = exam_point_distribution(con, dimension=dimension)
        eras = sorted(by_era, reverse=True)  # 新高考II 在前
        dims = sorted({d for era in by_era.values() for d in era})
        return {
            "province_scope": "辽宁卷",
            "layered_by": "卷制 era (PIT §3.1, 非全历史平均)",
            "provenance": "dual_model_agree (双模型一致; needs_review 歧义项不入)",
            "eras": eras,
            "dimensions": dims,
            "distribution": by_era,
            "shift": exam_point_shift(con),   # 命题迁移单算点 (前端不重算, Rule1; 审计HIGH#18)
            "sufficiency": _era_sufficiency(con, by_era),   # 审计#5: 传 by_era 得 per-(era,dim) 篇章级样本量
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
    """设问类型分布 (KG-A1 金矿; 子题级"怎么想", explicit_label, 推断50% vs inference错估15%)."""
    con = db_ro()
    try:
        return cognitive_skill_distribution(con)
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


ROUTES = {
    "/api/exam_point/distribution": api_exam_point_distribution,
    "/api/exam_point/cooccurrence": api_exam_point_cooccurrence,
    "/api/exam_point/cognitive_skill": api_exam_point_cognitive_skill,
    "/api/exam_point/cognitive_by_content": api_exam_point_cognitive_by_content,  # 技能×题材交叉(2015-20)
}
