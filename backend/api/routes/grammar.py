"""课标语法 API.

GET /api/grammar_items — 课标语法项目表 (层级)
GET /api/grammar/stats — 辽宁语法考查统计(课标子类频次热点) + 教材搭配/句型/表达库 (北极星 真题特点扩展)
"""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_grammar_items(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT grammar_item_id, depth, parent_id, category, label, cefr_level "
            "FROM grammar_items ORDER BY seq"
        ))
    finally:
        con.close()


def api_grammar_stats(_qs: dict) -> dict:
    """辽宁语法考查统计 + 教材搭配/句型/表达库 (语法/搭配/句型/时态/从句 扩展)."""
    from backend.services.exam_grammar_stats import expression_stats
    con = db_ro()
    try:
        return expression_stats(con)
    finally:
        con.close()


ROUTES = {
    "/api/grammar_items": api_grammar_items,
    "/api/grammar/stats": api_grammar_stats,
}
