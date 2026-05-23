"""历年高考趋势统计 (用户 2026-05-23: 全局综合关联, 非押题).

不做"押题预测", 做**频次统计 + 趋势**:
  - 词: 历年真题题面词频 (按年聚合), 标"高频/中频/低频"
  - 题型: 历年题型占比 (按 year × question_type)
  - 主题: 真题题面与 theme 关键词关联 (简单 substring, MVP)

输出给前端展示 (热力图扩展) + L4 模拟卷题型分布参考.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import duckdb

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")

# English stopwords + 高考阅读高频但分析价值低的功能词
STOPWORDS = {
    "the","a","an","and","or","but","of","to","in","on","at","for","with","by",
    "is","are","was","were","be","been","being","am","do","does","did","done",
    "have","has","had","having","will","would","shall","should","can","could",
    "may","might","must","not","no","nor","yes","so","as","if","then","than",
    "this","that","these","those","it","its","he","she","they","them","his",
    "her","their","we","you","i","me","my","your","our","us","him",
    "what","when","where","why","how","which","who","whom","whose",
    "from","into","onto","upon","over","under","about","above","below","between",
    "out","up","down","off","through","during","before","after","since","until",
    "while","because","although","though","unless","also","just","only","more",
    "most","some","any","all","each","every","other","another","such","same",
    "very","too","much","many","few","little","own","other",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "first","second","third",
    # 题面常用功能词
    "passage","question","answer","choose","read","write","following","below",
    "correct","best","blank","blanks","example","examples","section",
    "according","please","note","instructions",
}


def word_freq_by_year(con: duckdb.DuckDBPyConnection,
                       restrict_to_cefr: bool = True,
                       exclude_stopwords: bool = True) -> dict[str, dict[int, int]]:
    """Return {word: {year: count}} — token-level on raw_question."""
    cefr = set()
    if restrict_to_cefr:
        cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    out: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for yr, qtext in con.execute(
        "SELECT year, raw_question FROM exam_questions WHERE year IS NOT NULL"
    ).fetchall():
        if not yr or not qtext:
            continue
        for tok in _WORD_RE.findall(qtext):
            w = tok.lower()
            if exclude_stopwords and w in STOPWORDS:
                continue
            if restrict_to_cefr and w not in cefr:
                continue
            out[w][yr] += 1
    return out


def top_high_freq_words(con: duckdb.DuckDBPyConnection, top_n: int = 50) -> list[dict]:
    freq = word_freq_by_year(con)
    totals = {w: sum(yrs.values()) for w, yrs in freq.items()}
    rank = sorted(totals.items(), key=lambda kv: -kv[1])[:top_n]
    return [{"word": w, "total": n,
              "years": dict(sorted(freq[w].items())),
              "year_span": len(freq[w])} for w, n in rank]


def type_freq_by_year(con: duckdb.DuckDBPyConnection) -> dict[int, Counter]:
    out: dict[int, Counter] = defaultdict(Counter)
    for yr, qt in con.execute(
        "SELECT year, question_type FROM exam_questions WHERE year IS NOT NULL"
    ).fetchall():
        if yr and qt:
            out[yr][qt] += 1
    return out


def trend_summary(con: duckdb.DuckDBPyConnection) -> dict:
    top = top_high_freq_words(con, top_n=30)
    type_by_year = type_freq_by_year(con)
    type_by_year_serialized = {y: dict(c) for y, c in sorted(type_by_year.items())}
    return {
        "top_words": top,
        "type_distribution_by_year": type_by_year_serialized,
        "years_covered": sorted(type_by_year),
    }
