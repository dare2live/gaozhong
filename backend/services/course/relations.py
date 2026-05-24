"""R1 知识点关联 — 每节核心知识点 graph 联通 ≥3 其他.

走 nodes + edges. 关系来源:
  - edges 表 (word→word / word→grammar / grammar→grammar / word→phrase / ...)
  - 同 unit 同时出现 (共现) 作 fallback
"""
from __future__ import annotations

import duckdb

MIN_RELATIONS = 3   # R1 阈值


def related_concepts(con: duckdb.DuckDBPyConnection, concept_id: str, n: int = MIN_RELATIONS) -> list[dict]:
    """返 ≥n 个相关 concept (默认 3). 不够则尽力返."""
    rows = con.execute(
        "SELECT DISTINCT e.dst_id, n.node_type, n.label, e.relation "
        "FROM edges e JOIN nodes n ON n.concept_id = e.dst_id "
        "WHERE e.src_id = ? AND e.dst_id <> e.src_id "
        "LIMIT ?",
        [concept_id, n * 3],   # 取多点便于去重
    ).fetchall()
    out: list[dict] = []
    seen: set[str] = set()
    for tgt, ntype, label, rel in rows:
        if tgt in seen:
            continue
        seen.add(tgt)
        out.append({"id": tgt, "type": ntype, "label": label, "relation": rel})
        if len(out) >= n:
            break
    if len(out) >= n:
        return out
    # fallback 反向边
    rows = con.execute(
        "SELECT DISTINCT e.src_id, n.node_type, n.label, e.relation "
        "FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "WHERE e.dst_id = ? AND e.src_id <> e.dst_id "
        "LIMIT ?",
        [concept_id, n * 3],
    ).fetchall()
    for src, ntype, label, rel in rows:
        if src in seen:
            continue
        seen.add(src)
        out.append({"id": src, "type": ntype, "label": label, "relation": f"~{rel}"})
        if len(out) >= n:
            break
    return out


def count_relations(con: duckdb.DuckDBPyConnection, concept_id: str) -> int:
    """R1 audit 用 — 直接计数 (含正反向去重)."""
    return len(related_concepts(con, concept_id, n=MIN_RELATIONS * 2))
