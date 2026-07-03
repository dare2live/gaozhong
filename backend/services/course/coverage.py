"""L3 覆盖模型 — "用最少课程覆盖最大考点" 的可证量化 (北极星 Phase C, 决策C 框架不生成内容).

考点全集 (辽宁卷, 可教多轴): 题材 genre / 主题群 theme_l2 (tests_exam_point 边) +
高频考词 word (tests_word ∧ 离散) + 语法点 grammar (tests_grammar)。每考点权重 = 辽宁命题频次。
(设问思维 cognitive_skill = "怎么考"套路, 非可逐项覆盖的可教考点, 归真题特点套路分析, 不入覆盖全集。)
覆盖模型: 各轴按频次降序累计覆盖% → 达 target% 所需最少考点数 (高产出集) + 长尾缺口。回答"覆盖最大考查权重需教多少考点"。

全读已落库边 (前端/脚本禁重算, 铁律1)。单一计算点。数据真值, 算不出空轴不假填。
"""
from __future__ import annotations

import duckdb

# 覆盖考点轴 = **可教/可覆盖**项 (题材/主题群/词/语法); tests_exam_point 边覆盖 genre+theme_l2。
# 设问思维(cognitive_skill)不入此 — 它是"怎么考"套路(子题级独立边, 非 tests_exam_point), 是训练性技能非可逐项覆盖的考点, 归真题特点套路分析。
_PT_AXES = (
    ("genre", "题材 · 体裁"),
    ("theme_l2", "主题群 (课标)"),
)


def _ln_freq_by_point(con: duckdb.DuckDBPyConnection, dim: str) -> list[tuple[str, int]]:
    """某 exam_point 维度的辽宁命题频次 (tests_exam_point ∧ 辽宁前缀, 坑7-safe), 降序."""
    return con.execute(
        "SELECT SUBSTR(e.dst_id, LENGTH('exam_point:' || ? || ':') + 1) AS label, COUNT(*) AS n "
        "FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10) "
        "WHERE e.relation='tests_exam_point' AND e.dst_id LIKE 'exam_point:' || ? || ':%' "
        "AND q.province LIKE '辽宁%' GROUP BY 1 ORDER BY 2 DESC",
        [dim, dim],
    ).fetchall()


def _ln_word_freq(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int]]:
    """高频考词轴: tests_word ∧ 辽宁 ∧ 离散考点题型 (出现≠考查 根因A) 每词考查频次, 降序."""
    from backend.services.exam_vocab import TESTED_QTYPES
    qm = ",".join("?" * len(TESTED_QTYPES))
    return con.execute(
        "SELECT SUBSTR(e.dst_id, 6) AS w, COUNT(*) AS n "
        "FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10) "
        f"WHERE e.relation='tests_word' AND q.province LIKE '辽宁%' AND q.question_type IN ({qm}) "
        "GROUP BY 1 ORDER BY 2 DESC",
        list(TESTED_QTYPES),
    ).fetchall()


def _ln_grammar_freq(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int]]:
    """语法点轴: tests_grammar ∧ 辽宁 每语法点频次, 降序."""
    return con.execute(
        "SELECT SUBSTR(e.dst_id, LENGTH('grammar:') + 1) AS g, COUNT(*) AS n "
        "FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10) "
        "WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%' GROUP BY 1 ORDER BY 2 DESC",
        [],
    ).fetchall()


def _grammar_top_labels(con: duckdb.DuckDBPyConnection, top: list[dict]) -> None:
    """语法轴 top: 课标编码 → 人话标签 (P2-4). 纯查 grammar_items 单表 (真相源=课标 PDF 提取的官方层级),
    不建映射 YAML (第一性原理: 能查表不建映射文件)。每项补 id=课标编码, label=官方人话;
    查不到不杜撰 — label 保留编码 (D0 断言会抓悬挂)。"""
    gids = [t["label"] for t in top]
    if not gids:
        return
    qm = ",".join("?" * len(gids))
    labels = dict(con.execute(
        f"SELECT grammar_item_id, label FROM grammar_items WHERE grammar_item_id IN ({qm})",
        gids).fetchall())
    for t in top:
        t["id"] = t["label"]
        t["label"] = labels.get(t["id"], t["id"])


def _axis_curve(rows: list[tuple[str, int]], target_pct: float) -> dict:
    """从 (label,freq) 降序列表算覆盖曲线: 累计覆盖% + 达 target 所需最少考点数 + 长尾."""
    total = sum(n for _, n in rows)
    if total == 0:
        return {"n_total": 0, "weight_total": 0, "high_yield_n": 0, "tail_n": 0, "top": []}
    cum = 0
    high_yield_n = 0
    top = []
    for i, (label, n) in enumerate(rows):
        cum += n
        cum_pct = round(100.0 * cum / total, 1)
        if high_yield_n == 0 and cum_pct >= target_pct:
            high_yield_n = i + 1
        if i < 8:
            top.append({"label": label, "freq": n, "cum_pct": cum_pct})
    if high_yield_n == 0:
        high_yield_n = len(rows)
    return {
        "n_total": len(rows), "weight_total": total,
        "high_yield_n": high_yield_n, "high_yield_pct": target_pct,
        "tail_n": len(rows) - high_yield_n, "top": top,
    }


def coverage_model(con: duckdb.DuckDBPyConnection, target_pct: float = 90.0) -> dict:
    """各考点轴的覆盖模型 — "覆盖 target% 考查权重需多少考点" + 长尾缺口. 北极星 Phase C 核心证明."""
    axes = {}
    for key, label in _PT_AXES:
        axes[key] = {"label": label, **_axis_curve(_ln_freq_by_point(con, key), target_pct)}
    axes["word"] = {"label": "高频考词 (离散考查)", **_axis_curve(_ln_word_freq(con), target_pct)}
    axes["grammar"] = {"label": "语法点", **_axis_curve(_ln_grammar_freq(con), target_pct)}
    _grammar_top_labels(con, axes["grammar"]["top"])  # P2-4: 编码→课标人话标签 (单一计算点, 前端禁重查)
    return {
        "scope": "辽宁卷考点全集 (题材/主题群/高频考词/语法 可教轴); 权重=命题频次",
        "target_pct": target_pct,
        "axes": axes,
        "note": "高产出集=覆盖该轴 ≥target% 考查权重的最少考点数; 长尾=低频考点 (性价比低, 诚实非全覆盖)。词轴'出现≠考查'(根因A)。",
    }
