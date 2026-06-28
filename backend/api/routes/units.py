"""教材单元 API.

GET /api/units         — 教材单元列表 (STEP 2 输出)
GET /api/unit/content  — 单元词表(unit_vocab_intro) + 课文段(sections) — 直接 DB 渲染 (教材已入库, 不依赖 PDF)
"""
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


def api_unit_content(qs: dict) -> dict:
    """单元内容直出 DB (薄壳; 计算在 services.textbook_content 单算点): 上半知识点(词/短语/句型/语法/表达) + 下半正文."""
    version = (qs.get("version", [None])[0] or "").strip()
    volume = (qs.get("volume", [None])[0] or "").strip()
    raw_unit = qs.get("unit", [None])[0]  # unit=0 是合法预备单元(人教 WELCOME UNIT), 不用 falsy 判
    if not version or not volume or raw_unit is None:
        return {"error": "version/volume/unit required", "knowledge": {}, "passages": [], "passages_n": 0}
    try:
        unit = int(raw_unit)
    except (TypeError, ValueError):
        return {"error": "unit must be int", "knowledge": {}, "passages": [], "passages_n": 0}
    from backend.services.textbook_content import unit_content
    con = db_ro()
    try:
        return unit_content(con, version, volume, unit)
    finally:
        con.close()


ROUTES = {"/api/units": api_units, "/api/unit/content": api_unit_content}
