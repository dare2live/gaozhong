"""域B 多租户路由 (inc6; 与 students.py 分模块, teacher_id 隔离的端点单列).

/api/students/teachers       — 老师列表 (多租户入口)
/api/students/class_weakness — 班级 × 真考点弱点聚合 (单算点下沉 weakness service)
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.api.routes.students import _ep_dimension


def api_students_teachers(qs: dict) -> dict:
    """老师列表 (域B 多租户入口; 前端选老师后 /api/students/* 带 ?teacher_id= 作用域)."""
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT t.teacher_id, t.name, t.school, "
            "(SELECT COUNT(*) FROM classes c WHERE c.teacher_id = t.teacher_id) AS n_cls "
            "FROM teachers t ORDER BY t.teacher_id").fetchall()
        return {"teachers": [{"teacher_id": r[0], "name": r[1], "school": r[2], "n_classes": r[3]}
                             for r in rows], "count": len(rows)}
    finally:
        con.close()


def api_students_class_weakness(qs: dict) -> dict:
    """班级学情热力 (域B; class × exam_point 聚合弱点; ?class_id= 必填, 单算点下沉 weakness)."""
    cid = (qs.get("class_id", [None]) or [None])[0]
    if not cid:
        return {"error": "missing ?class_id"}
    con = db_ro()
    try:
        rows = con.execute(
            "SELECT w.concept_id, COALESCE(n.label, w.concept_id) AS label, "
            "       AVG(w.weakness_score) AS avg_score, COUNT(DISTINCT w.student_id) AS n_stu, "
            "       SUM(w.sample_n) AS total_n "
            "FROM student_weakness w "
            "JOIN students s ON s.student_id = w.student_id AND s.class_id = ? "
            "LEFT JOIN nodes n ON n.concept_id = w.concept_id "
            "GROUP BY w.concept_id, label ORDER BY avg_score DESC LIMIT 30", [cid]
        ).fetchall()
        n_stu = con.execute("SELECT COUNT(*) FROM students WHERE class_id = ?", [cid]).fetchone()[0]
        return {
            "class_id": cid, "n_students": n_stu,
            "data_status": "示例数据 · 待真实答题量 (weakness 派生结构就绪, 现 demo seed)",
            "weakness": [
                {"concept_id": r[0], "label": r[1], "avg_score": round(r[2], 3),
                 "n_weak_students": r[3], "total_sample": r[4], "dimension": _ep_dimension(r[0])}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


ROUTES = {
    "/api/students/teachers":       api_students_teachers,
    "/api/students/class_weakness": api_students_class_weakness,
}
