"""stage 回填 — 高中 word 节点 → at_stage 边 (域A; inc3, 完成 stage 维).

源: stage_refined.jsonl (4329 高中词的 K12 细分 stage; junior_stage_reconcile 产, 已验证)。
为高中词建 at_stage 边连 stage 节点 (inc2 只连了 112 初中独有词; 此处连高中词的真实 K12 阶段)。
校本超纲/课标变形 非纯 stage → 不连 (只连 5 个真阶段)。边是真相, 不动 attrs(避与 exam_coverage stage 冲突)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "junior_high" / "structured"
_REAL_STAGES = {"小学", "初中", "义务教育", "高中必修", "高中选修"}


def load(con) -> dict:
    """stage_refined → 高中 word 节点 at_stage 边 (5 真阶段)."""
    p = S / "stage_refined.jsonl"
    if not p.exists():
        return {"stage回填 at_stage边": 0}
    existing = {r[0] for r in con.execute("SELECT concept_id FROM nodes WHERE node_type='word'").fetchall()}
    edges, stages = [], set()
    for line in p.open(encoding="utf-8"):
        r = json.loads(line)
        st = r.get("refined_stage")
        cid = f"word:{r['word']}"
        if st in _REAL_STAGES and cid in existing:
            stages.add(st)
            edges.append((cid, f"stage:{st}", "at_stage", 1.0, None))
    if stages:
        con.executemany("INSERT OR IGNORE INTO nodes VALUES (?, 'stage', ?, NULL)",
                        [(f"stage:{s}", s) for s in sorted(stages)])
    if edges:
        con.executemany(
            "INSERT OR IGNORE INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)", edges)
    return {"stage回填 at_stage边(高中词)": len(edges), "stages": sorted(stages)}
