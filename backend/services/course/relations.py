"""R1 知识点关联 — 每节核心知识点 graph 联通 ≥3 其他.

Fallback 阶梯 (前者不够再走后者):
  (1) outgoing edges                — 直接 src→dst
  (2) incoming edges                — dst→src 反向
  (3) co-test fan-out (词专属)      — 同题被考过的其它词
  (4) same cefr_level (兜底)        — 同教学阶段词/语法
"""
from __future__ import annotations

import duckdb

MIN_RELATIONS = 3


def related_concepts(con: duckdb.DuckDBPyConnection, concept_id: str, n: int = MIN_RELATIONS) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = {concept_id}
    if _fill_outgoing(con, concept_id, out, seen, n): return out
    if _fill_incoming(con, concept_id, out, seen, n): return out
    if _fill_co_tested(con, concept_id, out, seen, n): return out
    _fill_same_cefr(con, concept_id, out, seen, n)
    return out


def count_relations(con: duckdb.DuckDBPyConnection, concept_id: str) -> int:
    return len(related_concepts(con, concept_id, n=MIN_RELATIONS * 2))


def _fill_outgoing(con, concept_id: str, out: list, seen: set, n: int) -> bool:
    for tgt, ntype, label, rel in con.execute(
        "SELECT DISTINCT e.dst_id, n.node_type, n.label, e.relation "
        "FROM edges e JOIN nodes n ON n.concept_id = e.dst_id "
        "WHERE e.src_id = ? AND e.dst_id <> e.src_id LIMIT ?",
        [concept_id, n * 3],
    ).fetchall():
        if tgt in seen: continue
        seen.add(tgt)
        out.append({"id": tgt, "type": ntype, "label": label, "relation": rel})
        if len(out) >= n: return True
    return False


def _fill_incoming(con, concept_id: str, out: list, seen: set, n: int) -> bool:
    for src, ntype, label, rel in con.execute(
        "SELECT DISTINCT e.src_id, n.node_type, n.label, e.relation "
        "FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "WHERE e.dst_id = ? AND e.src_id <> e.dst_id LIMIT ?",
        [concept_id, n * 3],
    ).fetchall():
        if src in seen: continue
        seen.add(src)
        out.append({"id": src, "type": ntype, "label": label, "relation": f"~{rel}"})
        if len(out) >= n: return True
    return False


def _fill_co_tested(con, concept_id: str, out: list, seen: set, n: int) -> bool:
    for cid, ntype, label in con.execute(
        "SELECT DISTINCT e2.dst_id, n.node_type, n.label "
        "FROM edges e1 JOIN edges e2 ON e1.src_id = e2.src_id AND e2.relation = 'tests_word' "
        "JOIN nodes n ON n.concept_id = e2.dst_id "
        "WHERE e1.dst_id = ? AND e1.relation = 'tests_word' AND e2.dst_id <> e1.dst_id "
        "LIMIT ?",
        [concept_id, n * 3],
    ).fetchall():
        if cid in seen: continue
        seen.add(cid)
        out.append({"id": cid, "type": ntype, "label": label, "relation": "co_tested"})
        if len(out) >= n: return True
    return False


def _fill_same_cefr(con, concept_id: str, out: list, seen: set, n: int) -> None:
    """通用 same-cefr fan-out: 走 edges(relation='cefr_level') 反向找同级 nodes.

    对 word + grammar 都适用 (无论 nodes.attrs 里有无 cefr_level 字段).
    """
    ntype = concept_id.split(":", 1)[0]
    for cid, label, cefr in con.execute(
        "SELECT e2.src_id, n.label, e1.dst_id "
        "FROM edges e1 JOIN edges e2 ON e1.dst_id = e2.dst_id "
        "JOIN nodes n ON n.concept_id = e2.src_id "
        "WHERE e1.src_id = ? AND e1.relation = 'cefr_level' "
        "AND e2.relation = 'cefr_level' AND e2.src_id <> e1.src_id "
        "AND n.node_type = ? LIMIT ?",
        [concept_id, ntype, n * 2],
    ).fetchall():
        if cid in seen: continue
        seen.add(cid)
        out.append({"id": cid, "type": ntype, "label": label, "relation": f"same_cefr({cefr.split(':')[-1]})"})
        if len(out) >= n: return


def _node_cefr(con: duckdb.DuckDBPyConnection, concept_id: str) -> str | None:
    r = con.execute(
        "SELECT JSON_EXTRACT(attrs_json, '$.cefr_level') FROM nodes WHERE concept_id = ?",
        [concept_id],
    ).fetchone()
    if r and r[0]:
        return r[0].strip('"')
    r = con.execute(
        "SELECT dst_id FROM edges WHERE src_id = ? AND relation = 'cefr_level' LIMIT 1",
        [concept_id],
    ).fetchone()
    if r and r[0] and r[0].startswith("cefr_level:"):
        return r[0].split(":", 1)[1]
    return None
