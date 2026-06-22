"""cefr_level → K12 stage 展示标签 单点 (中立 leaf, 无依赖).

穷尽扫描: exam_dictionary._LEVEL_STAGE 与 exam_coverage._STAGE 各写一份共享 3 键 → 收口此处。
义教/必修/选必 = 课标三级 (cefr_vocab.cefr_level 真值); 校本扩展/课标变形 是 exam_coverage 覆盖审计
专用的合成 stage 值, 不在此 canonical 3 键内, 由该模块本地扩展 (避把审计专用值泄漏进 dictionary 域)。
"""
from __future__ import annotations

CEFR_LEVEL_STAGE = {
    "义教": "义务教育",
    "必修": "高中必修",
    "选必": "高中选修",
}
