"""4.3 命题趋势真模型 (stdlib statistics + numpy-free 线性回归).

不引 numpy/sklearn, 用 Python stdlib.
模型:
  1. question_type_year_trend  — 各题型年占比线性回归 (slope > 0 = 上升趋势)
  2. vocab_year_growth         — 高频词年总词频回归 (词汇难度膨胀指数)
  3. top_rising_words          — 找近 3 年新出现 / 高速增长的词

不预测下次考什么 (gaokao 项目宪法 banned 押题); 只做趋势识别.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

import duckdb

from .raw import _WORD_RE, STOPWORDS


def _linreg(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """简单线性回归 y = slope*x + intercept (stdlib only)."""
    n = len(xs)
    if n < 2:
        return (0.0, 0.0)
    mx = statistics.mean(xs); my = statistics.mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    if den == 0: return (0.0, my)
    slope = num / den
    intercept = my - slope * mx
    return slope, intercept


def question_type_year_trend(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """每年每题型占比, 用线性回归算 slope. slope 高 = 该题型占比逐年上升."""
    rows = con.execute("""
        SELECT year, question_type, COUNT(*) AS n
        FROM exam_questions WHERE year IS NOT NULL AND question_type IS NOT NULL
        GROUP BY year, question_type
        ORDER BY year
    """).fetchall()
    by_year_type: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    year_totals: dict[int, int] = defaultdict(int)
    for y, t, n in rows:
        by_year_type[y][t] = n
        year_totals[y] += n
    all_types = sorted({t for ys in by_year_type.values() for t in ys})
    years = sorted(year_totals)
    out = []
    for qt in all_types:
        xs: list[float] = []
        ys: list[float] = []
        for y in years:
            xs.append(float(y))
            ys.append(by_year_type[y].get(qt, 0) / max(1, year_totals[y]))
        slope, intercept = _linreg(xs, ys)
        out.append({
            "question_type": qt,
            "slope_per_year": round(slope, 5),
            "avg_share": round(sum(ys) / len(ys), 4) if ys else 0,
            "trend": "上升" if slope > 0.001 else "下降" if slope < -0.001 else "持平",
            "n_years": len(years),
        })
    return sorted(out, key=lambda r: -r["slope_per_year"])


def vocab_year_growth(con: duckdb.DuckDBPyConnection) -> dict:
    """所有真题年总实义词 token 数 → 线性回归."""
    rows = con.execute(
        "SELECT year, raw_question FROM exam_questions WHERE year IS NOT NULL"
    ).fetchall()
    by_year: dict[int, int] = defaultdict(int)
    for y, q in rows:
        for t in _WORD_RE.findall(q or ""):
            tl = t.lower()
            if tl not in STOPWORDS and len(tl) >= 3:
                by_year[y] += 1
    years = sorted(by_year)
    xs = [float(y) for y in years]
    ys = [float(by_year[y]) for y in years]
    slope, intercept = _linreg(xs, ys)
    return {
        "years": years,
        "tokens_per_year": [by_year[y] for y in years],
        "slope_per_year": round(slope, 2),
        "interpretation": (
            "词汇量逐年上升" if slope > 50
            else "词汇量逐年下降" if slope < -50
            else "词汇量持平"
        ),
    }


def top_rising_words(con: duckdb.DuckDBPyConnection,
                       recent_years: int = 3, top_n: int = 20) -> list[dict]:
    """近 N 年新出现 / 频次上升的词. (M6 拆: 主函数 ≤10)"""
    by_word_year = _word_year_counts(con)
    all_years = sorted({y for d in by_word_year.values() for y in d})
    if len(all_years) < recent_years * 2:
        return []
    recent = set(all_years[-recent_years:])
    older = set(all_years[:-recent_years])
    rising = _filter_rising(by_word_year, recent, older)
    rising.sort(key=lambda x: -x[1])
    return [{"word": w, "recent_freq": r, "older_freq": o,
              "rise_ratio": (r + 1) / (o + 1)} for w, r, o in rising[:top_n]]


def _word_year_counts(con: duckdb.DuckDBPyConnection) -> dict[str, dict[int, int]]:
    rows = con.execute(
        "SELECT year, raw_question FROM exam_questions WHERE year IS NOT NULL"
    ).fetchall()
    by_wy: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for y, q in rows:
        for t in _WORD_RE.findall(q or ""):
            tl = t.lower()
            if tl not in STOPWORDS and len(tl) >= 4:
                by_wy[tl][y] += 1
    return by_wy


def _filter_rising(by_wy: dict, recent: set, older: set) -> list[tuple]:
    rising: list[tuple] = []
    for w, yd in by_wy.items():
        rt = sum(yd.get(y, 0) for y in recent)
        ot = sum(yd.get(y, 0) for y in older)
        if rt >= 3 and ot <= 1:
            rising.append((w, rt, ot))
    return rising
