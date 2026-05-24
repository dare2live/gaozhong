"""词形派生关系 (M) — 简单规则版.

规则:
  - 取同 stem (前 4 字符相同) + 不同后缀 (ed/ing/ly/tion/sion/ness/able/ful/less/ment)
  - 短词 (≤4 字母) 不参与 (噪音)
  - 派生方向: 短的 → 长的 (derive_from), 例如 able → ability (但 ability → able 也建)
  - 同 stem cluster 内每对建一条
"""
from __future__ import annotations

import re
from collections import defaultdict

import duckdb

SUFFIX_GROUPS = [
    "ed", "ing", "ly", "tion", "sion", "ness", "able", "ful", "less",
    "ment", "ity", "er", "or", "ive", "ous", "ic", "al", "en",
]


def _stem(word: str) -> str:
    """Naive stem: strip known suffix, lowercase, min 4 chars."""
    w = word.lower()
    for sfx in sorted(SUFFIX_GROUPS, key=len, reverse=True):
        if w.endswith(sfx) and len(w) - len(sfx) >= 4:
            return w[: -len(sfx)]
    return w if len(w) >= 4 else ""


def build_derive_edges(con: duckdb.DuckDBPyConnection) -> int:
    """Group words by stem (≥4 chars), build derive_from edges between members."""
    by_stem = _group_by_stem(con)
    edges = _build_edge_tuples(by_stem)
    con.execute("DELETE FROM edges WHERE relation = 'derive_from'")
    if not edges:
        return 0
    con.executemany(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
        "VALUES (?, ?, 'derive_from', ?, ?)",
        edges,
    )
    return len(edges)


def _group_by_stem(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    words = [r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()]
    by_stem: dict[str, list[str]] = defaultdict(list)
    for w in words:
        s = _stem(w)
        if s:
            by_stem[s].append(w)
    return by_stem


def _build_edge_tuples(by_stem: dict[str, list[str]]) -> list[tuple]:
    edges: list[tuple] = []
    for stem, group in by_stem.items():
        if len(group) < 2:
            continue
        for w1 in group:
            for w2 in group:
                if w1 != w2:
                    edges.append((f"word:{w1}", f"word:{w2}", 0.8,
                                   '{"shared_stem": "%s"}' % stem))
    return edges
