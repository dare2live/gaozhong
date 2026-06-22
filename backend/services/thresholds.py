"""全局阈值读取 (中立 leaf) — 消灭 magic numbers; 任意层可 import 无反向耦合。

单点真相源 = backend/config/thresholds.yaml; get_threshold('a.b', default) 点分路径取值 (lru_cache)。
原实现在 course/loader.py, 但 question_bank/exercise/audit 读阈值会被迫 import course (层级倒置) →
抽到此中立 leaf (只导 yaml/pathlib/functools, 无项目依赖, 零环险); course/loader 再导出保向后兼容。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_PATH = Path(__file__).resolve().parents[1] / "config" / "thresholds.yaml"


@lru_cache(maxsize=1)
def load_thresholds() -> dict:
    """读 thresholds.yaml — 全局阈值配置 (lru_cache; reload 用 load_thresholds.cache_clear())."""
    return yaml.safe_load(_PATH.read_text(encoding="utf-8")) or {}


def get_threshold(path: str, default=None):
    """按点分隔路径读阈值. 例: get_threshold('placement.followup_max', 5)."""
    data = load_thresholds()
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
    return data if data is not None else default
