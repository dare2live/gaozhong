"""趋势分析诚实护栏 (件1) — province 锚定 + PIT 卷制分段 + **区分"分布"与"趋势"两种样本量门槛**.

把 D0 从"数据诚实"扩展到"分析诚实": 任何命题分析必须
  1. **province-scoped**: 只对辽宁卷算 (§7 锚定; 不混 284 道全国卷/未知);
  2. **PIT 卷制分段**: 2015-2020 旧课标全国 II 与 2021+ 新高考全国 II 不混算 (§3.1);
  3. **两种门槛分开** (2026-06-15 用户纠偏: "辽宁项目怎么会样本不足" — 是我把分布与趋势混了):
     - **考点分布 (distribution / snapshot)**: "辽宁考什么的占比", 备课核心。只需同卷制 era 内
       总题数 ≥ MIN_DISTRIBUTION_SAMPLE。辽宁新高考II era 140 题/5套卷 → **充足**, 这是项目主用途。
     - **逐年趋势 (trend / slope over years)**: "逐年上升/下降"。需达标年 ≥ MIN_TREND_YEARS 且每年
       ≥ MIN_YEAR_SAMPLE。辽宁仅 5 年(其中 2023=6/2025=9) → **不足**, 不拟合可信斜率。

distribution_reliable=True 时放心报占比; trend_reliable=False 时只是不画逐年斜率线, 不是不能分析。
宁可说"趋势样本不足(分布可用)", 也不让薄样本伪装成 slope (谄媚死防线)。
"""
from __future__ import annotations

from collections import defaultdict

import duckdb

LIAONING_PREDICATE = "province LIKE '辽宁%'"
MIN_DISTRIBUTION_SAMPLE = 30  # 同卷制 era 总题数 ≥ 此 → 考点分布(占比)可报
MIN_YEAR_SAMPLE = 10          # 一年真题 < 此, 该年趋势点不可靠
MIN_TREND_YEARS = 5           # 一段内达标年 < 此, 不输出可信逐年 slope
# 词汇量年 slope 显著阈 (±词/年): |slope|>此 → 逐年上升/下降, 否则持平 (P2: model._slope_interp +
# predicted 难度判定共用此单点, 防两处 50 漂移; 与 MIN_* 同为 trend 判定阈值的模块单点)。
VOCAB_SLOPE_SIGNIFICANT = 50
# 卷制断点单点 (PIT §3.1): 2021 起辽宁用新高考全国 II 卷, 此前旧课标全国 II。
# segment()/era_sql() 都用这三个常量, 下游 (loader._ERA_SQL / cooccur / exam_paper / cognitive_skill) 复用,
# 不再各自硬编码 2021/2015 (G2 收口: 辽宁卷史边界全从这里取)。
ERA_BOUNDARY_YEAR = 2021
# 辽宁采用国家卷起始年 (2010-2014 自主命题无国家卷; 2015 起新课标全国 II = 辽宁卷判别的省份生效边界, CLAUDE §1.4)
LIAONING_NATIONAL_PAPER_SINCE = 2015
ERA_NEW = "2021+_新高考II"
ERA_OLD = "2015-2020_旧课标II"
# 辽宁卷 province 入库标签单点 (G3: 5处散落字面收口到此常量 hub; 坑3/坑7 province 一致性铁律 —
# 全项目用同一字符串, 防 "辽宁(新课标II卷)" vs "辽宁 (新课标 II 卷, 2021+)" 漂移导致精确匹配/统计错)。
# 与 ERA_NEW/OLD(segment 短键) 不同: 这是 exam_questions.province 字段的**完整标签**(省份+卷型+era)。
# 选 scope 作 home 而非 exam_paper: exam_paper fan-in=2 再+4=6 违铁律7; scope 本就是常量 leaf hub。
LIAONING_XGKII_2021 = "辽宁 (新课标 II 卷, 2021+)"          # 2021+ 新高考全国II
LIAONING_XGKII_2015_2020 = "辽宁 (新课标 II 卷, 2015-2020)"  # 2015-2020 旧课标全国II


def liaoning_clause(province_scoped: bool = True) -> str:
    """SQL 谓词; province_scoped=False 仅供诊断对比, 默认必锚定辽宁."""
    return LIAONING_PREDICATE if province_scoped else "1=1"


def segment(year: int) -> str:
    """PIT 卷制分段: 2021 起辽宁用新高考全国 II 卷, 此前旧课标全国 II (§3.1 不可混算)."""
    return ERA_NEW if year >= ERA_BOUNDARY_YEAR else ERA_OLD


def era_sql(year_col: str = "q.year") -> str:
    """SQL era CASE 片段 (与 segment() 同口径单点); 供 loader/cooccur 复用, 不各自硬编码 2021。"""
    return f"CASE WHEN {year_col} >= {ERA_BOUNDARY_YEAR} THEN '{ERA_NEW}' ELSE '{ERA_OLD}' END"


def year_totals(con: duckdb.DuckDBPyConnection, province_scoped: bool = True) -> dict[int, int]:
    rows = con.execute(
        f"SELECT year, count(*) FROM exam_questions "
        f"WHERE {liaoning_clause(province_scoped)} AND year IS NOT NULL "
        f"GROUP BY year"
    ).fetchall()
    return {int(y): int(n) for y, n in rows}


def sample_diagnosis(totals: dict[int, int]) -> dict:
    """每段 → {各年样本量, 达标年, 总题数, 趋势是否够格, 分布是否够格}."""
    segs: dict[str, dict[int, int]] = defaultdict(dict)
    for year, n in totals.items():
        segs[segment(year)][year] = n
    diagnosis = {}
    for seg, ys in segs.items():
        adequate = sorted(y for y, n in ys.items() if n >= MIN_YEAR_SAMPLE)
        seg_total = sum(ys.values())
        diagnosis[seg] = {
            "years": dict(sorted(ys.items())),
            "total": seg_total,
            "adequate_years": adequate,
            "trend_eligible": len(adequate) >= MIN_TREND_YEARS,
            "distribution_eligible": seg_total >= MIN_DISTRIBUTION_SAMPLE,
        }
    return diagnosis


def is_reliable(diagnosis: dict) -> bool:
    """趋势(逐年slope)可信: 任一段达标年够. 注意这只管趋势, 分布另见 distribution_reliable."""
    return any(seg["trend_eligible"] for seg in diagnosis.values())


def distribution_reliable(diagnosis: dict) -> bool:
    """考点分布(占比)可信: 任一卷制 era 总题数够 (辽宁新高考II 140题 → True)."""
    return any(seg["distribution_eligible"] for seg in diagnosis.values())


def diagnose(con: duckdb.DuckDBPyConnection, province_scoped: bool = True) -> dict:
    """一次性产出可信度诊断 (区分分布/趋势; 供趋势函数 + CLI + API 复用, 单一计算点)."""
    totals = year_totals(con, province_scoped)
    diagnosis = sample_diagnosis(totals)
    return {
        "province_scope": "辽宁卷" if province_scoped else "全部(非锚定,仅诊断对比)",
        "min_distribution_sample": MIN_DISTRIBUTION_SAMPLE,
        "min_year_sample": MIN_YEAR_SAMPLE,
        "min_trend_years": MIN_TREND_YEARS,
        "by_segment": diagnosis,
        "distribution_reliable": distribution_reliable(diagnosis),
        "trend_reliable": is_reliable(diagnosis),
        "reliable": is_reliable(diagnosis),  # 向后兼容 (= trend_reliable)
    }
