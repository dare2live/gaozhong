"""趋势分析诚实护栏 (件1) — province 锚定 + PIT 卷制分段 + 样本量守门.

把 D0 从"数据诚实"扩展到"分析诚实": 任何命题趋势必须
  1. **province-scoped**: 只对辽宁卷算 (§7 锚定; 不混 284 道全国卷/未知);
  2. **PIT 卷制分段**: 2015-2020 旧课标全国 II 与 2021+ 新高考全国 II 不混做一条回归 (§3.1);
  3. **样本量守门**: 任一年真题 < MIN_YEAR_SAMPLE 不足以锚定该年趋势点;
     一段内达标年 < MIN_TREND_YEARS 时该段标 insufficient (reliable=False), 不冒充可信 slope。

reliable=False 不代表不输出数字, 而是明确"此 slope 是噪声, 不可下命题趋势结论"——
宁可说样本不足, 也不让薄样本伪装成趋势 (谄媚死防线)。
"""
from __future__ import annotations

from collections import defaultdict

import duckdb

LIAONING_PREDICATE = "province LIKE '辽宁%'"
MIN_YEAR_SAMPLE = 10   # 一年真题 < 10 题, 该年趋势点不可靠
MIN_TREND_YEARS = 5    # 一段内达标年 < 5, 不输出可信 slope


def liaoning_clause(province_scoped: bool = True) -> str:
    """SQL 谓词; province_scoped=False 仅供诊断对比, 默认必锚定辽宁."""
    return LIAONING_PREDICATE if province_scoped else "1=1"


def segment(year: int) -> str:
    """PIT 卷制分段: 2021 起辽宁用新高考全国 II 卷, 此前旧课标全国 II (§3.1 不可混算)."""
    return "2021+_新高考II" if year >= 2021 else "2015-2020_旧课标II"


def year_totals(con: duckdb.DuckDBPyConnection, province_scoped: bool = True) -> dict[int, int]:
    rows = con.execute(
        f"SELECT year, count(*) FROM exam_questions "
        f"WHERE {liaoning_clause(province_scoped)} AND year IS NOT NULL "
        f"GROUP BY year"
    ).fetchall()
    return {int(y): int(n) for y, n in rows}


def sample_diagnosis(totals: dict[int, int]) -> dict:
    """每段 → {各年样本量, 达标年, 是否够格出趋势}. 趋势消费方据此决定可信与否."""
    segs: dict[str, dict[int, int]] = defaultdict(dict)
    for year, n in totals.items():
        segs[segment(year)][year] = n
    diagnosis = {}
    for seg, ys in segs.items():
        adequate = sorted(y for y, n in ys.items() if n >= MIN_YEAR_SAMPLE)
        diagnosis[seg] = {
            "years": dict(sorted(ys.items())),
            "adequate_years": adequate,
            "trend_eligible": len(adequate) >= MIN_TREND_YEARS,
        }
    return diagnosis


def is_reliable(diagnosis: dict) -> bool:
    """只要有一段达标即可输出可信趋势; 全段不达标 → 整体不可信."""
    return any(seg["trend_eligible"] for seg in diagnosis.values())


def diagnose(con: duckdb.DuckDBPyConnection, province_scoped: bool = True) -> dict:
    """一次性产出趋势可信度诊断 (供趋势函数 + CLI + API 复用, 单一计算点)."""
    totals = year_totals(con, province_scoped)
    diagnosis = sample_diagnosis(totals)
    return {
        "province_scope": "辽宁卷" if province_scoped else "全部(非锚定,仅诊断对比)",
        "min_year_sample": MIN_YEAR_SAMPLE,
        "min_trend_years": MIN_TREND_YEARS,
        "by_segment": diagnosis,
        "reliable": is_reliable(diagnosis),
    }
