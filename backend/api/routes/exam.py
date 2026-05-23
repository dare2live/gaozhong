"""GET /api/exam_questions — 真题查询 (province / type / year)."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_exam_questions(qs: dict) -> list[dict]:
    province = qs.get("province", [None])[0]
    qtype = qs.get("type", [None])[0]
    year = qs.get("year", [None])[0]
    try:
        limit = min(int(qs.get("limit", ["20"])[0]), 200)
    except ValueError:
        limit = 20
    where, args = [], []
    if province:
        where.append("province LIKE ?"); args.append(f"%{province}%")
    if qtype:
        where.append("question_type = ?"); args.append(qtype)
    if year:
        where.append("year = ?"); args.append(int(year))
    sql = ("SELECT question_id, year, province, paper_type, question_type, "
           "SUBSTR(raw_question, 1, 200) AS preview, source_file, source_index "
           "FROM exam_questions")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY year DESC, question_id LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


ROUTES = {"/api/exam_questions": api_exam_questions}
