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

from backend.api.db import db_ro

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


def _fetch_related(con, cid: str) -> list[dict]:
    """非真题相关 (outgoing + incoming, 去重, 排除 question_type)."""
    out: list[dict] = []
    seen: set[str] = {cid}
    # outgoing
    for tgt, ntype, label, rel in con.execute(
        "SELECT DISTINCT e.dst_id, n.node_type, n.label, e.relation "
        "FROM edges e JOIN nodes n ON n.concept_id = e.dst_id "
        "WHERE e.src_id = ? AND n.node_type <> 'question' "
        "LIMIT ?",
        [cid, LIMIT_RELATED * 2],
    ).fetchall():
        if tgt in seen: continue
        seen.add(tgt)
        out.append({"id": tgt, "type": ntype, "label": label,
                    "relation": rel, "direction": "out"})
        if len(out) >= LIMIT_RELATED: return out
    # incoming
    for src, ntype, label, rel in con.execute(
        "SELECT DISTINCT e.src_id, n.node_type, n.label, e.relation "
        "FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "WHERE e.dst_id = ? AND n.node_type <> 'question' "
        "LIMIT ?",
        [cid, LIMIT_RELATED * 2],
    ).fetchall():
        if src in seen: continue
        seen.add(src)
        out.append({"id": src, "type": ntype, "label": label,
                    "relation": rel, "direction": "in"})
        if len(out) >= LIMIT_RELATED: return out
    return out


def _fetch_questions(con, cid: str) -> list[dict]:
    """真题题目节点 (tests_word / tests_grammar 反向)."""
    rows = con.execute(
        "SELECT DISTINCT n.concept_id, q.qb_id, q.question_type, q.stem, "
        "       (SELECT dst_id FROM edges WHERE src_id = n.concept_id AND relation='in_year' LIMIT 1) "
        "FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "LEFT JOIN question_bank q ON q.origin_ref = REPLACE(n.concept_id, 'question:', '') "
        "WHERE e.dst_id = ? AND e.relation IN ('tests_word', 'tests_grammar') "
        "AND n.node_type = 'question' "
        "ORDER BY q.qb_id NULLS LAST LIMIT ?",
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
    return out


ROUTES = {"/api/graph/popup": api_graph_popup}
