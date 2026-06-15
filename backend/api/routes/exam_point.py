"""GET /api/exam_point/distribution — 辽宁考点分布 (按卷制 era 分层, 前端热力图源).

单一计算点 (Rule 1): 复用 backend.services.exam_point.exam_point_distribution, API 只读不重算。
分层非平均 (用户纠偏): 默认 {era: {dimension: [{label,n,pct}]}}; era ∈ {2021+_新高考II, 2015-2020_旧课标II}。
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.exam_point import exam_point_distribution


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
        }
    finally:
        con.close()


ROUTES = {
    "/api/exam_point/distribution": api_exam_point_distribution,
}
