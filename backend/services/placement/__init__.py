"""摸底测验卷 service (D 用户 2026-05-25).

3 套 G1/G2/G3 摸底卷, 题库化 spec, runtime 抽题 (R4 R5 兼容 R6 教材位置).

模块:
  loader.py     yaml spec 加载
  generator.py  按 spec 从 question_bank 抽题 (覆盖 ≥N 不同 concept)
  scorer.py     答案 → 正确率 → layer 推荐 + 弱点 concepts
  api 路由 → backend/api/routes/placement.py

D0 100% 准: layer 推荐 + 弱点 必须可 trace 真题 tag + nodes (不估算).
"""
from __future__ import annotations

from . import loader, generator, scorer    # re-export

__all__ = ["loader", "generator", "scorer"]
