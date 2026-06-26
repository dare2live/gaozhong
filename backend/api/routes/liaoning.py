"""GET /api/liaoning/* — 辽宁省允许版本 + 14 地市选用."""
from __future__ import annotations

import json

from backend.api.db import db_ro, rows_to_dicts
from backend.services import canonical


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
        # city→version 走 canonical 单点 (同表查询收口); 印证页按 publisher_short, city 排序
        rows = sorted(canonical.city_version_rows(con), key=lambda r: (r[1], r[0]))
        return [{"city": c, "publisher_short": p, "source": s} for c, p, s in rows]
    finally:
        con.close()


ROUTES = {
    "/api/liaoning/allowed_publishers": api_allowed_publishers,
    "/api/liaoning/city_choice": api_city_choice,
}
