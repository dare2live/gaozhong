"""停用词加载 (单一来源, Rule 5 共享) — autotag / tests_word 边构建剔除功能词.

规则数据化在 backend/config/stopwords.yaml (项目 §3.5), 本模块只读不 hardcode.
被 question_bank.loader.autotag 与 links_extra.build_tests_word 复用.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_CACHE: set[str] | None = None
_PATH = Path(__file__).resolve().parent.parent / "config" / "stopwords.yaml"


def load_stopwords() -> set[str]:
    """英语停用词集合 (小写). 缓存一次."""
    global _CACHE
    if _CACHE is None:
        data = yaml.safe_load(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
        _CACHE = {str(w).lower() for w in (data.get("english_stopwords") or [])}
    return _CACHE


def content_tokens(tokens: set[str], vocab: set[str]) -> set[str]:
    """题面 token ∩ 词表 − 停用词 = 实词考点 (autotag/tests_word 共用)."""
    return (tokens & vocab) - load_stopwords()
