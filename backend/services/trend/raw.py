"""raw 词频/题型 count 统计 (从原 trend.py 抽)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import duckdb

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")

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
    "very","too","much","many","few","little","own",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "first","second","third",
    "passage","question","answer","choose","read","write","following","below",
    "correct","best","blank","blanks","example","examples","section",
    "according","please","note","instructions",
}


def word_freq_by_year(con: duckdb.DuckDBPyConnection,
                       restrict_to_cefr: bool = True,
                       exclude_stopwords: bool = True) -> dict[str, dict[int, int]]:
    cefr = _load_cefr_set(con) if restrict_to_cefr else set()
    out: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    rows = con.execute(
        "SELECT year, raw_question FROM exam_questions WHERE year IS NOT NULL"
    ).fetchall()
    for yr, qtext in rows:
        _tally_year(out, yr, qtext, cefr, exclude_stopwords, restrict_to_cefr)
    return out


def _load_cefr_set(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}


def _tally_year(out: dict, yr, qtext, cefr: set, exclude_stop: bool, restrict: bool) -> None:
    if not yr or not qtext:
        return
    for tok in _WORD_RE.findall(qtext):
        w = tok.lower()
        if exclude_stop and w in STOPWORDS:
            continue
        if restrict and w not in cefr:
            continue
        out[w][yr] += 1


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
