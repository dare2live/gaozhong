"""Graph query — 单一图查询入口 (架构 §0 Rule 3).

API / exercise generator / 其他 service 都走这里, 不直接 SELECT edges.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Optional

import duckdb

from backend.services.thresholds import get_threshold

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
    # tiebreak by neighbor id (other) + relation — 等权重时仍确定 (D0 100% 可复现;
    # 全 weight=1.0 的高 in-degree 节点 ORDER BY weight 零区分度, 无 tiebreak 则 LIMIT 截谁不定)
    sql += " ORDER BY e.weight DESC NULLS LAST, other, e.relation LIMIT ?"
    args.append(limit)
    cur = con.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _incident_edges(con, cid: str, rel_filter: str, relation_whitelist: Optional[list[str]]) -> list[tuple]:
    """一个节点的全部关联边 (出+入), 按 rel_filter 过滤 (供 expand BFS 单步用)."""
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
    return cur.fetchall()


def _expand_step(
    con, cid: str, depth: int, rel_filter: str, relation_whitelist: Optional[list[str]],
    seen: set[str], out_edges: list[dict], out_nodes: list[dict], max_nodes: int,
) -> list[tuple[str, int]]:
    """BFS 单步: 拉一个节点的关联边, 记边, 未见过的邻居入队 (mutates seen/out_edges/out_nodes)."""
    next_queue_items: list[tuple[str, int]] = []
    for src_id, dst_id, rel, w in _incident_edges(con, cid, rel_filter, relation_whitelist):
        other = dst_id if src_id == cid else src_id
        out_edges.append({"src": src_id, "dst": dst_id, "relation": rel, "weight": w})
        if other not in seen and len(seen) < max_nodes:
            seen.add(other)
            n = _node(con, other)
            if n:
                out_nodes.append(n)
            next_queue_items.append((other, depth + 1))
    return next_queue_items


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
        for item in _expand_step(con, cid, depth, rel_filter, relation_whitelist,
                                  seen, out_edges, out_nodes, max_nodes):
            queue.append(item)
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


def _relation_weight_case(weights: dict[str, float]) -> tuple[str, list]:
    """构造 CASE WHEN relation=? THEN ? ... ELSE 1.0 END (参数化防注入; 未列出的relation默认权重1.0)."""
    if not weights:
        return "1.0", []
    parts, args = [], []
    for rel, w in weights.items():
        parts.append("WHEN relation = ? THEN ?")
        args.extend([rel, float(w)])
    return f"CASE {' '.join(parts)} ELSE 1.0 END", args


def _ranked_skeleton(con, types: list[str], label_rels: list[str], full_max: int, top_n: int,
                      relation_weights: dict[str, float] | None = None) -> list[tuple]:
    """按 node_type 分层排名: 类型总数<=full_max 全入选, 否则按relation加权degree(排除label_rels)取Top-N.

    坑(2026-07-06 数据关联设计审查): 原对所有relation无差别SUM(COUNT(*))求和, tests_word这类词
    噪声边(边总数占比最大)压倒性主导排名, tests_grammar(仅18条边)在Top-40骨架里生存率0/18——
    与 graph_popup.py::_REL_RANK 已验证的"真考点优先, 词噪声降权"思路自相矛盾(同项目两套排序
    逻辑各说各话, 违反Rule1单一计算点)。权重表数据化进 thresholds.yaml graph_atlas.relation_weights
    (不hardcode, 呼应CLAUDE.md §3.5), 未列出的relation默认权重1.0。

    坑(对抗验证发现纯加权求和不够): 仅做 SUM(d*w) 混合排序时, 一个阅读理解passage仍可能有
    上百条 tests_word 边(即便×0.5降权), 总分依然碾压只有几条 tests_grammar/tests_exam_point
    边(即便×2/×4加权)的语法/改错类小题——权重倍数在这种量级差距下不够, 排名结果不变(实测
    grammar边生存率仍0/18)。故改成两级排序: 先按"高价值关系(weight>1)的加权量"排, 打平才看
    总加权度数——只要摸到任意一条真考点/语法边, 就不会被词频量淹没, 而不是指望权重系数硬扛。
    """
    relation_weights = relation_weights or {}
    w_case, w_args = _relation_weight_case(relation_weights)
    lr_ph = ",".join(["?"] * len(label_rels)) if label_rels else "NULL"
    type_ph = ",".join(["?"] * len(types))
    return con.execute(
        f"""
        WITH deg AS (
            SELECT concept_id,
                   SUM(d * w) AS degree,
                   SUM(CASE WHEN w > 1.0 THEN d * w ELSE 0 END) AS signal_degree
            FROM (
                SELECT src_id AS concept_id, COUNT(*) AS d, {w_case} AS w FROM edges
                    WHERE relation NOT IN ({lr_ph}) GROUP BY src_id, relation
                UNION ALL
                SELECT dst_id AS concept_id, COUNT(*) AS d, {w_case} AS w FROM edges
                    WHERE relation NOT IN ({lr_ph}) GROUP BY dst_id, relation
            ) x GROUP BY concept_id
        ),
        totals AS (SELECT node_type, COUNT(*) AS total FROM nodes GROUP BY node_type),
        ranked AS (
            SELECT n.concept_id, n.node_type, n.label, n.attrs_json,
                   COALESCE(deg.degree, 0) AS degree, t.total,
                   ROW_NUMBER() OVER (PARTITION BY n.node_type
                                      ORDER BY COALESCE(deg.signal_degree, 0) DESC,
                                               COALESCE(deg.degree, 0) DESC, n.concept_id) AS rn
            FROM nodes n
            LEFT JOIN deg ON deg.concept_id = n.concept_id
            JOIN totals t ON t.node_type = n.node_type
            WHERE n.node_type IN ({type_ph})
        )
        SELECT concept_id, node_type, label, attrs_json, degree, total
        FROM ranked WHERE total <= ? OR rn <= ?
        """,
        [*w_args, *label_rels, *w_args, *label_rels, *types, full_max, top_n],
    ).fetchall()


def _skeleton_edges(con, ids: list[str], label_rels: list[str]) -> list[dict]:
    """两端均在骨架内、且非 label_rels 的边 (骨架的真实关系边)."""
    id_ph = ",".join(["?"] * len(ids))
    lr_ph = ",".join(["?"] * len(label_rels)) if label_rels else "NULL"
    return [
        {"src": r[0], "dst": r[1], "relation": r[2], "weight": r[3]}
        for r in con.execute(
            f"""SELECT src_id, dst_id, relation, weight FROM edges
                WHERE src_id IN ({id_ph}) AND dst_id IN ({id_ph}) AND relation NOT IN ({lr_ph})""",
            [*ids, *ids, *label_rels],
        ).fetchall()
    ]


def _word_labels(con, word_ids: list[str], label_rels: list[str]) -> dict[str, dict]:
    """word 节点的标签属性 (stage/cefr_level), 只查骨架内节点, 不碰全表 3277/3160 行."""
    if not word_ids or not label_rels:
        return {}
    wp = ",".join(["?"] * len(word_ids))
    rp = ",".join(["?"] * len(label_rels))
    by_node: dict[str, dict] = {}
    for src_id, relation, dst_label in con.execute(
        f"""SELECT e.src_id, e.relation, n.label FROM edges e JOIN nodes n ON n.concept_id = e.dst_id
            WHERE e.src_id IN ({wp}) AND e.relation IN ({rp})""",
        [*word_ids, *label_rels],
    ).fetchall():
        by_node.setdefault(src_id, {})[relation] = dst_label
    return by_node


def _label_relation_dst_types(con: duckdb.DuckDBPyConnection, label_rels: list[str]) -> list[str]:
    """label_relations(边关系名)的 dst 侧真实 node_type 集合 (单一计算点; 前端不猜名字对应关系)."""
    if not label_rels:
        return []
    rp = ",".join("?" * len(label_rels))
    rows = con.execute(
        f"""SELECT DISTINCT n.node_type FROM edges e JOIN nodes n ON n.concept_id = e.dst_id
            WHERE e.relation IN ({rp})""",
        label_rels,
    ).fetchall()
    return sorted(r[0] for r in rows)


def _build_type_meta(ranked: list[tuple]) -> dict[str, dict]:
    """按 node_type 汇总 shown/total/capped (ranked 行的 index 1=node_type, index 5=total)."""
    type_meta: dict[str, dict] = {}
    for r in ranked:
        m = type_meta.setdefault(r[1], {"total": r[5], "shown": 0})
        m["shown"] += 1
    for m in type_meta.values():
        m["capped"] = m["shown"] < m["total"]
    return type_meta


def _attach_word_labels(con, nodes_out: list[dict], label_rels: list[str]) -> None:
    """word 节点挂 labels (stage/cefr_level 等属性), mutates nodes_out in place."""
    word_ids = [n["concept_id"] for n in nodes_out if n["node_type"] == "word"]
    by_node = _word_labels(con, word_ids, label_rels)
    for n in nodes_out:
        if n["concept_id"] in by_node:
            n["labels"] = by_node[n["concept_id"]]


def degree_summary(
    con: duckdb.DuckDBPyConnection,
    node_types: Optional[list[str]] = None,
    top_n_per_type: Optional[int] = None,
) -> dict:
    """全景图谱骨架: 按 node_type 分层取全部/degree Top-N 节点 + 两端均入选的骨架边.

    单一计算点: 复用 nodes/edges 两表 (与 neighbors/expand 同源, Rule1)。node_type 总数
    <= graph_atlas.full_display_max_count 的类型全展示 (小规模不会形成毛球); 超过的按
    真实连接数 (排除 label_relations) 取 Top-N, 避免 word/question 这类大类型淹没骨架。

    label_relations (at_stage/cefr_level, 见 thresholds.yaml graph_atlas 注释) 是
    fan-out=1 的"标签"边非真实 N:M 关系 — 实测这两类关系的 dst 侧各只有 4-5 个节点却各
    吸附 650-800 条边, 原样画成边会把力导向图拉成放射状伪中心, 故排除在骨架边外, 只挂
    node["labels"] 供前端做颜色编码 (数据仍是真值, 只是渲染层从"边"降级为"属性")。
    """
    label_rels: list[str] = get_threshold("graph_atlas.label_relations", []) or []
    full_max = get_threshold("graph_atlas.full_display_max_count", 200)
    top_n = top_n_per_type or get_threshold("graph_atlas.default_top_n_per_type", 40)
    relation_weights: dict = get_threshold("graph_atlas.relation_weights", {}) or {}
    types = node_types or [r[0] for r in con.execute("SELECT DISTINCT node_type FROM nodes").fetchall()]
    # 坑(2026-07-05 数据可视化审计): label_relations 是"边关系名"(at_stage/cefr_level), 不等于
    # "node_type 名"(at_stage 的 dst node_type 实为 "stage", 只 cefr_level 恰好同名) — 前端此前
    # 各自硬编码 {"stage","cefr_level"} 两份猜测 dst 侧 node_type, 违反单一计算点。此处直接查 dst 侧
    # 真实 node_type 一次算出, API 显式回传, 前端只读不猜。
    attribute_only_types: list[str] = _label_relation_dst_types(con, label_rels)

    ranked = _ranked_skeleton(con, types, label_rels, full_max, top_n, relation_weights)
    nodes_out = [{"concept_id": r[0], "node_type": r[1], "label": r[2], "attrs": r[3], "degree": r[4]} for r in ranked]
    if not nodes_out:
        return {"nodes": [], "edges": [], "type_meta": {}, "label_relations": label_rels,
                "attribute_only_node_types": attribute_only_types}

    type_meta = _build_type_meta(ranked)

    ids = [n["concept_id"] for n in nodes_out]
    edges_out = _skeleton_edges(con, ids, label_rels)

    _attach_word_labels(con, nodes_out, label_rels)

    return {"nodes": nodes_out, "edges": edges_out, "type_meta": type_meta, "label_relations": label_rels,
            "attribute_only_node_types": attribute_only_types}
