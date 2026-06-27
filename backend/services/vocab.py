"""词汇 ↔ 真题 单一计算点 (架构 §0 Rule 1).

"单元引入词" 与 "某词的真题考查频次 / 题目溯源" 是派生事实, 只在这里算一次。
原先散在 recommend.unit_exam_alignment + lesson_plan._word_exam_trace 各算一遍 (双算债),
备课整合若再写一遍 = 第三套。收口到此, 三方 (recommend / lesson_plan / 备课整合) 同调。

真相源 = edges (introduces_word / tests_word) + exam_questions, 不读中间派生表。
"""
from __future__ import annotations

import duckdb

# 后端审计 根因A+#3 (2026-06-27): "该词被真题**考查**" ≠ "词出现在阅读篇章"。tests_word 边对整篇 raw_question
# 建边(含95词阅读篇章), 直接当"考查/必教"会把 make/time/go 等篇章功能词刷成高频考词(实测辽宁74%边来自
# 阅读/听力/续写等语篇题型)。且原函数**无 province 过滤**(make 66%边非辽宁), 违 §7 辽宁锚定 +
# lesson_plan.py docstring 谎称"word 同省"。故"考查频次/对齐"收口到: **辽宁卷 离散vocab/grammar题型**
# (TESTED_QTYPES, 与 exam_vocab/exam_status 同源同口径), 排除阅读/听力/续写/七选五/应用文篇章。
# (注: 完形/语法填空 raw_question 仍含空格上下文, 非完美"被考词"; 但已剔除最严重的阅读篇章污染, 见 task 根因A 深修。)
from backend.services.exam_vocab import TESTED_QTYPES   # 单一真相源: 离散考点题型口径
_TESTED_IN = ",".join("'" + t.replace("'", "''") + "'" for t in TESTED_QTYPES)
_TESTED_JOIN = (
    "JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10) "
    "WHERE e.relation = 'tests_word' AND q.province LIKE '辽宁%' "
    f"AND q.question_type IN ({_TESTED_IN})")


def unit_introduced_words(con: duckdb.DuckDBPyConnection, unit_id: str) -> list[str]:
    """该单元 introduces_word 边引入的词 (去 'word:' 前缀, 不去重 — 调用方按需 set)."""
    rows = con.execute(
        "SELECT dst_id FROM edges WHERE src_id = ? AND relation = 'introduces_word'",
        [unit_id],
    ).fetchall()
    return [r[0].split(":", 1)[1] for r in rows]


def word_exam_frequency(con: duckdb.DuckDBPyConnection, word: str) -> int:
    """该词在辽宁卷**离散考点题型**(完形/语法填空/短改/单选)被考查的频次 (非阅读篇章出现; §7+根因A)."""
    return con.execute(
        f"SELECT COUNT(*) FROM edges e {_TESTED_JOIN} AND e.dst_id = ?",
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
        f"SELECT e.dst_id, COUNT(*) FROM edges e {_TESTED_JOIN} "
        f"AND e.dst_id IN ({ph}) GROUP BY e.dst_id",
        keys,
    ).fetchall()
    freq = {r[0].split(":", 1)[1]: r[1] for r in rows}
    return {w: freq.get(w, 0) for w in uniq}


def word_exam_trace(con: duckdb.DuckDBPyConnection, word: str,
                    recent_n: int = 5) -> list[dict]:
    """近 N 次辽宁卷**离散考点题型**考查该词的 question 溯源 (year DESC; §7+根因A, 非阅读篇章出现)."""
    rows = con.execute(
        f"SELECT q.question_id, q.year, q.question_type "
        f"FROM edges e {_TESTED_JOIN} AND e.dst_id = ? "
        f"ORDER BY q.year DESC, q.question_id LIMIT ?",
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
