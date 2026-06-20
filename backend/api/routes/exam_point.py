"""GET /api/exam_point/{distribution,cooccurrence} — 辽宁考点分布 + 关联性 (按卷制 era 分层).

单一计算点 (Rule 1): 复用 backend.services.exam_point 的 service, API 只读不重算。
分层非平均 (用户纠偏): {era: {dimension: [{label,n,pct}]}}; era ∈ {2021+_新高考II, 2015-2020_旧课标II}。
样本诚实 (件1): sufficiency 透传 scope.diagnose 的 distribution_eligible, 前端可标"样本不足"。
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.exam_point import (exam_point_cooccurrence, exam_point_distribution,
                                          exam_point_shift)
from backend.services.trend import scope


def _era_sufficiency(con) -> dict:
    """各 era 分布充足度 (单点取自 scope.diagnose, 与趋势同源); 供前端透出诚实标注."""
    diag = scope.diagnose(con)
    suff = {era: {"n_total": seg["total"], "distribution_eligible": seg["distribution_eligible"]}
            for era, seg in diag["by_segment"].items()}
    return {"by_era": suff, "distribution_reliable": diag["distribution_reliable"]}


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
            "sufficiency": _era_sufficiency(con),
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


ROUTES = {
    "/api/exam_point/distribution": api_exam_point_distribution,
    "/api/exam_point/cooccurrence": api_exam_point_cooccurrence,
}
