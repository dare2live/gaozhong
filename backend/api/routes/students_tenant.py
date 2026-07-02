"""域B 多租户路由 (inc6; 与 students.py 分模块, teacher_id 隔离的端点单列).

/api/students/teachers       — 老师列表 (多租户入口; 无 per-student 数据, 不作用域)
"""
from __future__ import annotations

from backend.api.db import db_ro


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


ROUTES = {
    "/api/students/teachers":       api_students_teachers,
}
