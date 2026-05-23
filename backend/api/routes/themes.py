"""GET /api/theme_contexts — 课标主题语境."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_theme_contexts(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT theme_context_id, level1, level2 FROM theme_contexts "
            "ORDER BY level1, level2 NULLS FIRST"
        ))
    finally:
        con.close()


ROUTES = {"/api/theme_contexts": api_theme_contexts}
