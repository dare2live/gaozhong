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
    """单元内容直出 DB (教材已解析入库, 不链 PDF): 词表(unit_vocab_intro) + 课文段(sections).

    入参 version/volume/unit. 词表带 在课标/词性/中文释义; 课文段带 kind/title/页码 (语篇/应用文/听力标记)。
    """
    version = (qs.get("version", [None])[0] or "").strip()
    volume = (qs.get("volume", [None])[0] or "").strip()
    raw_unit = qs.get("unit", [None])[0]  # unit=0 是合法的预备单元(如人教 WELCOME UNIT), 不能用 falsy 判
    _empty = {"vocab": [], "vocab_n": 0, "sections": [], "sections_n": 0}
    if not version or not volume or raw_unit is None:
        return {"error": "version/volume/unit required", **_empty}
    try:
        unit = int(raw_unit)
    except (TypeError, ValueError):
        return {"error": "unit must be int", **_empty}
    con = db_ro()
    try:
        vocab = rows_to_dicts(con.execute(
            "SELECT word, pos, zh_def, in_curriculum FROM unit_vocab_intro "
            "WHERE version_key=? AND volume_key=? AND unit_number=? ORDER BY word", [version, volume, unit]))
        sections = rows_to_dicts(con.execute(
            "SELECT seq, kind, title, page_start, page_end, is_narrative, is_applied, is_listening "
            "FROM sections WHERE version_key=? AND volume_key=? AND unit_number=? ORDER BY seq", [version, volume, unit]))
    finally:
        con.close()
    return {"version_key": version, "volume_key": volume, "unit_number": unit,
            "vocab": vocab, "vocab_n": len(vocab), "sections": sections, "sections_n": len(sections),
            "note": "教材已解析入库, 内容直接来自 DB (unit_vocab_intro + sections), 不依赖 PDF。"}


ROUTES = {"/api/units": api_units, "/api/unit/content": api_unit_content}
