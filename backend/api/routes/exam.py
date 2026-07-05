"""真题查询 API.

GET /api/exam_questions — 通用查询 (province / type / year; province 子串匹配, 通用语义)
GET /api/exam/liaoning_browse — 辽宁卷 真题库浏览 (北极星 Phase B 基础库; province 前缀匹配, 坑7-safe 排除非辽宁)
"""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts
from backend.services.extraction.example_text import clean_preview

# 坑(2026-07-05 根因审计): raw_question 定长 SUBSTR 无边界意识, 收口共享 clean_preview
# (SQL 端宽窗留余量, Python 端裁到句末标点 + 需要时补省略号).
_PREVIEW_FETCH_WINDOW = 400


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
           f"SUBSTR(raw_question, 1, {_PREVIEW_FETCH_WINDOW}) AS preview, source_file, source_index "
           "FROM exam_questions")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY year DESC, question_id LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        rows = rows_to_dicts(con.execute(sql, args))
        for r in rows:
            r["preview"] = clean_preview(r["preview"], 200)
        return rows
    finally:
        con.close()


def api_liaoning_browse(qs: dict) -> dict:
    """辽宁卷真题库浏览 (基础库). province 前缀 LIKE '辽宁%' — 坑7-safe (排除"非辽宁;辽宁当年自主命题"等含'辽宁'子串的非辽宁行).

    按年降序分组; 每题带溯源 (source_file/index + paper_type + 题型 + 是否有答案). 供学习者浏览真题 + L3 作业题源。
    """
    year = qs.get("year", [None])[0]
    qtype = qs.get("type", [None])[0]
    where = ["province LIKE '辽宁%'"]
    args: list = []
    if year:
        where.append("year = ?"); args.append(int(year))
    if qtype:
        where.append("question_type = ?"); args.append(qtype)
    con = db_ro()
    try:
        rows = rows_to_dicts(con.execute(
            f"SELECT question_id, year, paper_type, question_type, "
            f"SUBSTR(raw_question,1,{_PREVIEW_FETCH_WINDOW}) AS preview, "
            "CASE WHEN answer IS NOT NULL AND answer <> '' THEN 1 ELSE 0 END AS has_answer, "
            "source_file, source_index "
            "FROM exam_questions WHERE " + " AND ".join(where) +
            " ORDER BY year DESC, question_type, question_id", args))
        for r in rows:
            r["preview"] = clean_preview(r["preview"], 160)
        type_counts = dict(con.execute(
            "SELECT question_type, COUNT(*) FROM exam_questions WHERE province LIKE '辽宁%' GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall())
        all_years = [r[0] for r in con.execute(
            "SELECT DISTINCT year FROM exam_questions WHERE province LIKE '辽宁%' ORDER BY year DESC").fetchall()]
    finally:
        con.close()
    by_year: dict[str, list] = {}
    for r in rows:
        by_year.setdefault(str(r["year"]), []).append(r)
    return {
        "scope": "辽宁卷 (新课标 II 卷, 2015+); province 前缀匹配, 坑7-safe 排除非辽宁",
        "total": len(rows), "years": all_years, "type_counts": type_counts,
        "by_year": by_year, "filters": {"year": year, "type": qtype},
    }


ROUTES = {
    "/api/exam_questions": api_exam_questions,
    "/api/exam/liaoning_browse": api_liaoning_browse,
}
