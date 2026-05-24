"""GET /api/lesson_plan?unit=... — 单元教案 (含趋势 + 真题溯源)."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services import lesson_plan


def api_lesson_plan(qs: dict) -> dict:
    unit_id = qs.get("unit", [None])[0]
    if not unit_id or not unit_id.startswith("unit:"):
        return {"error": "missing or invalid ?unit= (need 'unit:waiyan/bixiu_1/U1')"}
    con = db_ro()
    try:
        return lesson_plan.generate_lesson_plan(con, unit_id)
    finally:
        con.close()


ROUTES = {
    "/api/lesson_plan": api_lesson_plan,
}
