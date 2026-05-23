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


ROUTES = {
    "/api/graph/stats": api_graph_stats,
    "/api/graph/neighbors": api_graph_neighbors,
}
