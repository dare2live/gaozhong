#!/usr/bin/env python3
"""课标主题缺口分析 — 发现"哪类主题没题/少题", 指导下一批生成方向."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"

THEME_KEYWORDS = {
    "学校生活": ["school", "class", "teacher", "student", "exam", "homework", "grade"],
    "日常生活": ["family", "friend", "home", "cook", "shop", "daily", "weekend"],
    "兴趣爱好": ["hobby", "music", "sport", "read", "draw", "game", "collect"],
    "个人情感": ["happy", "sad", "worry", "nervous", "proud", "confident", "lonely"],
    "人际沟通": ["talk", "letter", "invite", "advice", "argue", "apologize", "thank"],
    "科学技术": ["science", "technology", "computer", "robot", "AI", "experiment", "discover"],
    "自然环境": ["environment", "pollution", "recycle", "animal", "plant", "ocean", "climate"],
    "社会服务": ["volunteer", "community", "help", "charity", "donate", "service"],
    "文学艺术": ["story", "poem", "novel", "art", "museum", "paint", "drama"],
    "历史文化": ["history", "culture", "tradition", "festival", "ancient", "heritage"],
    "体育健康": ["exercise", "health", "diet", "sleep", "basketball", "run", "fitness"],
    "旅行探险": ["travel", "trip", "visit", "mountain", "adventure", "explore", "camp"],
    "职业规划": ["job", "career", "future", "dream", "plan", "profession", "interview"],
    "中外交流": ["exchange", "abroad", "foreigner", "cultural", "international", "bridge"],
    "媒体信息": ["news", "internet", "media", "phone", "app", "online", "information"],
}


def analyze(con: duckdb.DuckDBPyConnection) -> dict:
    real_rows = con.execute(
        "SELECT stem, answer FROM question_bank WHERE origin = 'real' AND stem IS NOT NULL"
    ).fetchall()
    gen_rows = con.execute(
        "SELECT stem, answer FROM question_bank "
        "WHERE origin IN ('listening_exercise', 'writing_exercise', 'rule_synth') AND stem IS NOT NULL"
    ).fetchall()

    real_hits = _count_themes(real_rows)
    gen_hits = _count_themes(gen_rows)

    gaps = []
    for theme in THEME_KEYWORDS:
        r = real_hits.get(theme, 0)
        g = gen_hits.get(theme, 0)
        real_pct = r / max(sum(real_hits.values()), 1) * 100
        gen_pct = g / max(sum(gen_hits.values()), 1) * 100
        gap = real_pct - gen_pct
        suggested = max(0, round(gap * 0.5)) if gap > 2 else 0
        gaps.append({
            "theme": theme,
            "real_count": r, "gen_count": g,
            "real_pct": round(real_pct, 1), "gen_pct": round(gen_pct, 1),
            "gap": round(gap, 1), "suggested_n": suggested,
        })

    gaps.sort(key=lambda x: x["gap"], reverse=True)
    uncovered = [g for g in gaps if g["gen_count"] == 0]
    score = 100 * (1 - len(uncovered) / max(len(THEME_KEYWORDS), 1))
    total_suggested = sum(g["suggested_n"] for g in gaps)

    return {
        "name": "课标主题缺口分析",
        "score": round(score, 1),
        "pass": score >= 60,
        "themes_total": len(THEME_KEYWORDS),
        "themes_covered_real": sum(1 for g in gaps if g["real_count"] > 0),
        "themes_covered_gen": sum(1 for g in gaps if g["gen_count"] > 0),
        "uncovered": [g["theme"] for g in uncovered],
        "top_gaps": gaps[:5],
        "total_suggested": total_suggested,
        "all_gaps": gaps,
    }


def _count_themes(rows: list) -> dict[str, int]:
    hits: dict[str, int] = {}
    for stem, answer in rows:
        text = ((stem or "") + " " + (answer or "")).lower()
        for theme, keywords in THEME_KEYWORDS.items():
            if any(kw.lower() in text for kw in keywords):
                hits[theme] = hits.get(theme, 0) + 1
    return hits


def main():
    import argparse
    parser = argparse.ArgumentParser(description="课标主题缺口分析")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = analyze(con)
    finally:
        con.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"课标主题缺口分析: {result['score']:.1f}/100")
    print(f"覆盖: 真题 {result['themes_covered_real']}/{result['themes_total']}, "
          f"生成 {result['themes_covered_gen']}/{result['themes_total']}")
    if result["uncovered"]:
        print(f"未覆盖: {result['uncovered']}")
    print(f"\n{'主题':<12} {'真题':>4} {'生成':>4} {'缺口':>6} {'建议补':>4}")
    print("-" * 40)
    for g in result["all_gaps"]:
        marker = " ⚠️" if g["gap"] > 5 else (" ❌" if g["gen_count"] == 0 else "")
        print(f"{g['theme']:<12} {g['real_count']:>4} {g['gen_count']:>4} "
              f"{g['gap']:>+5.1f}% {g['suggested_n']:>4}{marker}")
    print(f"\n总建议新增: {result['total_suggested']} 题")


if __name__ == "__main__":
    main()
