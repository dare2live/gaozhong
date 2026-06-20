"""写边即注入血缘 (docs/kg_layer_design.md §3.2; 死亡线#2: 绝不事后回填).

stamp() 是派生边血缘的**唯一构造入口**: 写边那一刻调, version_ids 经 effective_version 当场固化。
回填会取到换版后的错版 (信息已丢) → 所有 build_*/loader 写 evidence_json 前必经 stamp。
"""
from __future__ import annotations

import json

from .versions import effective_version


def stamp(con, *, source_year: int, source_qid: str | None, provenance: str,
          derived_by: str, version_kinds: dict[str, str | None]) -> dict:
    """构造一条派生边的血缘子契约 (放进 edge.evidence_json['lineage']).

    version_kinds: {kind: variant} 该边相关的真相源流, 如
        {"exam_paper": "liaoning_gaokao", "curriculum": "gaozhong"} (真题→考点边);
        {"textbook": "waiyan", "curriculum": "gaozhong"} (教材 locus 边)。
    锚点 (必修a): exam_paper 用 source_year(=exam_year, 精确); curriculum/textbook 用 source_year
        作 cohort 近似 (课标/教材慢变, 当前数据无跨版边界; 真遇 mid-cohort 换版再传精确 enroll_year)。
    无墙钟 built_at: 会破幂等 (rebuild 两遍 diff 须空); derived_by 记提取者身份(稳定)即足以溯"谁产的"。
    """
    version_ids: dict[str, str] = {}
    for kind, variant in (version_kinds or {}).items():
        vid = effective_version(con, kind, source_year, variant=variant)
        if vid:
            version_ids[kind] = vid          # 无匹配诚实不填 (consumer 见缺即知该年该流无登记版本)
    return {"source_year": source_year, "source_qid": source_qid,
            "version_ids": version_ids, "provenance": provenance, "derived_by": derived_by}


def lineage_of(evidence_json) -> dict | None:
    """从 edge.evidence_json 取 lineage 子契约 (消费方 4 路溯源用)."""
    if not evidence_json:
        return None
    d = evidence_json if isinstance(evidence_json, dict) else json.loads(evidence_json)
    return d.get("lineage")
