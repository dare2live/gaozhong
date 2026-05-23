"""⭐ 图谱治理 audit (用户 2026-05-23 顶层关注).

3 类:
  1. node_orphans  — 节点存在但无任何 edge (按 node_type 容忍度不同)
  2. edge_validity — 边的 src/dst 必须能 JOIN 回 nodes 表
  3. grammar_dag   — grammar cat_of 应是 DAG, 不能有环
  4. relation_dictionary — 所有 edges.relation 必须在白名单内 (防止 typo 静默)
"""
from __future__ import annotations

import duckdb

from ._common import finding

# Canonical relation 白名单 (links/build_* 实际产出的 relation)
# 加新 relation 时**先来更新这张表**, 否则 edges 写入会标 FAIL.
ALLOWED_RELATIONS = {
    "cefr_level": "word|grammar → cefr_level",
    "cat_of": "grammar(child) → grammar(parent)",
    "city_uses": "city → publisher",
    "allowed_in_ln": "publisher → subject",
    "vol_in_ver": "volume → publisher",
    "in_year": "question → exam_year",
    "question_type": "question → qtype",
    "in_volume": "unit → volume",
    # 后续 STEP 2/3 添加 (现在加进来, 防止启用时 FAIL):
    "introduces_word": "unit → word",
    "uses_grammar": "unit → grammar",
    "theme_of_unit": "unit → theme",
    "tests_word": "question → word",
    "tests_grammar": "question → grammar",
    "tests_theme": "question → theme",
    "co_occurs": "word ↔ word",
    "topic_aligned": "unit ↔ unit",
    "introduces_phrase": "unit → phrase",
    "derive_from": "word ↔ word (同 stem)",
}

# 哪些节点类型可以"孤儿" (e.g. cefr_level 是标签节点, 终点, 没 outgoing 是正常)
# subject = allowed_in_ln 的 dst 标签
ORPHAN_TOLERATED_TYPES = {"cefr_level", "qtype", "exam_year", "subject"}


# 按 node_type 的孤儿率容忍 (≤ N% 算 OK, ≤ M% 算 WARN, 否则 FAIL).
# 没列出的 type 默认 0 容忍.
ORPHAN_RATIO_TOLERATED = {
    "theme": (0.80, 0.90),    # 课标主题部分允许不教 (level3 子主题大量孤儿合理)
    "exam_year": (1.0, 1.0),  # 标签节点
    "qtype": (1.0, 1.0),
    "cefr_level": (1.0, 1.0),
    "subject": (1.0, 1.0),
}


def audit_node_orphans(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """节点 in_degree + out_degree = 0 视为孤儿. 按 type 比例容忍."""
    rows = con.execute("""
        SELECT n.node_type, n.concept_id,
               COALESCE((SELECT COUNT(*) FROM edges e WHERE e.src_id = n.concept_id), 0) AS od,
               COALESCE((SELECT COUNT(*) FROM edges e WHERE e.dst_id = n.concept_id), 0) AS id
        FROM nodes n
    """).fetchall()
    total_by_type: dict[str, int] = {}
    orphan_by_type: dict[str, int] = {}
    orphan_samples: list[tuple[str, str]] = []
    for nt, cid, od, id_ in rows:
        total_by_type[nt] = total_by_type.get(nt, 0) + 1
        if od + id_ == 0:
            orphan_by_type[nt] = orphan_by_type.get(nt, 0) + 1
            if len(orphan_samples) < 10:
                orphan_samples.append((nt, cid))
    # severity per type
    severities: list[str] = []
    type_status: dict[str, str] = {}
    for nt, total in total_by_type.items():
        n_orphan = orphan_by_type.get(nt, 0)
        if n_orphan == 0:
            type_status[nt] = "OK"; continue
        ratio = n_orphan / max(1, total)
        ok_th, warn_th = ORPHAN_RATIO_TOLERATED.get(nt, (0.0, 0.0))
        if ratio <= ok_th: type_status[nt] = "OK"
        elif ratio <= warn_th: type_status[nt] = "WARN"
        else: type_status[nt] = "FAIL"
        severities.append(type_status[nt])
    overall = "FAIL" if "FAIL" in severities else ("WARN" if "WARN" in severities else "OK")
    return [finding("graph_orphans", overall,
                    target="按 node_type 的孤儿率",
                    expected="theme≤40% OK / ≤70% WARN; 其它 type 0",
                    actual=str(type_status),
                    note=f"orphan_by_type={orphan_by_type}; sample={orphan_samples[:5]}")]


def audit_edge_validity(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """edges.src_id / dst_id 必须在 nodes.concept_id 中存在."""
    bad_src = con.execute("""
        SELECT COUNT(*) FROM edges e
        WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id = e.src_id)
    """).fetchone()[0]
    bad_dst = con.execute("""
        SELECT COUNT(*) FROM edges e
        WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id = e.dst_id)
    """).fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    out = [finding("graph_edge_validity", "FAIL" if bad_src else "OK",
                   target="edges.src_id ⊆ nodes", expected="0",
                   actual=str(bad_src), note=f"of total {total}"),
           finding("graph_edge_validity", "FAIL" if bad_dst else "OK",
                   target="edges.dst_id ⊆ nodes", expected="0",
                   actual=str(bad_dst))]
    return out


def audit_relation_dictionary(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """所有 edges.relation 必须在 ALLOWED_RELATIONS."""
    actual = {row[0] for row in con.execute("SELECT DISTINCT relation FROM edges").fetchall()}
    unknown = actual - set(ALLOWED_RELATIONS)
    return [finding("graph_relation_dict",
                    "FAIL" if unknown else "OK",
                    target="edges.relation ⊆ whitelist",
                    expected=str(sorted(ALLOWED_RELATIONS)),
                    actual=str(sorted(actual)),
                    note=f"unknown={sorted(unknown)}" if unknown else None)]


def audit_grammar_dag(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """grammar cat_of 应是 DAG, 不允许环. 用 ancestors 闭包检测."""
    # Simple: BFS from each child, if visit self → cycle.
    parents = dict(con.execute(
        "SELECT grammar_item_id, parent_id FROM grammar_items WHERE parent_id IS NOT NULL"
    ).fetchall())
    cycles = []
    for start in list(parents):
        seen = set()
        cur = start
        for _ in range(50):
            cur = parents.get(cur)
            if cur is None:
                break
            if cur == start or cur in seen:
                cycles.append(start)
                break
            seen.add(cur)
    return [finding("graph_grammar_dag",
                    "FAIL" if cycles else "OK",
                    target="grammar cat_of acyclic",
                    expected="0 cycle", actual=str(len(cycles)),
                    note=str(cycles[:5]) if cycles else None)]
