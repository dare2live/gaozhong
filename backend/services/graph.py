"""Graph query — 单一图查询入口 (架构 §0 Rule 3).

API / exercise generator / 其他 service 都走这里, 不直接 SELECT edges.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent


def open_db(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=read_only)


def neighbors(
    con: duckdb.DuckDBPyConnection,
    concept_id: str,
    relation: Optional[str] = None,
    direction: str = "out",
    limit: int = 200,
) -> list[dict]:
    """List direct neighbors with relation + weight."""
    if direction == "out":
        sql = ("SELECT e.dst_id AS other, n.node_type, n.label, e.relation, e.weight, e.evidence_json "
               "FROM edges e LEFT JOIN nodes n ON n.concept_id = e.dst_id "
               "WHERE e.src_id = ?")
    elif direction == "in":
        sql = ("SELECT e.src_id AS other, n.node_type, n.label, e.relation, e.weight, e.evidence_json "
               "FROM edges e LEFT JOIN nodes n ON n.concept_id = e.src_id "
               "WHERE e.dst_id = ?")
    else:
        raise ValueError("direction must be 'in' or 'out'")
    args: list = [concept_id]
    if relation:
        sql += " AND e.relation = ?"
        args.append(relation)
    sql += " ORDER BY e.weight DESC NULLS LAST LIMIT ?"
    args.append(limit)
    cur = con.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def expand(
    con: duckdb.DuckDBPyConnection,
    start: str,
    max_depth: int = 2,
    relation_whitelist: Optional[list[str]] = None,
    max_nodes: int = 200,
) -> dict:
    """BFS subgraph (capped). Returns {nodes:[...], edges:[...]}."""
    seen: set[str] = {start}
    out_edges: list[dict] = []
    out_nodes: list[dict] = []
    queue: deque = deque([(start, 0)])
    rel_filter = ""
    if relation_whitelist:
        rel_filter = " AND e.relation IN (" + ",".join(["?"] * len(relation_whitelist)) + ")"

    # bootstrap node
    n = _node(con, start)
    if n:
        out_nodes.append(n)
    else:
        return {"nodes": [], "edges": []}

    while queue and len(seen) < max_nodes:
        cid, depth = queue.popleft()
        if depth >= max_depth:
            continue
        args = [cid, cid]
        if rel_filter:
            args.extend(relation_whitelist)
            args.extend(relation_whitelist)
        cur = con.execute(
            f"""
            SELECT src_id, dst_id, relation, weight FROM edges
            WHERE (src_id = ? OR dst_id = ?){rel_filter}
            """,
            args,
        )
        for src_id, dst_id, rel, w in cur.fetchall():
            other = dst_id if src_id == cid else src_id
            out_edges.append({"src": src_id, "dst": dst_id, "relation": rel, "weight": w})
            if other not in seen and len(seen) < max_nodes:
                seen.add(other)
                n = _node(con, other)
                if n:
                    out_nodes.append(n)
                queue.append((other, depth + 1))
    return {"nodes": out_nodes, "edges": out_edges}


def _node(con: duckdb.DuckDBPyConnection, cid: str) -> Optional[dict]:
    row = con.execute(
        "SELECT concept_id, node_type, label, attrs_json FROM nodes WHERE concept_id = ?",
        [cid],
    ).fetchone()
    if not row:
        return None
    return {"concept_id": row[0], "node_type": row[1], "label": row[2], "attrs": row[3]}


def stats(con: duckdb.DuckDBPyConnection) -> dict:
    by_type = dict(con.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type").fetchall())
    by_rel = dict(con.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC").fetchall())
    return {"nodes": by_type, "edges": by_rel,
            "total_nodes": sum(by_type.values()), "total_edges": sum(by_rel.values())}
