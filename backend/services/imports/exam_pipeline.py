"""辽宁高考真题入库编排 — 读 exam_import_pipeline.yaml 逐步调用 (单一入口).

init_db 只调 import_all(con); 加年 = 改 yaml + importer, 不改 init_db (架构 §2 #1).
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[3]
_CFG = ROOT / "backend" / "config" / "exam_import_pipeline.yaml"


def load_steps() -> list[dict[str, Any]]:
    raw = yaml.safe_load(_CFG.read_text(encoding="utf-8")) or {}
    steps = list(raw.get("steps") or [])
    if not steps:
        raise ValueError(f"exam_import_pipeline.yaml 无 steps: {_CFG}")
    for i, s in enumerate(steps):
        for k in ("name", "module", "callable"):
            if not str(s.get(k) or "").strip():
                raise ValueError(f"pipeline step[{i}] missing {k}")
    return steps


def import_all(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """按注册表顺序执行各 importer; 返回 {step_name: result}."""
    out: dict[str, Any] = {}
    for step in load_steps():
        mod = importlib.import_module(step["module"])
        fn = getattr(mod, step["callable"])
        out[step["name"]] = fn(con)
    out["_steps"] = [s["name"] for s in load_steps()]
    return out
