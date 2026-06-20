"""stage 节点 + at_stage 边 (域A; inc2: 连初中节点防孤儿 + materialize stage 维).

为 inc2 新建的初中独有 word + grammar:jr 节点连到 stage 节点(否则 word/grammar 孤儿率>0, orphan门红)。
stage 节点动态建(只建实际出现的 stage, 防孤儿 stage 节点)。inc3 再把高中词回填 + 连 at_stage。
"""
from __future__ import annotations

import json


def load(con) -> dict:
    """初中节点 → stage 节点 + at_stage 边."""
    rows = con.execute(
        "SELECT concept_id, attrs_json FROM nodes "
        "WHERE (node_type='word' AND attrs_json LIKE '%junior_curriculum%') "
        "OR concept_id LIKE 'grammar:jr:%'"
    ).fetchall()
    edges, stages = [], set()
    for cid, attrs in rows:
        st = json.loads(attrs or "{}").get("stage")
        if st:
            stages.add(st)
            edges.append((cid, f"stage:{st}", "at_stage", 1.0, None))
    if stages:
        con.executemany("INSERT OR IGNORE INTO nodes VALUES (?, 'stage', ?, NULL)",
                        [(f"stage:{s}", s) for s in sorted(stages)])
    if edges:
        con.executemany(
            "INSERT OR IGNORE INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)", edges)
    return {"stage 节点": len(stages), "at_stage 边(初中节点)": len(edges)}
