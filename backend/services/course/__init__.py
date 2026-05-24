"""Course service — 40 节分层课程方案 (第五阶段核心交付).

模块分工 (M1 三层严分, M2 插件 dispatch, M3 yaml 外置):
  registry.py       插件注册表 (block_kind / scenario / audit)
  loader.py         yaml 加载 + spec 校验
  lexicon_filter.py 4 层词集 G1/G2/G3/G_FINAL                       R5 R6
  relations.py      ≥3 知识点关联抽取                                R1
  scenarios.py      主题池 + ≥3 场景 + 教材重叠扫 + 政治词扫          R2 R3
  materials.py      合成 materials (graph + trend + qbank + scenarios)
  homework.py       10 题作业 strict tag ⊆ 本节                      R4
  handout.py        讲义 7 段 (hook/复习/核心/关联/真题/场景/作业)
  init_courses.py   init_db 灌课程 + materials (yaml → DB)

铁律 R1-R6 由对应 audit 拦截 (Stop hook 集成).
"""
from __future__ import annotations
