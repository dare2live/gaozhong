"""GET /api/cefr_vocab — 课标词汇表查询."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_cefr_vocab(qs: dict) -> list[dict]:
    level = qs.get("level", [None])[0]
    prefix = qs.get("prefix", [""])[0].lower()
    try:
        limit = min(int(qs.get("limit", ["200"])[0]), 1000)
    except ValueError:
        limit = 200
    where, args = [], []
    if level:
        where.append("cefr_level = ?"); args.append(level)
    if prefix:
        where.append("word LIKE ?"); args.append(prefix + "%")
    sql = "SELECT word, cefr_level, raw_suffix FROM cefr_vocab"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY word LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


ROUTES = {"/api/cefr_vocab": api_cefr_vocab}
