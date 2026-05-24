"""M2 插件注册表 — block_kind / scenario_kind / audit_kind 全走这里.

禁 `if/elif kind == 'vocab': ...` 长链.

用法:
    from . import registry
    @registry.block('vocab')
    def handle_vocab(...): ...

    handler = registry.get_block('vocab')
"""
from __future__ import annotations

from typing import Callable

_BLOCK: dict[str, Callable] = {}
_SCENARIO: dict[str, Callable] = {}
_HANDOUT_SEG: dict[str, Callable] = {}


def block(kind: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        _BLOCK[kind] = fn
        return fn
    return deco


def scenario(kind: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        _SCENARIO[kind] = fn
        return fn
    return deco


def handout_seg(name: str) -> Callable:
    """讲义段 — hook / review / core / relations / exam_trace / practice / homework."""
    def deco(fn: Callable) -> Callable:
        _HANDOUT_SEG[name] = fn
        return fn
    return deco


def get_block(kind: str) -> Callable | None:
    return _BLOCK.get(kind)


def get_scenario(kind: str) -> Callable | None:
    return _SCENARIO.get(kind)


def get_handout_seg(name: str) -> Callable | None:
    return _HANDOUT_SEG.get(name)


def list_blocks() -> list[str]:
    return sorted(_BLOCK.keys())


def list_handout_segs() -> list[str]:
    return sorted(_HANDOUT_SEG.keys())
