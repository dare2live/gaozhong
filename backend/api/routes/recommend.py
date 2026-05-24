"""教师端 ─ 知识图谱产品化 (推荐 / 路径 / 跨版本对照)."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services import recommend as r


def api_city_curriculum(qs: dict) -> dict:
    city = qs.get("city", ["沈阳"])[0]
    con = db_ro()
    try: return r.city_curriculum(con, city)
    finally: con.close()


def api_top_exam_words(qs: dict) -> list[dict]:
    try: limit = min(int(qs.get("n", ["30"])[0]), 200)
    except ValueError: limit = 30
    con = db_ro()
    try: return r.top_exam_words(con, limit)
    finally: con.close()


def api_cross_version_units(qs: dict) -> list[dict]:
    unit_id = qs.get("unit", [""])[0]
    con = db_ro()
    try: return r.cross_version_units(con, unit_id)
    finally: con.close()


def api_unit_exam_alignment(qs: dict) -> dict:
    unit_id = qs.get("unit", [""])[0]
    con = db_ro()
    try: return r.unit_exam_alignment(con, unit_id)
    finally: con.close()


ROUTES = {
    "/api/recommend/city_curriculum": api_city_curriculum,
    "/api/recommend/top_exam_words": api_top_exam_words,
    "/api/recommend/cross_version_units": api_cross_version_units,
    "/api/recommend/unit_exam_alignment": api_unit_exam_alignment,
}
