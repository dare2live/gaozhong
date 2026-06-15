"""蓝图结构练习卷 — 从 question_bank(历年真题) 按**考纲蓝图结构**组卷, 非预测非押题.

2026-06-15 REVISE (件1 分析诚实): 原名"趋势驱动预测试卷"是营销话术 (§3.2 Banned 押题;
exam_scenario_patterns §8: "AI 押中高考"违反 D0)。已重定位:
  - 题面均来自 question_bank(全 origin=real 历年真题), **不合成、不预测具体题面**;
  - 题型占比按**考纲蓝图固定结构**(历史平均占比)组卷;
  - **仅当辽宁卷趋势可信(reliable=True)时**才用 slope 做轻微近年方向加权; 件1 判定辽宁样本
    不足(reliable=False)→ 退回蓝图固定结构, 绝不按不可信 slope 加权 (不让噪声伪装成"预测")。
  - 老师可手动调整 type_mix。

公开 API: generate_blueprint_practice_paper(con, total, seed)。
"""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from backend.services.question_bank import compose as cmp
from backend.services.trend import (question_type_year_trend, top_rising_words,
                                       vocab_year_growth)


def _spec_from_trends(con: duckdb.DuckDBPyConnection, total: int = 30,
                       seed: int | None = None) -> dict:
    """推 compose spec: 趋势可信→轻微 slope 加权; 不可信→蓝图固定占比 (件1 reliability 门控)."""
    trends = question_type_year_trend(con)
    reliable = bool(trends and trends[0].get("reliable"))
    if reliable:
        weights = {t["question_type"]: max(t["avg_share"] + 5 * t["slope_per_year"], 0.02)
                   for t in trends}
        prefs = [f"word:{w['word']}" for w in top_rising_words(con, top_n=10)[:6]]
        basis = "trend_weighted (辽宁卷趋势可信, slope 轻微加权近年方向)"
    else:
        # 样本不足: 退回考纲蓝图固定结构 (历史平均占比), 不按 slope 加权, 不注入"上升词"
        weights = {t["question_type"]: max(t["avg_share"], 0.02) for t in trends}
        prefs = []
        basis = "blueprint_fixed (辽宁卷样本不足 reliable=False → 退回蓝图固定占比, 不按不可信 slope 加权)"
    total_w = sum(weights.values()) or 1.0
    type_mix = {qt: max(1, round(total * w / total_w)) for qt, w in weights.items()}
    growth = vocab_year_growth(con)
    difficulty = "hard" if (growth.get("reliable") and growth.get("slope_per_year", 0) > 50) else "mixed"
    return {
        "type_mix": type_mix,
        "require_tags": None,
        "preference_tags": prefs,
        "difficulty": difficulty,
        "seed": seed,
        "selection_basis": basis,
    }


def generate_blueprint_practice_paper(con: duckdb.DuckDBPyConnection,
                                      total: int = 30, seed: int | None = None) -> dict:
    """按考纲蓝图结构从历年真题组练习卷 (非预测/非押题)."""
    spec = _spec_from_trends(con, total=total, seed=seed)
    paper = cmp.compose(con, spec)
    paper["paper_type"] = "blueprint_structured_practice"
    paper["composition_basis"] = {
        "selection_basis": spec["selection_basis"],
        "type_mix": spec["type_mix"],
        "positioning": (
            "按考纲蓝图结构从 question_bank(历年真题) 加权抽样组卷; "
            "非预测/非押题——不预测具体题面, 题面均为历年真题; "
            "辽宁卷趋势样本不足时退回蓝图固定占比, 不按不可信 slope 加权. 老师可手动调整."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return paper


# 向后兼容别名 (历史调用方); 指向重定位后的诚实实现, 不再是"预测"语义。
generate_predicted_paper = generate_blueprint_practice_paper
