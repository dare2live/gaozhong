"""命题近年加权 — 单点真相源读取 backend/config/year_weights.yaml。

坑(2026-07-04 死代码审计): 原随 backend/services/constitution.py (设计宪法, API/前端已于
2026-07-02 下线) 一并声明, 但本模块两个函数是仅有的真实消费点(trend_engine/milestone_b_rebuild/
exam_pattern_extractor/model_capability_audit 4 处 import); constitution 表/check_compliance()/
enforce_before_generation() 从未被任何存活生成流程调用(0 wired), 已删。本模块独立拆出, 避免连坐删除。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_YW_PATH = Path(__file__).resolve().parent.parent / "config" / "year_weights.yaml"


@lru_cache(maxsize=1)
def _yw_raw() -> dict:
    return yaml.safe_load(_YW_PATH.read_text(encoding="utf-8")) or {}


def year_weights() -> dict[int, float]:
    """命题近年加权 — 单点真相源 backend/config/year_weights.yaml。
    改权重改 yaml 不动代码; 每年6月滚动。返回新 dict, 调用方可安全改。"""
    return {int(y): float(w) for y, w in (_yw_raw().get("weights") or {}).items()}


def year_weight_default() -> float:
    """未列年份 (2021前旧课标期) 兜底权重 (yaml default, 默认 0.5)。"""
    return float(_yw_raw().get("default", 0.5))
