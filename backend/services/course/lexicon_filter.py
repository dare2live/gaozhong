"""R5 R6 词汇分层 + 教材位置 — 4 层词集 + 反查 position.

层映射 (volume_key → layer):
  必修 1, 2          → G1   (高一 ~1200 词)
  必修 3, 选必 1, 2  → G2   (高二, G1 ∪)
  选必 3, 4          → G3   (高三, G2 ∪)
  cefr_vocab 其它    → G_FINAL  (高考前突击, G3 ∪ 课标补充)
"""
from __future__ import annotations

from functools import lru_cache

import duckdb

# volume_key → year_level (1/2/3)
VOLUME_TO_YEAR = {
    "bixiu_1": 1, "bixiu_2": 1,
    "bixiu_3": 2, "xuanze_1": 2, "xuanze_2": 2,
    "xuanze_3": 3, "xuanze_4": 3,
}

# year → layer (累计)
YEAR_TO_LAYERS = {
    1: ["G1", "G2", "G3", "G_FINAL"],         # G1 词在所有层都允许
    2: ["G2", "G3", "G_FINAL"],
    3: ["G3", "G_FINAL"],
    99: ["G_FINAL"],                            # 课标补充只在 G_FINAL
}

VOLUME_LABEL = {
    "bixiu_1": "必修1", "bixiu_2": "必修2", "bixiu_3": "必修3",
    "xuanze_1": "选必1", "xuanze_2": "选必2",
    "xuanze_3": "选必3", "xuanze_4": "选必4",
}

VERSION_LABEL = {"waiyan": "外研", "renjiao": "人教"}


@lru_cache(maxsize=4)
def allowed_words(layer: str) -> frozenset[str]:
    """返 layer 允许的所有词 (lowercase). R5 strict ⊆ 校验用."""
    raise RuntimeError("call allowed_words_for(con, layer) — needs DB con")


CEFR_LEVELS_PER_LAYER = {
    "G1":      ["义教"],
    "G2":      ["义教", "必修"],
    "G3":      ["义教", "必修", "选必"],
    "G_FINAL": ["义教", "必修", "选必"],   # cefr_vocab 实际无"选修", G_FINAL ≡ G3 词集 (差异在真题密集 + 模拟卷, 非新词)
}


def allowed_words_for(con: duckdb.DuckDBPyConnection, layer: str) -> set[str]:
    """R5 词集 = unit_vocab_intro (按 volume → year) ∪ cefr_vocab (按 cefr_level)."""
    if layer not in ("G1", "G2", "G3", "G_FINAL"):
        raise ValueError(f"bad layer {layer}")
    words: set[str] = set()
    # (1) 教材展开词
    volumes: list[str] = [v for v, y in VOLUME_TO_YEAR.items() if layer in YEAR_TO_LAYERS[y]]
    if volumes:
        placeholders = ",".join("?" * len(volumes))
        rows = con.execute(
            f"SELECT DISTINCT LOWER(word) FROM unit_vocab_intro "
            f"WHERE volume_key IN ({placeholders})",
            volumes,
        ).fetchall()
        words.update(r[0] for r in rows)
    # (2) 课标 cefr_vocab (按 cefr_level 映射到 layer)
    cefr_levels = CEFR_LEVELS_PER_LAYER.get(layer, [])
    if cefr_levels:
        placeholders = ",".join("?" * len(cefr_levels))
        rows = con.execute(
            f"SELECT LOWER(word) FROM cefr_vocab WHERE cefr_level IN ({placeholders})",
            cefr_levels,
        ).fetchall()
        words.update(r[0] for r in rows)
    return words


def word_position(con: duckdb.DuckDBPyConnection, word: str) -> tuple[int, str] | None:
    """R6: 反查词的 (year_level, textbook_position).

    优先教材位置 (year 1/2/3 + 'XXX·必修Y·U?·Vocabulary'),
    否则课标补充 (year 99 + '课标·3500词表'),
    否则 None.
    """
    w = word.lower()
    row = con.execute(
        "SELECT version_key, volume_key, unit_number "
        "FROM unit_vocab_intro WHERE LOWER(word) = ? "
        "ORDER BY volume_key, unit_number LIMIT 1",
        [w],
    ).fetchone()
    if row:
        ver, vol, uno = row
        year = VOLUME_TO_YEAR.get(vol, 0)
        pos = f"{VERSION_LABEL.get(ver, ver)}·{VOLUME_LABEL.get(vol, vol)}·U{uno}·Vocabulary"
        return year, pos
    row = con.execute("SELECT 1 FROM cefr_vocab WHERE LOWER(word) = ? LIMIT 1", [w]).fetchone()
    if row:
        return 99, "课标·3500词表"
    return None


def grammar_position(con: duckdb.DuckDBPyConnection, grammar_id: str) -> tuple[int, str] | None:
    """R6 for grammar — 走 grammar_items 的 cefr_level 推 year."""
    row = con.execute(
        "SELECT cefr_level, label FROM grammar_items WHERE grammar_item_id = ? LIMIT 1",
        [grammar_id],
    ).fetchone()
    if not row:
        return None
    cefr, label = row
    year = {"义教": 1, "必修": 2, "选必": 3, "选修": 99}.get(cefr, 99)
    pos = f"课标·语法·{cefr}·{label}"
    return year, pos


def check_words_in_layer(con: duckdb.DuckDBPyConnection, words: list[str], layer: str) -> list[str]:
    """R5 strict: 返回不在 layer 词集的词 (陌生词列表). 空 = 通过."""
    allowed = allowed_words_for(con, layer)
    return [w for w in words if w.lower() not in allowed]
