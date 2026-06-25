"""GET /api/graph/popup?id=<concept_id> — 全局浮窗用 1 层关联图 + 真题.

(用户 2026-05-24): 任意 concept 超链接 → 弹联通图 (含真题题目节点) → 可递归扩展.

返回结构:
  {
    "center":    {id, type, label, attrs},
    "related":   [{id, type, label, relation, direction}] — 1 层非真题关联
    "questions": [{qb_id, question_type, stem_preview, year}] — 真题题目节点
  }
"""
from __future__ import annotations

import json

from backend.api.db import db_ro
from backend.services import graph

LIMIT_RELATED = 12
LIMIT_QUESTIONS = 8


def api_graph_popup(qs: dict) -> dict:
    cid = qs.get("id", [None])[0]
    if not cid:
        return {"error": "missing ?id (concept_id)"}
    con = db_ro()
    try:
        center = _fetch_center(con, cid)
        if not center:
            return {"error": f"concept {cid} not found"}
        return {
            "center":    center,
            "related":   _fetch_related(con, cid),
            "questions": _fetch_questions(con, cid),
        }
    finally:
        con.close()


def _fetch_center(con, cid: str) -> dict | None:
    r = con.execute(
        "SELECT concept_id, node_type, label, attrs_json FROM nodes WHERE concept_id = ?",
        [cid],
    ).fetchone()
    if not r:
        return None
    return {"id": r[0], "type": r[1], "label": r[2], "attrs_json": r[3]}


# 关系优先级 (讲课浮窗: 真考点/题型/年份/课标/教材 先于 tests_word 词噪声, 否则真考点被 LIMIT 截掉)
_REL_RANK = {"tests_exam_point": 0, "question_type": 1, "in_year": 2,
             "tests_grammar": 3, "cefr_level": 4, "tests_word": 8}


def _rank(relation: str) -> int:
    return _REL_RANK.get(relation, 5)


def _fetch_related(con, cid: str) -> list[dict]:
    """非真题相关 (outgoing + incoming, 去重). 真题的真考点(tests_exam_point)优先于词噪声.

    图遍历单一入口 (Rule 3): edge↔node 1-hop 走 services.graph.neighbors, 浮窗专属的
    "排除 question 节点 + 关系优先级 + 去重" 留在路由 (展示层关注点, 不污染 graph service)。
    """
    out: list[dict] = []
    seen: set[str] = {cid}

    def _take(rows: list[dict], direction: str) -> bool:
        for r in rows:
            other = r["other"]
            if other in seen or r["node_type"] in (None, "question"):
                continue
            seen.add(other)
            out.append({"id": other, "type": r["node_type"], "label": r["label"],
                        "relation": r["relation"], "direction": direction})
            if len(out) >= LIMIT_RELATED:
                return True
        return False

    # outgoing — 按关系优先级排 (真考点先出, 不被 38 条/题的 tests_word 淹没)
    outs = graph.neighbors(con, cid, direction="out", limit=500)
    outs.sort(key=lambda r: (_rank(r["relation"]), r["label"] or ""))
    if _take(outs, "out"):
        return out
    _take(graph.neighbors(con, cid, direction="in", limit=500), "in")
    return out


def _fetch_questions(con, cid: str) -> list[dict]:
    """真题题目节点 (tests_word / tests_grammar / tests_exam_point 反向).

    INNER JOIN question_bank: 浮窗真题只来自 qbank (157 辽宁真题, §7 锚定); 外省题节点虽在
    tests_word 边里, 但不在 qbank → 不漏进浮窗 (原 LEFT JOIN + NULLS LAST 会把外省以空行带出)。
    #2: 加 tests_exam_point → genre/theme 考点浮窗显真题 (src 在 qbank, 481边/~434命中);
    cognitive_skill 考点的真题是 2021+ 新高考II 辽宁子题 (attrs.subquestion=true, 不在 qbank) →
    走 _fetch_exam_point_subquestions 分支按 nodes.attrs 渲染 (诚实标子题级, 不混进 qbank真题)。
    """
    rows = con.execute(
        "SELECT DISTINCT n.concept_id, q.qb_id, q.question_type, q.stem, "
        "       (SELECT dst_id FROM edges WHERE src_id = n.concept_id AND relation='in_year' "
        "        ORDER BY dst_id LIMIT 1) "
        "FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "INNER JOIN question_bank q ON q.origin_ref = REPLACE(n.concept_id, 'question:', '') "
        "WHERE e.dst_id = ? AND e.relation IN ('tests_word', 'tests_grammar', 'tests_exam_point') "
        "AND n.node_type = 'question' "
        "ORDER BY q.qb_id LIMIT ?",
        [cid, LIMIT_QUESTIONS],
    ).fetchall()
    out: list[dict] = []
    for qcid, qb_id, qtype, stem, year_node in rows:
        out.append({
            "concept_id": qcid,
            "qb_id": qb_id,
            "question_type": qtype,
            "stem_preview": (stem or "")[:120],
            "year": (year_node or "").replace("exam_year:", "") if year_node else None,
        })
    if len(out) < LIMIT_QUESTIONS:
        out += _fetch_exam_point_subquestions(con, cid, LIMIT_QUESTIONS - len(out))
    return out


_QTYPE_ZH = {"reading_comprehension": "阅读理解", "cloze": "完形填空",
             "grammar_filling": "语法填空", "writing": "写作"}


def _fetch_exam_point_subquestions(con, cid: str, limit: int) -> list[dict]:
    """cognitive_skill 等考点的 2021+ 新高考II 辽宁子题 (attrs.subquestion=true, 不在 qbank)。
    诚实: 子题级标注无完整题面, 从 attrs 渲 year/篇/题号/题型; subquestion=true 过滤排除外省整题。"""
    if limit <= 0 or not cid.startswith("exam_point:"):
        return []
    rows = con.execute(
        "SELECT DISTINCT n.concept_id, n.attrs_json "
        "FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "LEFT JOIN question_bank q ON q.origin_ref = REPLACE(n.concept_id, 'question:', '') "
        "WHERE e.dst_id = ? AND e.relation = 'tests_exam_point' "
        "AND n.node_type = 'question' AND q.qb_id IS NULL "
        "AND json_extract_string(n.attrs_json, '$.subquestion') = 'true' "
        "ORDER BY n.concept_id LIMIT ?",
        [cid, limit],
    ).fetchall()
    out: list[dict] = []
    for ccid, attrs in rows:
        try:
            a = json.loads(attrs or "{}")
        except (json.JSONDecodeError, TypeError):
            a = {}
        yr, pl, qn = a.get("year"), a.get("passage_label"), a.get("question_number")
        loc = f"{pl}篇第{qn}题" if pl and qn else "子题"
        out.append({
            "concept_id": ccid,
            "qb_id": None,
            "question_type": _QTYPE_ZH.get(a.get("question_type"), a.get("question_type") or "子题"),
            "stem_preview": f"辽宁{yr or ''} {loc} · 子题级标注(2021+新高考II, 无完整题面)",
            "year": str(yr) if yr else None,
        })
    return out


ROUTES = {"/api/graph/popup": api_graph_popup}
