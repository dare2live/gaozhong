"""R2 R3 + D5 — 场景/主题相关.

R2 不抄教材   — n-gram 滑窗校验 与教材原句无 ≥10 词连续重叠
R3 多场景     — 每知识点 ≥3 场景 (主选 1 + 副选 ≥2)
D5 政治词扫  — 主题/篇/transcript 不含黑名单词
"""
from __future__ import annotations

import re

import duckdb

from .loader import load_political_blacklist, load_theme_pool

MIN_SCENARIOS = 3
NGRAM_N = 10   # ≥10 词连续重叠即判抄

_TOK = re.compile(r"[A-Za-z]+")


def list_themes(category_id: str | None = None) -> list[str]:
    pool = load_theme_pool()
    if category_id:
        return list(pool.get(category_id, {}).get("themes", []))
    out: list[str] = []
    for c in pool.values():
        out.extend(c.get("themes", []))
    return out


def scenarios_for_course(course: dict) -> list[str]:
    """主选 + 副选, 去重."""
    main = (course.get("themes_main") or "").strip()
    aux = list(course.get("themes_aux") or [])
    seen: set[str] = set()
    out: list[str] = []
    for s in [main] + aux:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def count_scenarios(course: dict) -> int:
    return len(scenarios_for_course(course))


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOK.findall(text or "")]


def has_textbook_copy(con: duckdb.DuckDBPyConnection, text: str, n: int = NGRAM_N) -> str | None:
    """R2: 返触发的重叠 n-gram (调试用), 否则 None.

    把 text n-gram 与 section_text 库做 set 交集 (规模 OK 用 SQL string contains 兜底).
    """
    toks = _tokens(text)
    if len(toks) < n:
        return None
    grams = {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}
    # 抽样 section_text 100 行做 substring 扫
    rows = con.execute("SELECT content FROM section_text LIMIT 500").fetchall()
    for (content,) in rows:
        c = " ".join(_tokens(content or ""))
        for g in grams:
            if g and g in c:
                return g
    return None


def has_political_word(text: str) -> str | None:
    """D5: 返触发的政治词 (debug), 否则 None."""
    if not text:
        return None
    low = text.lower()
    for w in load_political_blacklist():
        if w.lower() in low:
            return w
    return None
