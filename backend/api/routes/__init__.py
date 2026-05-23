"""Auto-merge all ROUTES dicts from sibling modules.

每个 routes/<name>.py 必须暴露 module-level `ROUTES: dict[str, callable]`.
此 __init__ 自动收集, 提供 ALL_ROUTES 给 main.py.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Callable

ALL_ROUTES: dict[str, Callable] = {}

for _mod in pkgutil.iter_modules(__path__):
    if _mod.name.startswith("_"):
        continue
    m = importlib.import_module(f"{__name__}.{_mod.name}")
    r = getattr(m, "ROUTES", None)
    if isinstance(r, dict):
        for path, fn in r.items():
            if path in ALL_ROUTES:
                raise RuntimeError(f"duplicate route {path} in {_mod.name}")
            ALL_ROUTES[path] = fn
