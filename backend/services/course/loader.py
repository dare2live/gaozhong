"""M3 yaml 加载 — backend/config/*.yaml → dict, 带 spec 校验.

外置数据:
  course_templates.yaml     40 节 spec
  theme_pool.yaml           50 主题
  political_blacklist.yaml  政治词
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

VALID_LAYERS = {"G1", "G2", "G3", "G_FINAL"}
VALID_BLOCK_KINDS = {
    "vocab", "grammar", "reading", "cloze", "gramfill",
    "applied", "narrative", "mock", "listening",
}
VALID_ITEM_KINDS = {"word", "grammar", "phrase", "exam_question",
                    "reading_section", "listening_clip"}


@lru_cache(maxsize=1)
def load_course_templates() -> list[dict]:
    """读 course_templates.yaml 返 list[course]. 失败抛 ValueError (M5 spec 校验)."""
    path = CONFIG_DIR / "course_templates.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    courses = data.get("courses") or []
    for c in courses:
        _validate_course(c)
    return courses


@lru_cache(maxsize=1)
def load_theme_pool() -> dict:
    """读 theme_pool.yaml 返 {category_id: {label, refs, themes}}."""
    data = yaml.safe_load((CONFIG_DIR / "theme_pool.yaml").read_text(encoding="utf-8")) or {}
    return {c["id"]: c for c in (data.get("categories") or [])}


@lru_cache(maxsize=1)
def load_political_blacklist() -> list[str]:
    data = yaml.safe_load((CONFIG_DIR / "political_blacklist.yaml").read_text(encoding="utf-8")) or {}
    return [w.lower() for w in (data.get("trigger_words") or [])]


def _validate_course(c: dict) -> None:
    cid = _validate_id(c)
    _validate_enums(cid, c)
    _validate_block_order(cid, c)
    _validate_items(cid, c.get("core_items") or [])


def _validate_id(c: dict) -> int:
    cid = c.get("course_id")
    if not isinstance(cid, int) or not (1 <= cid <= 40):
        raise ValueError(f"course_id must be 1..40, got {cid}")
    return cid


def _validate_enums(cid: int, c: dict) -> None:
    if c.get("layer") not in VALID_LAYERS:
        raise ValueError(f"#{cid} bad layer {c.get('layer')}, want one of {VALID_LAYERS}")
    if c.get("block_kind") not in VALID_BLOCK_KINDS:
        raise ValueError(f"#{cid} bad block_kind {c.get('block_kind')}")


def _validate_block_order(cid: int, c: dict) -> None:
    bo = c.get("block_order")
    if not isinstance(bo, int) or not (1 <= bo <= 10):
        raise ValueError(f"#{cid} block_order must be 1..10")


def _validate_items(cid: int, items: list[dict]) -> None:
    if not items:
        raise ValueError(f"#{cid} core_items empty")
    for it in items:
        if it.get("kind") not in VALID_ITEM_KINDS:
            raise ValueError(f"#{cid} core_items bad kind {it.get('kind')}")
        if not it.get("position"):
            raise ValueError(f"#{cid} core_items missing position (R6)")
        if it.get("year") not in (1, 2, 3, 99):
            raise ValueError(f"#{cid} core_items year must be 1|2|3|99 (R6)")


def reload_all() -> None:
    """Test only — clear lru_cache so config edits picked up."""
    load_course_templates.cache_clear()
    load_theme_pool.cache_clear()
    load_political_blacklist.cache_clear()
