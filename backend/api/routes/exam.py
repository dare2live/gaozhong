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


def _question_tags(con, question_ids: list[str]) -> dict[str, list[dict]]:
    """question_id → [{type, concept_id, label}] (tests_grammar/tests_exam_point 边反查, 一次批量查, 防N+1).

    坑(2026-07-06 数据关联设计审查): 97%的辽宁真题至少有一条相关边, 但真题库页从未展示——
    数据现成只是没接, edges.src_id = 'question:'+question_id (已核验编码), tests_grammar 的
    dst_id='grammar:<grammar_item_id>' 需 JOIN grammar_items 取人话label; tests_exam_point 的
    dst_id='exam_point:<dim>:<label>' label 已内嵌在id里, 不需要JOIN。
    """
    if not question_ids:
        return {}
    prefixed = ["question:" + q for q in question_ids]
    ph = ",".join(["?"] * len(prefixed))
    rows = con.execute(
        f"SELECT e.src_id, e.relation, e.dst_id, gi.label AS grammar_label "
        f"FROM edges e LEFT JOIN grammar_items gi ON gi.grammar_item_id = REPLACE(e.dst_id, 'grammar:', '') "
        f"WHERE e.relation IN ('tests_grammar', 'tests_exam_point') AND e.src_id IN ({ph})",
        prefixed,
    ).fetchall()
    out: dict[str, list[dict]] = {}
    for src_id, relation, dst_id, grammar_label in rows:
        qid = src_id[len("question:"):]
        label = grammar_label if relation == "tests_grammar" else dst_id.split(":", 2)[-1]
        out.setdefault(qid, []).append({"type": relation, "concept_id": dst_id, "label": label or dst_id})
    return out


def api_liaoning_browse(qs: dict) -> dict:
    """辽宁卷真题库浏览 (基础库). province 前缀 LIKE '辽宁%' — 坑7-safe (排除"非辽宁;辽宁当年自主命题"等含'辽宁'子串的非辽宁行).

    按年降序分组; 每题带溯源 (source_file/index + paper_type + 题型 + 是否有答案) + 命中的语法点/考点
    (tags, 坑: 真题库页原是四子页里唯一的数据孤岛, 补上后可深链到教材语法/考点关联)。供学习者浏览真题 + L3 作业题源。
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
        tags_by_qid = _question_tags(con, [r["question_id"] for r in rows])
        for r in rows:
            r["preview"] = clean_preview(r["preview"], 160)
            r["tags"] = tags_by_qid.get(r["question_id"], [])
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
