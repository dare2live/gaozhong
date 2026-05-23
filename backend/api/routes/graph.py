"""GET /api/graph/* — 知识图谱查询 (走 backend.services.graph 单一入口)."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services import graph as gsvc


def api_graph_stats(_qs: dict) -> dict:
    con = db_ro()
    try:
        return gsvc.stats(con)
    finally:
        con.close()


def api_graph_neighbors(qs: dict) -> list[dict]:
    node = qs.get("node", [""])[0]
    if not node:
        return []
    rel = qs.get("relation", [None])[0]
    direction = qs.get("direction", ["out"])[0]
    try:
        limit = min(int(qs.get("limit", ["50"])[0]), 500)
    except ValueError:
        limit = 50
    con = db_ro()
    try:
        return gsvc.neighbors(con, node, rel, direction, limit)
    finally:
        con.close()


def api_graph_subgraph(qs: dict) -> dict:
    """BFS expand from a concept_id, returns nodes+edges subgraph (for SVG render)."""
    start = qs.get("node", [""])[0]
    if not start:
        return {"nodes": [], "edges": []}
    try:
        depth = min(int(qs.get("depth", ["2"])[0]), 3)
    except ValueError:
        depth = 2
    try:
        max_nodes = min(int(qs.get("max_nodes", ["60"])[0]), 200)
    except ValueError:
        max_nodes = 60
    rel = qs.get("relation", [None])
    rel_list = rel if rel != [None] and rel else None
    con = db_ro()
    try:
        return gsvc.expand(con, start, max_depth=depth,
                            relation_whitelist=rel_list, max_nodes=max_nodes)
    finally:
        con.close()


ROUTES = {
    "/api/graph/stats": api_graph_stats,
    "/api/graph/neighbors": api_graph_neighbors,
    "/api/graph/subgraph": api_graph_subgraph,
}
