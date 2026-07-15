"""初中可背诵正文词量门 — 累计沪教(hujiao) ∪ 义教基底, 禁 G_FINAL / 高中卷册.

与 HS lexicon_filter.allowed_words_for(..., "G_FINAL") 刻意分流:
  junior = 小学/义教基底 + cefr 义教 + 教学序累计至当前单元的 hujiao intro 词。
"""
from __future__ import annotations

from functools import lru_cache

import duckdb

from backend.services.course.lexicon_filter import _load_base_vocab, expand_morphology

_VOL_ORD = {"7a": 1, "7b": 2, "8a": 3, "8b": 4, "9a": 5, "9b": 6}


def _vol_ord_sql(alias: str = "volume_key") -> str:
    return (
        f"CASE {alias} "
        "WHEN '7a' THEN 1 WHEN '7b' THEN 2 WHEN '8a' THEN 3 "
        "WHEN '8b' THEN 4 WHEN '9a' THEN 5 WHEN '9b' THEN 6 ELSE 99 END"
    )


@lru_cache(maxsize=64)
def allowed_hujiao_through(
    con: duckdb.DuckDBPyConnection, volume_key: str, unit_number: int
) -> frozenset[str]:
    """累计允许词 (lowercase, 未 morph 展开)."""
    if volume_key not in _VOL_ORD:
        raise ValueError(f"bad volume_key {volume_key!r}")
    unit_number = int(unit_number)
    words: set[str] = set(_load_base_vocab())
    rows = con.execute(
        "SELECT LOWER(word) FROM cefr_vocab WHERE cefr_level = '义教'"
    ).fetchall()
    words.update(r[0] for r in rows)
    ord_sql = _vol_ord_sql()
    rows = con.execute(
        f"""
        SELECT DISTINCT LOWER(word) FROM unit_vocab_intro
        WHERE version_key = 'hujiao'
          AND (
            {ord_sql} < ?
            OR (volume_key = ? AND unit_number <= ?)
          )
        """,
        [_VOL_ORD[volume_key], volume_key, unit_number],
    ).fetchall()
    words.update(r[0] for r in rows)
    return frozenset(words)


def allowed_hujiao_through_expanded(
    con: duckdb.DuckDBPyConnection, volume_key: str, unit_number: int
) -> frozenset[str]:
    return expand_morphology(set(allowed_hujiao_through(con, volume_key, unit_number)))


def reload() -> None:
    allowed_hujiao_through.cache_clear()
