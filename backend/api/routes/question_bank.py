"""题库 + 标签 + 组卷 API."""
from __future__ import annotations

import json

from backend.api.db import db_ro, rows_to_dicts


def api_qb_stats(_qs: dict) -> dict:
    con = db_ro()
    try:
        s = {}
        s["total"] = con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0]
        s["by_type"] = dict(con.execute(
            "SELECT question_type, COUNT(*) FROM question_bank GROUP BY question_type "
            "ORDER BY COUNT(*) DESC"
        ).fetchall())
        s["by_origin"] = dict(con.execute(
            "SELECT origin, COUNT(*) FROM question_bank GROUP BY origin"
        ).fetchall())
        s["by_difficulty"] = dict(con.execute(
            "SELECT difficulty, COUNT(*) FROM question_bank GROUP BY difficulty"
        ).fetchall())
        s["tags_total"] = con.execute(
            "SELECT COUNT(*) FROM tag_dictionary").fetchone()[0]
        s["tag_by_kind"] = dict(con.execute(
            "SELECT tag_kind, COUNT(*) FROM tag_dictionary GROUP BY tag_kind "
            "ORDER BY COUNT(*) DESC"
        ).fetchall())
        s["question_tags"] = con.execute(
            "SELECT COUNT(*) FROM question_tags").fetchone()[0]
        return s
    finally:
        con.close()


def api_qb_browse(qs: dict) -> list[dict]:
    """Browse + filter question_bank by tag_id / question_type."""
    qtype = qs.get("type", [None])[0]
    tag_id = qs.get("tag", [None])[0]
    try:
        limit = min(int(qs.get("limit", ["50"])[0]), 200)
    except ValueError:
        limit = 50
    where = ["1=1"]
    args: list = []
    if qtype:
        where.append("qb.question_type = ?"); args.append(qtype)
    if tag_id:
        where.append("EXISTS (SELECT 1 FROM question_tags qt "
                     "WHERE qt.qb_id = qb.qb_id AND qt.tag_id = ?)")
        args.append(tag_id)
    sql = ("SELECT qb_id, origin, question_type, "
           "SUBSTR(stem, 1, 200) AS stem_preview, answer, difficulty "
           "FROM question_bank qb WHERE " + " AND ".join(where)
           + " ORDER BY qb_id DESC LIMIT ?")
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


def api_qb_detail(qs: dict) -> dict:
    qb_id_s = qs.get("id", [None])[0]
    if not qb_id_s:
        return {"error": "missing ?id="}
    try:
        qb_id = int(qb_id_s)
    except ValueError:
        return {"error": "id must be int"}
    con = db_ro()
    try:
        row = con.execute("""
            SELECT qb_id, origin, origin_ref, question_type, stem, options_json,
                   answer, analysis, difficulty
            FROM question_bank WHERE qb_id = ?
        """, [qb_id]).fetchone()
        if not row:
            return {"error": "not found"}
        tags = [r[0] for r in con.execute(
            "SELECT tag_id FROM question_tags WHERE qb_id = ?", [qb_id]
        ).fetchall()]
        return {
            "qb_id": row[0], "origin": row[1], "origin_ref": row[2],
            "qtype": row[3], "stem": row[4],
            "options": json.loads(row[5]) if row[5] else None,
            "answer": row[6], "analysis": row[7], "difficulty": row[8],
            "tags": tags,
        }
    finally:
        con.close()


def api_qb_tags(qs: dict) -> list[dict]:
    """List tags filtered by kind."""
    kind = qs.get("kind", [None])[0]
    try: limit = min(int(qs.get("limit", ["200"])[0]), 2000)
    except ValueError: limit = 200
    sql = ("SELECT t.tag_id, t.tag_kind, t.label, COUNT(qt.qb_id) AS n_q "
           "FROM tag_dictionary t LEFT JOIN question_tags qt ON qt.tag_id = t.tag_id ")
    args: list = []
    if kind:
        sql += " WHERE t.tag_kind = ?"; args.append(kind)
    sql += " GROUP BY t.tag_id, t.tag_kind, t.label ORDER BY n_q DESC LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


def _parse_type_mix(s: str) -> dict:
    mix = {}
    for pair in s.split(","):
        if ":" in pair:
            t, c = pair.split(":", 1)
            try: mix[t.strip()] = int(c)
            except ValueError: pass
    return mix


def _parse_list(s: str | None) -> list | None:
    if not s: return None
    out = [t for t in s.split(",") if t]
    return out or None


def _parse_int(s: str | None) -> int | None:
    return int(s) if s and s.isdigit() else None


def _build_spec(qs: dict) -> dict:
    mix = _parse_type_mix(qs.get("type_mix", [""])[0]) or \
          {"阅读理解": 4, "语法填空": 8, "选义单选": 8}
    year_in_s = qs.get("year_in", [""])[0]
    year_in = [int(y) for y in year_in_s.split(",") if y.isdigit()] if year_in_s else None
    return {
        "type_mix": mix,
        "require_tags": _parse_list(qs.get("require_tags", [""])[0]),
        "difficulty": qs.get("difficulty", [None])[0],
        "seed": _parse_int(qs.get("seed", [None])[0]),
        "year_in": year_in,
    }


def api_paper_compose(qs: dict) -> dict:
    from backend.services.question_bank import compose as cmp
    spec = _build_spec(qs)
    con = db_ro()
    try:
        return cmp.compose(con, spec)
    finally:
        con.close()


ROUTES = {
    "/api/qb/stats": api_qb_stats,
    "/api/qb/browse": api_qb_browse,
    "/api/qb/detail": api_qb_detail,
    "/api/qb/tags": api_qb_tags,
    "/api/paper/compose": api_paper_compose,
}
