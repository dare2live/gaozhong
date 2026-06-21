"""D0 计数基线读取 (判断值数据化 §3.5; 用户 no-hardcode 指令).

基线值集中 backend/config/d0_baselines.yaml, 本模块按 key 取值 — 检查脚本用 B('cefr_vocab')
代替硬编码 3052。改基线改 yaml 不动代码。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_PATH = Path(__file__).resolve().parents[2] / "backend" / "config" / "d0_baselines.yaml"


@lru_cache(maxsize=1)
def _load() -> dict:
    return (yaml.safe_load(_PATH.read_text(encoding="utf-8")) or {}).get("baselines", {})


def B(key: str) -> int:
    """基线值 (int)。key 缺失即 KeyError(防静默用错 key)."""
    return int(_load()[key]["value"])
