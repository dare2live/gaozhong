"""学生 CSV 导入 (域B 多租户; 从 students.py 抽出, 控 LOC + 隔离租户绑定逻辑).

租户铁律 (审计 BLOCK 修):
  - 导入的学生/班级**绑定到调用方 teacher_id**, 不允许无主写入。
  - IDOR 防护: 已存在且属**别的老师**的 student_id / class_id → 拒绝, 不能跨租户接管。
"""
from __future__ import annotations

from backend.api.db import db_write


def do_csv_import(csv_text: str, teacher_id: str) -> dict:
    """csv 列: student_id,name,school,city,grade,class_id. 全部绑定到 teacher_id."""
    import csv
    import io
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"student_id", "name", "school", "grade"}
    seen_classes: dict[str, tuple] = {}
    n_students = 0
    rejected: list[str] = []
    with db_write() as con:
        for row in reader:
            if not required.issubset(row.keys()):
                return {"error": f"csv 缺列, 必填: {sorted(required)}"}
            sid = row["student_id"]
            cid = (row.get("class_id") or "").strip()
            if _foreign_student(con, sid, teacher_id) or _foreign_class(con, cid, teacher_id):
                rejected.append(sid)
                continue
            if cid and cid not in seen_classes:
                seen_classes[cid] = (row["school"], row["grade"])
            con.execute(
                "INSERT OR REPLACE INTO students "
                "(student_id, name, school, city, grade, class_id, enroll_year, created_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [sid, row["name"], row["school"], row.get("city", ""), row["grade"], cid,
                 _to_int(row.get("enroll_year")), now, "csv_import"],
            )
            n_students += 1
        n_classes = 0
        for cid, (school, grade) in seen_classes.items():
            con.execute(
                "INSERT OR REPLACE INTO classes (class_id, teacher_id, school, grade, name, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [cid, teacher_id, school, grade, f"{school} {grade} {cid}", now],
            )
            n_classes += 1
    out = {"students_imported": n_students, "classes_touched": n_classes, "scoped_by_teacher": teacher_id}
    if rejected:
        out["rejected_cross_tenant"] = rejected  # 跨租户接管已拦截 (IDOR 防护)
    return out


def _foreign_student(con, student_id: str, teacher_id: str) -> bool:
    """student_id 已存在且属别的老师 → True (拒绝接管)."""
    r = con.execute(
        "SELECT c.teacher_id FROM students s LEFT JOIN classes c ON c.class_id = s.class_id "
        "WHERE s.student_id = ?", [student_id]).fetchone()
    return bool(r and r[0] and r[0] != teacher_id)


def _foreign_class(con, class_id: str, teacher_id: str) -> bool:
    if not class_id:
        return False
    r = con.execute("SELECT teacher_id FROM classes WHERE class_id = ?", [class_id]).fetchone()
    return bool(r and r[0] and r[0] != teacher_id)


def _to_int(v) -> int | None:
    try:
        return int(v) if v else None
    except (TypeError, ValueError):
        return None
