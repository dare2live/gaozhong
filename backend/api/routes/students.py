"""/api/students/* — 5.6 学生档案 (P1).

endpoints:
  /api/students/list                列表 (可 ?class_id=, ?city=, ?grade= 过滤)
  /api/students/get?id=             单生详情 + 班级 + 弱点
  /api/students/classes             班级列表
  /api/students/weakness?id=        学生弱点 heatmap (按 word/grammar)
  /api/students/recommend?id=       弱点 → 推送对应课节
"""
from __future__ import annotations

from backend.api.db import db_ro


def api_students_list(qs: dict) -> dict:
    filters: list[str] = []
    args: list = []
    for k in ("class_id", "city", "grade", "school"):
        v = qs.get(k, [None])[0]
        if v:
            filters.append(f"{k} = ?")
            args.append(v)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    con = db_ro()
    try:
        rows = con.execute(
            f"SELECT student_id, name, school, city, grade, class_id, enroll_year "
            f"FROM students{where} ORDER BY student_id LIMIT 500",
            args,
        ).fetchall()
        return {"students": [_student_dict(r) for r in rows], "count": len(rows)}
    finally:
        con.close()


def api_students_get(qs: dict) -> dict:
    sid = qs.get("id", [None])[0]
    if not sid:
        return {"error": "missing ?id"}
    con = db_ro()
    try:
        r = con.execute(
            "SELECT student_id, name, school, city, grade, class_id, enroll_year "
            "FROM students WHERE student_id = ?",
            [sid],
        ).fetchone()
        if not r:
            return {"error": f"student {sid} not found"}
        answers = con.execute(
            "SELECT COUNT(*), SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) "
            "FROM student_answers WHERE student_id = ?",
            [sid],
        ).fetchone()
        return {
            "student": _student_dict(r),
            "answers": {"total": answers[0] or 0, "correct": answers[1] or 0},
        }
    finally:
        con.close()


def api_students_classes(qs: dict) -> dict:
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT c.class_id, c.school, c.grade, c.name, "
            "(SELECT COUNT(*) FROM students s WHERE s.class_id = c.class_id) AS n "
            "FROM classes c ORDER BY c.school, c.grade, c.class_id"
        ).fetchall()
        return {
            "classes": [
                {"class_id": r[0], "school": r[1], "grade": r[2], "name": r[3], "n_students": r[4]}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def api_students_weakness(qs: dict) -> dict:
    sid = qs.get("id", [None])[0]
    if not sid:
        return {"error": "missing ?id"}
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT concept_id, weakness_score, sample_n "
            "FROM student_weakness WHERE student_id = ? "
            "ORDER BY weakness_score DESC LIMIT 30",
            [sid],
        ).fetchall()
        return {
            "weakness": [
                {"concept_id": r[0], "score": r[1], "sample_n": r[2],
                 "kind": r[0].split(":", 1)[0]}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def api_students_recommend(qs: dict) -> dict:
    """弱点 → 推荐 课节 (concept_id 在哪节出现 → 推该节)."""
    sid = qs.get("id", [None])[0]
    if not sid:
        return {"error": "missing ?id"}
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT DISTINCT c.course_id, c.layer, c.title, sw.concept_id, sw.weakness_score "
            "FROM student_weakness sw "
            "JOIN course_materials cm ON cm.ref_id = sw.concept_id "
            "JOIN courses c ON c.course_id = cm.course_id "
            "WHERE sw.student_id = ? "
            "ORDER BY sw.weakness_score DESC LIMIT 20",
            [sid],
        ).fetchall()
        return {
            "recommendations": [
                {"course_id": r[0], "layer": r[1], "title": r[2],
                 "weak_concept": r[3], "score": r[4]}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def _student_dict(r: tuple) -> dict:
    return {"student_id": r[0], "name": r[1], "school": r[2],
            "city": r[3], "grade": r[4], "class_id": r[5], "enroll_year": r[6]}


ROUTES = {
    "/api/students/list":      api_students_list,
    "/api/students/get":       api_students_get,
    "/api/students/classes":   api_students_classes,
    "/api/students/weakness":  api_students_weakness,
    "/api/students/recommend": api_students_recommend,
}
