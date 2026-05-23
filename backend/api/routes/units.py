"""GET /api/units — 教材单元列表 (STEP 2 输出)."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_units(qs: dict) -> list[dict]:
    version = qs.get("version", [None])[0]
    volume = qs.get("volume", [None])[0]
    where, args = [], []
    if version:
        where.append("version_key = ?"); args.append(version)
    if volume:
        where.append("volume_key = ?"); args.append(volume)
    sql = ("SELECT version_key, volume_key, unit_number, title_en, "
           "page_start, page_end, extract_method "
           "FROM units")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY version_key, volume_key, unit_number"
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


ROUTES = {"/api/units": api_units}
