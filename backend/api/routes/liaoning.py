"""GET /api/liaoning/* — 辽宁省允许版本 + 14 地市选用."""
from __future__ import annotations

import json

from backend.api.db import db_ro, rows_to_dicts


def api_allowed_publishers(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        rows = rows_to_dicts(con.execute(
            "SELECT rank, chief_editor, publisher, book_title, volumes_json, source "
            "FROM liaoning_allowed_publishers WHERE subject = '英语' ORDER BY rank"
        ))
        for r in rows:
            r["volumes"] = json.loads(r.pop("volumes_json"))
        return rows
    finally:
        con.close()


def api_city_choice(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT city, publisher_short, source FROM liaoning_city_textbook_choice "
            "WHERE subject = '英语' ORDER BY publisher_short, city"
        ))
    finally:
        con.close()


ROUTES = {
    "/api/liaoning/allowed_publishers": api_allowed_publishers,
    "/api/liaoning/city_choice": api_city_choice,
}
