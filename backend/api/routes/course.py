"""第五阶段 /api/course/* — 40 节课程方案 (5.1 接口契约 D6).

endpoints:
  /api/course/list                 -> 40 节列表 (按 layer 分组)
  /api/course/session?id=N         -> 1 节详情 (含 materials)
  /api/course/handout?id=N         -> 1 节讲义 md + segments
  /api/course/stats                -> 课程统计 (灌库后)
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.course import handout, loader


def api_course_list(qs: dict) -> dict:
    layer = (qs.get("layer", [None])[0] or "").strip()
    con = db_ro()
    try:
        sql = ("SELECT course_id, layer, title, block_kind, block_order, duration_min, "
               "listening_required, themes_main "
               "FROM courses")
        args: list = []
        if layer:
            sql += " WHERE layer = ?"
            args.append(layer)
        sql += " ORDER BY layer, block_order"
        rows = con.execute(sql, args).fetchall()
        return {
            "courses": [
                {"course_id": r[0], "layer": r[1], "title": r[2],
                 "block_kind": r[3], "block_order": r[4],
                 "duration_min": r[5], "listening_required": r[6],
                 "themes_main": r[7]}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def api_course_session(qs: dict) -> dict:
    cid = _course_id(qs)
    if cid is None:
        return {"error": "missing or invalid ?id (1..40)"}
    con = db_ro()
    try:
        c = con.execute(
            "SELECT course_id, layer, title, block_kind, block_order, duration_min, "
            "listening_required, description, themes_main, themes_aux "
            "FROM courses WHERE course_id = ?",
            [cid],
        ).fetchone()
        if not c:
            return {"error": f"course {cid} not found"}
        mats = con.execute(
            "SELECT seq, kind, ref_id, year_level, textbook_position, source, reason "
            "FROM course_materials WHERE course_id = ? ORDER BY seq",
            [cid],
        ).fetchall()
        return {
            "course": {
                "course_id": c[0], "layer": c[1], "title": c[2],
                "block_kind": c[3], "block_order": c[4],
                "duration_min": c[5], "listening_required": c[6],
                "description": c[7], "themes_main": c[8], "themes_aux": c[9],
            },
            "materials": [
                {"seq": m[0], "kind": m[1], "ref_id": m[2], "year_level": m[3],
                 "textbook_position": m[4], "source": m[5], "reason": m[6]}
                for m in mats
            ],
        }
    finally:
        con.close()


def api_course_handout(qs: dict) -> dict:
    cid = _course_id(qs)
    if cid is None:
        return {"error": "missing or invalid ?id (1..40)"}
    courses = loader.load_course_templates()
    course = next((c for c in courses if c["course_id"] == cid), None)
    if not course:
        return {"error": f"course {cid} not in yaml"}
    con = db_ro()
    try:
        return handout.render_handout(con, course)
    finally:
        con.close()


def api_course_stats(qs: dict) -> dict:
    con = db_ro()
    try:
        layer_rows = con.execute(
            "SELECT layer, COUNT(*) FROM courses GROUP BY layer ORDER BY 1"
        ).fetchall()
        kind_rows = con.execute(
            "SELECT block_kind, COUNT(*) FROM courses GROUP BY block_kind ORDER BY 2 DESC"
        ).fetchall()
        mat_total = con.execute("SELECT COUNT(*) FROM course_materials").fetchone()[0]
        return {
            "by_layer": {r[0]: r[1] for r in layer_rows},
            "by_block_kind": {r[0]: r[1] for r in kind_rows},
            "total_courses": sum(r[1] for r in layer_rows),
            "total_materials": mat_total,
        }
    finally:
        con.close()


def _course_id(qs: dict) -> int | None:
    raw = qs.get("id", [None])[0]
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def api_course_quiz(qs: dict) -> dict:
    """课后测验 — 返回本节 homework 题 (含选项+答案, 供前端即时批改)."""
    cid = _course_id(qs)
    if cid is None:
        return {"error": "missing or invalid ?id (1..40)"}
    courses = loader.load_course_templates()
    course = next((c for c in courses if c["course_id"] == cid), None)
    if not course:
        return {"error": f"course {cid} not in yaml"}
    tags = course.get("homework_tags") or []
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT DISTINCT qb.qb_id, qb.question_type, qb.stem, "
            "qb.options_json, qb.answer, qb.difficulty, qb.analysis "
            "FROM question_bank qb "
            "JOIN question_tags qt ON qt.qb_id = qb.qb_id "
            f"WHERE qt.tag_id IN ({','.join('?' * len(tags))}) "
            "ORDER BY qb.qb_id LIMIT 10",
            tags,
        ).fetchall() if tags else []
        questions = [
            {"qb_id": r[0], "question_type": r[1], "stem": r[2],
             "options_json": r[3], "answer": r[4],
             "difficulty": r[5], "analysis": r[6]}
            for r in rows
        ]
        return {
            "course_id": cid, "layer": course.get("layer"),
            "title": course.get("title"),
            "questions": questions, "count": len(questions),
        }
    finally:
        con.close()


ROUTES = {
    "/api/course/list":    api_course_list,
    "/api/course/session": api_course_session,
    "/api/course/handout": api_course_handout,
    "/api/course/stats":   api_course_stats,
    "/api/course/quiz":    api_course_quiz,
}
