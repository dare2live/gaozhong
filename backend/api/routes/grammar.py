"""GET /api/grammar_items — 课标语法项目表 (层级)."""
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


ROUTES = {"/api/grammar_items": api_grammar_items}
