"""/api/students/* — 5.6 学生档案 (P1, 域B 多租户).

全 per-student 端点按 teacher_id 隔离 (老师只见自己班级链下学生);
归属判定单一执行点在 [[_tenant]] (审计 BLOCK 修 2026-06-20: 原先 6/7 端点裸读 = 越权)。

endpoints (均需 ?teacher_id=):
  /api/students/list                列表 (该老师班级链下; 可再 ?class_id=/city/grade/school 过滤)
  /api/students/get?id=             单生详情 (owns 校验, 非自己学生 → forbidden)
  /api/students/classes             班级列表 (该老师)
  /api/students/weakness?id=        学生弱点 (owns 校验; 按 exam_point 真考点)
  /api/students/recommend?id=       弱点 → 推送课节 (owns 校验)
  /api/students/import_csv          导入 (实现下沉 [[students_csv]], 租户绑定 + IDOR 防护)
"""
from __future__ import annotations

from backend.api.db import db_ro, db_write
from backend.api.routes import _tenant
from backend.api.routes.students_csv import do_csv_import
from backend.services import weakness as weakness_svc


def api_students_list(qs: dict) -> dict:
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    filters = ["c.teacher_id = ?"]
    args: list = [tid]
    for k in ("class_id", "city", "grade", "school"):
        v = qs.get(k, [None])[0]
        if v:
            filters.append(f"s.{k} = ?")
            args.append(v)
    where = " WHERE " + " AND ".join(filters)
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT s.student_id, s.name, s.school, s.city, s.grade, s.class_id, s.enroll_year "
            "FROM students s JOIN classes c ON c.class_id = s.class_id"
            f"{where} ORDER BY s.student_id LIMIT 500",
            args,
        ).fetchall()
        return {"scoped_by_teacher": tid,
                "students": [_student_dict(r) for r in rows], "count": len(rows)}
    finally:
        con.close()


def api_students_get(qs: dict) -> dict:
    sid = qs.get("id", [None])[0]
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    if not sid:
        return {"error": "missing ?id"}
    con = db_ro()
    try:
        if not _tenant.owns_student(con, tid, sid):
            return _tenant.DENIED
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
    """班级列表 (域B 隔离: 老师只见自己班级; ?teacher_id= 必填)."""
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT c.class_id, c.school, c.grade, c.name, c.teacher_id, "
            "(SELECT COUNT(*) FROM students s WHERE s.class_id = c.class_id) AS n "
            "FROM classes c WHERE c.teacher_id = ? "
            "ORDER BY c.school, c.grade, c.class_id", [tid]
        ).fetchall()
        return {
            "scoped_by_teacher": tid,
            "classes": [
                {"class_id": r[0], "school": r[1], "grade": r[2], "name": r[3],
                 "teacher_id": r[4], "n_students": r[5]}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def api_students_weakness(qs: dict) -> dict:
    sid = qs.get("id", [None])[0]
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    if not sid:
        return {"error": "missing ?id"}
    con = db_ro()
    try:
        if not _tenant.owns_student(con, tid, sid):
            return _tenant.DENIED
        # join nodes 取可读 label (薄弱环节=exam_point真考点, 非裸 concept_id); 维度=concept_id 中段
        rows = con.execute(
            "SELECT w.concept_id, COALESCE(n.label, w.concept_id) AS label, "
            "       w.weakness_score, w.sample_n "
            "FROM student_weakness w LEFT JOIN nodes n ON n.concept_id = w.concept_id "
            "WHERE w.student_id = ? ORDER BY w.weakness_score DESC LIMIT 30",
            [sid],
        ).fetchall()
        return {
            "weakness": [
                {"concept_id": r[0], "label": r[1], "score": r[2], "sample_n": r[3],
                 "dimension": _ep_dimension(r[0])}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def _ep_dimension(concept_id: str) -> str:
    """exam_point:theme_l2:环境保护 → 'theme_l2' (考点维度); 非 exam_point → 前缀."""
    parts = concept_id.split(":")
    if parts[0] == "exam_point" and len(parts) >= 3:
        return parts[1]
    return parts[0]


def api_students_recommend(qs: dict) -> dict:
    """弱点 → 推荐 课节 (concept_id 在哪节出现 → 推该节; owns 校验)."""
    sid = qs.get("id", [None])[0]
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    if not sid:
        return {"error": "missing ?id"}
    con = db_ro()
    try:
        if not _tenant.owns_student(con, tid, sid):
            return _tenant.DENIED
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


def api_students_weakness_recompute(qs: dict) -> dict:
    """重算单生弱点 — 从 student_answers 真实数据算 (4.7.E); 必 owns 校验, 不开全局重算 API."""
    sid = qs.get("id", [None])[0]
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    if not sid:
        return {"error": "missing ?id (按生重算; 全局重算属维护操作 init_db, 不经此 API)"}
    with db_write() as con:
        if not _tenant.owns_student(con, tid, sid):
            return _tenant.DENIED
        return weakness_svc.recompute_one(con, sid)


def api_students_import_csv(qs: dict, body: bytes | None = None) -> dict:
    """POST csv 导入学生 (4.7.D; 租户绑定 + IDOR 防护下沉 [[students_csv]])."""
    tid = _tenant.get_teacher(qs)
    if not tid:
        return _tenant.MISSING
    if not body:
        return {"error": "POST 需要 csv body (Content-Type: text/csv)"}
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    return do_csv_import(text, tid)


ROUTES = {
    "/api/students/list":               api_students_list,
    "/api/students/get":                api_students_get,
    "/api/students/classes":            api_students_classes,
    "/api/students/weakness":           api_students_weakness,
    "/api/students/weakness_recompute": api_students_weakness_recompute,
    "/api/students/recommend":          api_students_recommend,
    "/api/students/import_csv":         api_students_import_csv,
}
