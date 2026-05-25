#!/usr/bin/env python3
"""考点趋势分析引擎 — 横向(年份趋势) + 纵向(考点关联) + 热力矩阵.

核心产出:
  1. 年份×考点 热力矩阵 (哪些考点在上升/下降)
  2. 考点关联图 (哪些考点经常同时出现)
  3. 趋势斜率排序 (上升最快的考点 = 明年最可能考的)
  4. 教学推荐 (基于趋势+关联, 推荐重点教学内容)

输出: data/reports/trend_analysis.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
OUTPUT_PATH = ROOT / "data" / "reports" / "trend_analysis.json"

EXAM_POINTS = [
    "细节理解", "推理判断", "主旨大意", "词义猜测", "标题选择", "目的意图",
    "定语从句", "名词性从句", "状语从句", "非谓语动词", "时态语态",
    "冠词", "介词搭配", "连词", "代词", "词性转换",
    "完形语境推断", "七选五衔接", "短文改错语法", "续写情节", "应用文格式",
]

POINT_KEYWORDS = {
    "细节理解": ["细节", "detail", "according to"],
    "推理判断": ["推断", "infer", "imply", "suggest"],
    "主旨大意": ["主旨", "main idea", "mainly about", "best title"],
    "词义猜测": ["词义", "meaning of", "closest in meaning", "underlined"],
    "标题选择": ["title", "标题", "heading"],
    "目的意图": ["目的", "purpose", "in order to", "意图"],
    "定语从句": ["定语从句", "which", "who", "whose", "关系代词", "关系副词"],
    "名词性从句": ["名词性从句", "主语从句", "宾语从句", "表语从句"],
    "状语从句": ["状语从句", "although", "if条件", "unless"],
    "非谓语动词": ["非谓语", "to do", "doing", "done", "不定式", "现在分词", "过去分词"],
    "时态语态": ["时态", "语态", "被动", "过去式", "现在完成", "will"],
    "冠词": ["冠词", "a/an", "the"],
    "介词搭配": ["介词", "搭配", "固定短语"],
    "连词": ["连词", "however", "therefore", "转折", "因果"],
    "代词": ["代词", "it", "them", "指代"],
    "词性转换": ["词性", "形容词", "副词", "名词", "动词", "转换"],
    "完形语境推断": ["完形", "语境", "上下文"],
    "七选五衔接": ["七选五", "衔接", "上文", "下文"],
    "短文改错语法": ["改错", "改正"],
    "续写情节": ["续写", "续", "情节"],
    "应用文格式": ["应用文", "书信", "格式", "Dear", "通知"],
}


YEAR_WEIGHTS = {2025: 5, 2024: 4, 2023: 3, 2022: 2, 2021: 1.5}
YEAR_WEIGHT_OLD = 0.5


def _yw(year: int) -> float:
    return YEAR_WEIGHTS.get(year, YEAR_WEIGHT_OLD)


def analyze(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT year, question_type, raw_question, answer, analysis "
        "FROM exam_questions WHERE year >= 2017 ORDER BY year"
    ).fetchall()
    years = sorted({r[0] for r in rows})
    heatmap, year_totals = _build_heatmap(rows, years)
    trends = _compute_trends(heatmap, years)
    cooccurrence = _compute_cooccurrence(rows)
    recommendations = _generate_recommendations(trends, cooccurrence)
    return {
        "years": years, "n_questions": len(rows),
        "year_weights": {y: _yw(y) for y in years},
        "heatmap": heatmap,
        "trends": trends,
        "cooccurrence": cooccurrence,
        "recommendations": recommendations,
    }


def _count_raw(rows, years) -> tuple[dict, dict]:
    """统计原始频次 + 年题量."""
    raw = {p: {y: 0 for y in years} for p in EXAM_POINTS}
    totals = {y: 0 for y in years}
    for year, _, rq, _, anal in rows:
        totals[year] = totals.get(year, 0) + 1
        detected = _detect_points((rq or "") + " " + (anal or ""))
        for point in detected:
            raw[point][year] += 1
    return raw, totals


def _build_heatmap(rows, years) -> tuple[dict, dict]:
    """年份×考点 比例矩阵 (归一化: count / year_total)."""
    raw, totals = _count_raw(rows, years)
    normed = {p: {y: raw[p][y] / max(totals.get(y, 1), 1) for y in years} for p in EXAM_POINTS}
    return normed, totals


def _wls_slope(x_vals: list, y_vals: list, weights: list) -> float:
    """Weighted Least Squares slope. 宪法 P1 合规."""
    w_sum = sum(weights)
    x_wm = sum(weights[i] * x_vals[i] for i in range(len(x_vals))) / w_sum
    y_wm = sum(weights[i] * y_vals[i] for i in range(len(y_vals))) / w_sum
    num = sum(weights[i] * (x_vals[i] - x_wm) * (y_vals[i] - y_wm) for i in range(len(x_vals)))
    den = sum(weights[i] * (x_vals[i] - x_wm) ** 2 for i in range(len(x_vals)))
    return num / den if den != 0 else 0


def _compute_trends(heatmap, years) -> list[dict]:
    """加权线性回归趋势排序."""
    if len(years) < 2:
        return []
    weights = [_yw(y) for y in years]
    results = []
    for point, year_counts in heatmap.items():
        vals = [year_counts[y] for y in years]
        slope = _wls_slope(list(years), vals, weights)
        w_total = sum(weights[i] * vals[i] for i in range(len(years)))
        w_recent = sum(weights[i] * vals[i] for i in range(len(years)) if years[i] >= years[-1] - 2)
        results.append({
            "point": point, "slope": round(slope, 3),
            "weighted_total": round(w_total, 1), "weighted_recent_3y": round(w_recent, 1),
            "raw_total": sum(vals),
            "direction": "rising" if slope > 0.005 else ("falling" if slope < -0.005 else "stable"),
        })
    results.sort(key=lambda x: x["slope"], reverse=True)
    return results


def _detect_points(text: str) -> set[str]:
    """检测文本中命中的考点."""
    found = set()
    for point, keywords in POINT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.add(point)
    return found


def _compute_cooccurrence(rows) -> list[dict]:
    """考点同现矩阵 — 哪些考点在同一年经常一起考."""
    year_points: dict[int, set] = defaultdict(set)
    for year, _, rq, _, anal in rows:
        year_points[year] |= _detect_points((rq or "") + " " + (anal or ""))
    pairs = Counter()
    for pts in year_points.values():
        pts_list = sorted(pts)
        for i, a in enumerate(pts_list):
            for b in pts_list[i + 1:]:
                pairs[(a, b)] += 1
    return [{"pair": list(p), "co_years": n} for p, n in pairs.most_common(15)]


def _generate_recommendations(trends, cooccurrence) -> list[dict]:
    """基于趋势+关联生成教学推荐."""
    recs = []
    rising = [t for t in trends if t["direction"] == "rising" and t["raw_total"] >= 3]
    for t in rising[:5]:
        related = [c["pair"][1] if c["pair"][0] == t["point"] else c["pair"][0]
                   for c in cooccurrence if t["point"] in c["pair"]][:3]
        recs.append({
            "point": t["point"],
            "reason": f"上升趋势 (WLS slope={t['slope']:+.3f}), 加权近3年={t['weighted_recent_3y']}",
            "related": related, "priority": "high",
        })
    falling = [t for t in trends if t["direction"] == "falling" and t["raw_total"] >= 3]
    for t in falling[:3]:
        recs.append({
            "point": t["point"],
            "reason": f"下降趋势 (WLS slope={t['slope']:+.3f}), 可适当减少",
            "priority": "low",
        })
    return recs


def save(result: dict) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return OUTPUT_PATH


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = analyze(con)
    finally:
        con.close()
    path = save(result)
    print(f"趋势分析已保存: {path}")
    print(f"数据范围: {result['years']}, {result['n_questions']} 题")

    print(f"年份权重: {result.get('year_weights', {})}")
    print(f"\n=== 考点趋势排序 (WLS slope, 加权) ===")
    for t in result["trends"][:10]:
        arrow = "↑" if t["direction"] == "rising" else ("↓" if t["direction"] == "falling" else "→")
        print(f"  {arrow} {t['point']:<12} slope={t['slope']:+.3f}  w_total={t['weighted_total']:>5.1f}  w_recent={t['weighted_recent_3y']:>5.1f}")

    print(f"\n=== 考点同现 TOP 10 ===")
    for c in result["cooccurrence"][:10]:
        print(f"  {c['pair'][0]} ↔ {c['pair'][1]}: {c['co_years']} 年同现")

    print(f"\n=== 教学推荐 ===")
    for r in result["recommendations"]:
        print(f"  [{r['priority'].upper()}] {r['point']}: {r['reason']}")
        if r.get("related"):
            print(f"         关联考点: {r['related']}")


if __name__ == "__main__":
    main()
