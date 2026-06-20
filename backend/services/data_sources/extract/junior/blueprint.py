"""跨阶段 deepens 边 — 初中语法 → 高中语法 (域A; inc3, 10维语法蓝图 K12衔接核心).

中考语篇填空 = 高考语法填空考点全集 (zhongkao_gaokao_alignment.md N=2 实证)。
初中 grammar:jr 节点 → 同 label 高中 grammar 节点, 建 `deepens` 边 (低阶→高阶深化)。
label 精确匹配 (59 对实测): 一般过去时的被动语态/不可数名词/定语从句... 初中学牢, 高中深化。
"""
from __future__ import annotations

import json


def load(con) -> dict:
    """初中 grammar → 高中 grammar deepens 边 (label 精确匹配)."""
    jr = con.execute(
        "SELECT concept_id, label FROM nodes WHERE concept_id LIKE 'grammar:jr:%'").fetchall()
    hs = {lab: cid for cid, lab in con.execute(
        "SELECT concept_id, label FROM nodes WHERE node_type='grammar' "
        "AND concept_id NOT LIKE 'grammar:jr:%'").fetchall()}
    ev = json.dumps({"basis": "label_exact", "blueprint": "中考语篇填空↔高考语法填空 10维"},
                    ensure_ascii=False)
    edges = [(jr_cid, hs[lab], "deepens", 1.0, ev) for jr_cid, lab in jr if lab in hs]
    if edges:
        con.executemany(
            "INSERT OR IGNORE INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)", edges)
    return {"deepens边(初中grammar→高中, label匹配)": len(edges)}
