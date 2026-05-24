"""yaml spec 加载 (M3 数据外置)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "placement_tests.yaml"

VALID_GRADES = {"G1", "G2", "G3"}


@lru_cache(maxsize=1)
def load_specs() -> list[dict]:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    specs = data.get("placement_tests") or []
    for s in specs:
        _validate(s)
    return specs


def get_spec(grade: str) -> dict | None:
    for s in load_specs():
        if s.get("grade") == grade:
            return s
    return None


def _validate(spec: dict) -> None:
    g = spec.get("grade")
    if g not in VALID_GRADES:
        raise ValueError(f"placement spec bad grade: {g}")
    if not spec.get("blocks"):
        raise ValueError(f"{g} blocks empty")
    sc = spec.get("scoring") or {}
    cf = sc.get("consolidate_floor", sc.get("strong_threshold", 0))   # 兼容旧名
    if not (0 < cf < sc.get("pass_threshold", 0) <= 1):
        raise ValueError(f"{g} scoring thresholds invalid")
