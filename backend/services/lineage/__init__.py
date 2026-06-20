"""KG层横切机制: PIT版本 + 数据血缘 + 幂等重推导 (docs/kg_layer_design.md §3).

- versions.py: source_versions 注册表 + effective_version 单一 PIT 计算点 (收口"按年对齐哪版").
- stamp.py:   写边那一刻注入血缘子契约 (version_ids 当场固化, 绝不回填).
- rebuild.py: 逐年追加幂等重推导编排 (P1, 首次逐年追加痛了再建).
"""
from .versions import effective_version, load_versions, version_anchor_year
from .stamp import stamp, lineage_of

__all__ = ["effective_version", "load_versions", "version_anchor_year", "stamp", "lineage_of"]
