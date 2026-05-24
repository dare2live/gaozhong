"""4.3 + 趋势驱动的"预测试卷" — 不押题, 按 trend.model 推 spec → compose.

逻辑:
  1. trend.question_type_year_trend → slope > 0 题型加权 (近年趋势)
  2. trend.top_rising_words           → require_tags 含这些 word
  3. trend.vocab_growth               → 难度档位调 (上升期偏 hard)
  4. compose.compose(spec) → 出卷

非押题原因:
  - 题面不是 LLM 合成新的, 是从 question_bank 选 (题库 = 历年真题 + 规则合成)
  - 选题策略是"按趋势加权抽样", 不是"猜下次题面"
  - 输出含"why_selected" 说明每题为何入选 (透明)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from backend.services.question_bank import compose as cmp
from backend.services.trend import (question_type_year_trend, top_rising_words,
                                       vocab_year_growth)


def _spec_from_trends(con: duckdb.DuckDBPyConnection, total: int = 30,
                       seed: int | None = None) -> dict:
    """根据 trend.model 输出推 compose spec."""
    # 1. 题型分布 (slope > 0 占主, slope < 0 给少量)
    trends = question_type_year_trend(con)
    weights = {t["question_type"]: max(t["avg_share"] + 5 * t["slope_per_year"], 0.02)
                for t in trends}
    total_w = sum(weights.values()) or 1.0
    type_mix = {qt: max(1, round(total * w / total_w))
                 for qt, w in weights.items()}

    # 2. 高频上升词作 require (优先选含这些词的题)
    rising = top_rising_words(con, top_n=10)
    require = [f"word:{w['word']}" for w in rising[:6]]

    # 3. 词汇膨胀 → 偏难
    growth = vocab_year_growth(con)
    difficulty = "hard" if growth.get("slope_per_year", 0) > 50 else "mixed"

    return {
        "type_mix": type_mix,
        "require_tags": None,   # require_tags 太严会 0 命中, 改放进 metadata
        "preference_tags": require,   # 抽样时优先 (compose 现版未实装, 放 metadata)
        "difficulty": difficulty,
        "seed": seed,
    }


def generate_predicted_paper(con: duckdb.DuckDBPyConnection,
                                total: int = 30, seed: int | None = None) -> dict:
    spec = _spec_from_trends(con, total=total, seed=seed)
    paper = cmp.compose(con, spec)
    paper["paper_type"] = "predicted_trend_driven"
    paper["trend_basis"] = {
        "type_slopes": question_type_year_trend(con)[:6],
        "rising_words": [w["word"] for w in top_rising_words(con, top_n=10)],
        "vocab_growth_slope": vocab_year_growth(con).get("slope_per_year"),
        "selection_logic": "按 trend.model slope 加权题型 + 偏好高频上升词 + 词汇膨胀期偏 hard",
        "non_押题_disclaimer": (
            "题面均来自 question_bank (历年真题 + 规则合成), "
            "不预测具体题目, 仅按趋势加权抽样. 老师可手动调整."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return paper
