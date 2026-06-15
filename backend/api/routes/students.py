"""/api/students/* — 5.6 学生档案 (P1).

endpoints:
  /api/students/list                列表 (可 ?class_id=, ?city=, ?grade= 过滤)
  /api/students/get?id=             单生详情 + 班级 + 弱点
  /api/students/classes             班级列表
  /api/students/weakness?id=        学生弱点 (按 exam_point 真考点; 2026-06-16 改, 返 label/dimension)
  /api/students/recommend?id=       弱点 → 推送对应课节
"""
from __future__ import annotations

from backend.api.db import db_ro, db_write
from backend.services import weakness as weakness_svc


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


def api_students_weakness_recompute(qs: dict) -> dict:
    """重算弱点 — 从 student_answers 真实数据算 (4.7.E)."""
    sid = qs.get("id", [None])[0]
    with db_write() as con:
        if sid:
            return weakness_svc.recompute_one(con, sid)
        return weakness_svc.recompute_all(con)


def api_students_import_csv(qs: dict, body: bytes | None = None) -> dict:
    """POST csv 导入学生 (4.7.D). csv 列: student_id,name,school,city,grade,class_id.

    behaviour:
      - 同 student_id 已存在 → UPDATE
      - 新 class_id → 同时建 classes 行 (school + grade 取首批学生)
    """
    if not body:
        return {"error": "POST 需要 csv body (Content-Type: text/csv)"}
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    return _do_csv_import(text)


def _do_csv_import(csv_text: str) -> dict:
    import csv
    import io
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"student_id", "name", "school", "grade"}
    seen_classes: dict[str, tuple] = {}
    n_students = 0
    with db_write() as con:
        for row in reader:
            if not required.issubset(row.keys()):
                return {"error": f"csv 缺列, 必填: {sorted(required)}"}
            cid = (row.get("class_id") or "").strip()
            if cid and cid not in seen_classes:
                seen_classes[cid] = (row["school"], row["grade"])
            con.execute(
                "INSERT OR REPLACE INTO students "
                "(student_id, name, school, city, grade, class_id, enroll_year, created_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [row["student_id"], row["name"], row["school"],
                 row.get("city", ""), row["grade"], cid,
                 _to_int(row.get("enroll_year")), now, "csv_import"],
            )
            n_students += 1
        # 自动建班级 (如不存在)
        n_classes = 0
        for cid, (school, grade) in seen_classes.items():
            con.execute(
                "INSERT OR REPLACE INTO classes (class_id, school, grade, name, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                [cid, school, grade, f"{school} {grade} {cid}", now],
            )
            n_classes += 1
    return {"students_imported": n_students, "classes_touched": n_classes}


def _to_int(v) -> int | None:
    try:
        return int(v) if v else None
    except (TypeError, ValueError):
        return None


ROUTES = {
    "/api/students/list":               api_students_list,
    "/api/students/get":                api_students_get,
    "/api/students/classes":            api_students_classes,
    "/api/students/weakness":           api_students_weakness,
    "/api/students/weakness_recompute": api_students_weakness_recompute,
    "/api/students/recommend":          api_students_recommend,
    "/api/students/import_csv":         api_students_import_csv,
}
