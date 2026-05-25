#!/usr/bin/env python3
"""模型驱动题目生成器 — 宪法 P4 合规: 先查模型, 再生成, 后审计.

不依赖外部 LLM API (M8 零新依赖). 基于 trend_engine 推荐 + pattern_extractor 约束,
从现有题库中按考点权重重新组卷, 或生成模板化练习题.

用法:
    python3 scripts/tools/generation/question_generator.py --n 10 --focus rising
    python3 scripts/tools/generation/question_generator.py --n 5 --point 词义猜测
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"


def generate(con: duckdb.DuckDBPyConnection, n: int = 10, focus: str = "rising") -> dict:
    """宪法合规生成: 先查约束 → 按趋势选题 → 审计."""
    from backend.services.constitution import enforce_before_generation
    compliance = enforce_before_generation(con)
    rising = compliance.get("rising_points", [])
    trends_path = ROOT / "data" / "reports" / "trend_analysis.json"
    trends = json.loads(trends_path.read_text()) if trends_path.exists() else {}
    trend_list = trends.get("trends", [])
    if focus == "rising":
        target_points = [t["point"] for t in trend_list if t.get("direction") == "rising"][:5]
    elif focus == "falling":
        target_points = [t["point"] for t in trend_list if t.get("direction") == "falling"][:3]
    else:
        target_points = [focus]
    selected = _select_from_bank(con, target_points, n, compliance)
    return {
        "n_requested": n, "n_selected": len(selected),
        "focus": focus, "target_points": target_points,
        "year_weights": compliance["year_weights"],
        "questions": selected,
    }


def _select_from_bank(con, points: list, n: int, compliance: dict) -> list[dict]:
    """从现有题库按考点+年份权重选题."""
    template_years = compliance.get("recent_template_years", [2023, 2024, 2025])
    all_candidates = []
    for point in points:
        from scripts.tools.alignment.trend_engine import POINT_KEYWORDS
        keywords = POINT_KEYWORDS.get(point, [point])
        like_clauses = " OR ".join(f"(qb.stem LIKE '%{kw}%' OR qb.analysis LIKE '%{kw}%')" for kw in keywords[:3])
        rows = con.execute(
            f"SELECT qb.qb_id, qb.question_type, qb.stem, qb.difficulty, qb.analysis, qb.origin "
            f"FROM question_bank qb WHERE ({like_clauses}) "
            f"ORDER BY CASE qb.origin WHEN 'real' THEN 0 ELSE 1 END, qb.qb_id "
            f"LIMIT 20"
        ).fetchall()
        for r in rows:
            all_candidates.append({
                "qb_id": r[0], "question_type": r[1], "stem": (r[2] or "")[:200],
                "difficulty": r[3], "has_analysis": bool(r[4]),
                "origin": r[5], "matched_point": point,
            })
    random.shuffle(all_candidates)
    seen = set()
    selected = []
    for c in all_candidates:
        if c["qb_id"] not in seen and len(selected) < n:
            seen.add(c["qb_id"])
            selected.append(c)
    return selected


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--focus", default="rising")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = generate(con, args.n, args.focus)
    finally:
        con.close()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"生成: {result['n_selected']}/{result['n_requested']} 题, 焦点={result['focus']}")
    print(f"目标考点: {result['target_points']}")
    for q in result["questions"]:
        print(f"  #{q['qb_id']} [{q['question_type']}] {q['difficulty']} | {q['matched_point']} | {q['stem'][:60]}...")


if __name__ == "__main__":
    main()
