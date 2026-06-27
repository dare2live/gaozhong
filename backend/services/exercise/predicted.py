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
from backend.services.trend import scope   # P2: 词汇slope显著阈单点 (与 model 共用)


def _canonical_type_weights() -> dict:
    """新高考II 笔试 canonical 题数 → 真考纲蓝图结构占比 (exam_structure_eras.yaml item_counts, 数据化单点).

    后端审计 根因B: 原 type_mix 用 question_type_year_trend.avg_share, 但该 share 跨卷制混算 2021/22 子题级
    与 2023-26 篇章级(阅读占比虚高); docstring 一直承诺"退回考纲蓝图固定结构" 实际却用 grain混合历史均值。
    此处兑现: 用真考纲题数(听力外笔试 47 题)做固定结构占比。
    """
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "backend" / "config" / "exam_structure_eras.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    ic = ((data.get("eras") or {}).get("2021+_新高考II") or {}).get("item_counts") or {}
    return {str(k): float(v) for k, v in ic.items() if float(v) > 0}


def _type_weights(con: duckdb.DuckDBPyConnection, trends: list, reliable: bool, canonical: dict) -> tuple:
    """type_mix 权重 + preference_tags + basis (根因B: canonical 考纲结构优先, 仅可信才叠 slope)。
    返回 (weights, prefs, basis)。抽出以降 _spec_from_trends 复杂度 (Rule8 CC≤10)."""
    if canonical and reliable:
        slope = {t["question_type"]: t.get("slope_per_year", 0) for t in trends}
        w = {qt: max(v + 5 * slope.get(qt, 0), 0.02) for qt, v in canonical.items()}
        prefs = [f"word:{x['word']}" for x in top_rising_words(con, top_n=10)[:6]]
        return w, prefs, "trend_weighted (考纲 canonical 结构 + 辽宁卷可信 slope 轻微近年加权)"
    if canonical:
        # 样本不足: 退回**考纲蓝图固定结构**(item_counts 真值), 不按 slope 加权, 不注入上升词
        return dict(canonical), [], "blueprint_canonical (辽宁卷样本不足 → 退回考纲蓝图固定结构 item_counts; 非 grain混合历史均值)"
    # canonical 缺失兜底 (config 异常): 诚实降级历史均值并标明
    return ({t["question_type"]: max(t["avg_share"], 0.02) for t in trends}, [],
            "avg_share_fallback (canonical 结构缺失, 降级历史平均占比; 注: 跨卷制 grain 未归一)")


def _spec_from_trends(con: duckdb.DuckDBPyConnection, total: int = 30,
                       seed: int | None = None) -> dict:
    """推 compose spec: type_mix 用考纲 canonical 结构(根因B 修, 非 grain混合 avg_share);
    仅辽宁卷趋势可信(reliable=True)时叠加轻微 slope 近年方向加权 (件1 reliability 门控)."""
    trends = question_type_year_trend(con)
    reliable = bool(trends and trends[0].get("reliable"))
    weights, prefs, basis = _type_weights(con, trends, reliable, _canonical_type_weights())
    total_w = sum(weights.values()) or 1.0
    type_mix = {qt: max(1, round(total * w / total_w)) for qt, w in weights.items()}
    growth = vocab_year_growth(con)
    difficulty = "hard" if (growth.get("reliable") and growth.get("slope_per_year", 0) > scope.VOCAB_SLOPE_SIGNIFICANT) else "mixed"
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
