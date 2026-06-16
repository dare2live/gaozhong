"""词汇 ↔ 真题 单一计算点 (架构 §0 Rule 1).

"单元引入词" 与 "某词的真题考查频次 / 题目溯源" 是派生事实, 只在这里算一次。
原先散在 recommend.unit_exam_alignment + lesson_plan._word_exam_trace 各算一遍 (双算债),
备课整合若再写一遍 = 第三套。收口到此, 三方 (recommend / lesson_plan / 备课整合) 同调。

真相源 = edges (introduces_word / tests_word) + exam_questions, 不读中间派生表。
"""
from __future__ import annotations

import duckdb


def unit_introduced_words(con: duckdb.DuckDBPyConnection, unit_id: str) -> list[str]:
    """该单元 introduces_word 边引入的词 (去 'word:' 前缀, 不去重 — 调用方按需 set)."""
    rows = con.execute(
        "SELECT dst_id FROM edges WHERE src_id = ? AND relation = 'introduces_word'",
        [unit_id],
    ).fetchall()
    return [r[0].split(":", 1)[1] for r in rows]


def word_exam_frequency(con: duckdb.DuckDBPyConnection, word: str) -> int:
    """该词被真题考查的真实频次 (tests_word 边数, 不截断)."""
    return con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation = 'tests_word' AND dst_id = ?",
        [f"word:{word}"],
    ).fetchone()[0]


def unit_word_frequencies(con: duckdb.DuckDBPyConnection, unit_id: str) -> dict[str, int]:
    """单元每个引入词的真题考查频次 (一次 GROUP BY, 灭 N+1; 含 0 频词).

    单一计算点批量版: word 列表 + 频次都从此出, recommend/lesson_plan 不各自 N 次 COUNT。
    """
    uniq = sorted(set(unit_introduced_words(con, unit_id)))
    if not uniq:
        return {}
    keys = [f"word:{w}" for w in uniq]
    ph = ",".join("?" * len(keys))
    rows = con.execute(
        f"SELECT dst_id, COUNT(*) FROM edges "
        f"WHERE relation = 'tests_word' AND dst_id IN ({ph}) GROUP BY dst_id",
        keys,
    ).fetchall()
    freq = {r[0].split(":", 1)[1]: r[1] for r in rows}
    return {w: freq.get(w, 0) for w in uniq}


def word_exam_trace(con: duckdb.DuckDBPyConnection, word: str,
                    recent_n: int = 5) -> list[dict]:
    """近 N 次真题中考查该词的 question 溯源 (year DESC)."""
    rows = con.execute(
        "SELECT q.question_id, q.year, q.question_type "
        "FROM edges e INNER JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10) "
        "WHERE e.relation = 'tests_word' AND e.dst_id = ? "
        "ORDER BY q.year DESC, q.question_id LIMIT ?",
        [f"word:{word}", recent_n],
    ).fetchall()
    return [{"question_id": r[0], "year": r[1], "question_type": r[2]} for r in rows]


def unit_word_exam_alignment(con: duckdb.DuckDBPyConnection, unit_id: str) -> dict:
    """该单元引入词 ∩ 历年真题考过的词 统计 (intro_total / exam_overlap / top examples)."""
    freqs = unit_word_frequencies(con, unit_id)
    if not freqs:
        return {"unit_id": unit_id, "intro_total": 0, "exam_overlap": 0, "examples": []}
    overlap = [(w, f) for w, f in freqs.items() if f > 0]
    overlap.sort(key=lambda x: (-x[1], x[0]))   # 同频按词字母序 — 确定性 (D0 100% 可复现)
    return {
        "unit_id": unit_id,
        "intro_total": len(freqs),
        "exam_overlap": len(overlap),
        "examples": [{"word": w, "exam_freq": c} for w, c in overlap[:20]],
    }
