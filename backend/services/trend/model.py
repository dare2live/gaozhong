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

from . import scope
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


def question_type_year_trend(con: duckdb.DuckDBPyConnection,
                             province_scoped: bool = True) -> list[dict]:
    """每年每题型占比线性回归 slope. 件1 护栏: 默认只对**辽宁卷**算 (§7);
    样本不达标时 reliable=False + trend='样本不足', 不冒充可信趋势 (分析诚实)."""
    rows = con.execute(f"""
        SELECT year, question_type, COUNT(*) AS n
        FROM exam_questions
        WHERE {scope.liaoning_clause(province_scoped)}
          AND year IS NOT NULL AND question_type IS NOT NULL
        GROUP BY year, question_type
        ORDER BY year
    """).fetchall()
    by_year_type: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    year_totals: dict[int, int] = defaultdict(int)
    for y, t, n in rows:
        by_year_type[y][t] = n
        year_totals[y] += n
    reliable = scope.is_reliable(scope.sample_diagnosis(dict(year_totals)))
    scope_label = "辽宁卷" if province_scoped else "全部(非锚定)"
    all_types = sorted({t for ys in by_year_type.values() for t in ys})
    years = sorted(year_totals)
    out = []
    for qt in all_types:
        ys = [by_year_type[y].get(qt, 0) / max(1, year_totals[y]) for y in years]
        slope, _intercept = _linreg([float(y) for y in years], ys)
        out.append({
            "question_type": qt,
            "slope_per_year": round(slope, 5),
            "avg_share": round(sum(ys) / len(ys), 4) if ys else 0,
            "trend": _trend_label(slope, reliable),
            "n_years": len(years),
            "province_scope": scope_label,
            "reliable": reliable,
        })
    return sorted(out, key=lambda r: -r["slope_per_year"])


def _trend_label(slope: float, reliable: bool) -> str:
    """样本不达标 → '样本不足'(不冒充趋势); 达标才给上升/下降/持平."""
    if not reliable:
        return "样本不足"
    return "上升" if slope > 0.001 else "下降" if slope < -0.001 else "持平"


def vocab_year_growth(con: duckdb.DuckDBPyConnection,
                      province_scoped: bool = True) -> dict:
    """辽宁卷年总实义词 token 数 → 线性回归 (件1: province 锚定 + 样本量护栏)."""
    by_year = _tokens_per_year(con, province_scoped)
    years = sorted(by_year)
    xs = [float(y) for y in years]
    ys = [float(by_year[y]) for y in years]
    slope, _intercept = _linreg(xs, ys)
    reliable = scope.is_reliable(scope.diagnose(con, province_scoped)["by_segment"])
    return {
        "years": years,
        "tokens_per_year": [by_year[y] for y in years],
        "slope_per_year": round(slope, 2),
        "interpretation": _slope_interp(slope) if reliable else "样本不足, 不下趋势结论",
        "province_scope": "辽宁卷" if province_scoped else "全部(非锚定)",
        "reliable": reliable,
    }


def _tokens_per_year(con: duckdb.DuckDBPyConnection,
                     province_scoped: bool = True) -> dict[int, int]:
    rows = con.execute(
        f"SELECT year, raw_question FROM exam_questions "
        f"WHERE {scope.liaoning_clause(province_scoped)} AND year IS NOT NULL"
    ).fetchall()
    by_year: dict[int, int] = defaultdict(int)
    for y, q in rows:
        for t in _WORD_RE.findall(q or ""):
            tl = t.lower()
            if tl not in STOPWORDS and len(tl) >= 3:
                by_year[y] += 1
    return by_year


def _slope_interp(slope: float) -> str:
    if slope > 50:
        return "词汇量逐年上升"
    if slope < -50:
        return "词汇量逐年下降"
    return "词汇量持平"


def top_rising_words(con: duckdb.DuckDBPyConnection,
                       recent_years: int = 3, top_n: int = 20,
                       province_scoped: bool = True) -> list[dict]:
    """近 N 年新出现 / 频次上升的词 (件1: province 锚定; 跨卷制断点的'新词'不可信故附 reliable)."""
    by_word_year = _word_year_counts(con, province_scoped)
    all_years = sorted({y for d in by_word_year.values() for y in d})
    if len(all_years) < recent_years * 2:
        return []
    recent = set(all_years[-recent_years:])
    older = set(all_years[:-recent_years])
    reliable = scope.is_reliable(scope.diagnose(con, province_scoped)["by_segment"])
    rising = _filter_rising(by_word_year, recent, older)
    rising.sort(key=lambda x: -x[1])
    return [{"word": w, "recent_freq": r, "older_freq": o,
              "rise_ratio": (r + 1) / (o + 1), "reliable": reliable}
            for w, r, o in rising[:top_n]]


def _word_year_counts(con: duckdb.DuckDBPyConnection,
                      province_scoped: bool = True) -> dict[str, dict[int, int]]:
    rows = con.execute(
        f"SELECT year, raw_question FROM exam_questions "
        f"WHERE {scope.liaoning_clause(province_scoped)} AND year IS NOT NULL"
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
