#!/usr/bin/env python3
"""细粒度考点标注器 — 从真题 analysis 中逐题提取考点标签.

GAOKAO-Bench 的 analysis 字段含 "【36题详解】...【37题详解】..." 格式.
本工具拆分成逐题, 并自动标注每题的考点类型.

输出: data/reports/fine_grain_annotations.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
OUTPUT = ROOT / "data" / "reports" / "fine_grain_annotations.json"

SKILL_RULES = [
    ("细节理解", ["细节", "根据第", "according to", "文中提到", "原文"]),
    ("推理判断", ["推断", "推知", "infer", "imply", "可知", "由此可知"]),
    ("主旨大意", ["主旨", "中心", "main idea", "mainly about", "全文"]),
    ("词义猜测", ["词义", "meaning", "划线", "underlined", "closest"]),
    ("标题选择", ["标题", "title", "best title"]),
    ("目的意图", ["目的", "purpose", "意图", "为了"]),
    ("作者态度", ["态度", "attitude", "tone", "观点"]),
    ("语境推断", ["语境", "上下文", "context", "逻辑"]),
    ("定语从句", ["定语从句", "which", "who", "关系代词", "关系副词"]),
    ("非谓语动词", ["非谓语", "to do", "doing", "done", "不定式", "分词"]),
    ("时态语态", ["时态", "语态", "被动", "过去式", "完成时"]),
    ("词性转换", ["词性", "形容词", "副词", "名词变", "动词变"]),
    ("冠词介词", ["冠词", "介词", "a/an", "the", "固定搭配"]),
    ("连词代词", ["连词", "代词", "however", "therefore", "指代"]),
    ("七选五衔接", ["衔接", "上文", "下文", "承上启下", "过渡"]),
    ("完形语境", ["完形", "语境推断", "上下文选词"]),
    ("短文改错", ["改错", "改正", "主谓一致", "时态错误"]),
]


def annotate(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT question_id, year, question_type, raw_question, analysis "
        "FROM exam_questions WHERE year >= 2021 AND analysis IS NOT NULL "
        "AND LENGTH(analysis) > 100 ORDER BY year"
    ).fetchall()
    all_items = []
    for qid, year, qtype, raw, analysis in rows:
        sub_items = _split_sub_questions(qid, year, qtype, analysis)
        all_items.extend(sub_items)
    skill_dist = Counter()
    for item in all_items:
        for skill in item["skills"]:
            skill_dist[skill] += 1
    return {
        "total_blocks": len(rows),
        "total_sub_items": len(all_items),
        "years": sorted({i["year"] for i in all_items}),
        "skill_distribution": dict(skill_dist.most_common()),
        "items": all_items,
    }


def _split_sub_questions(qid, year, qtype, analysis) -> list[dict]:
    """拆分 analysis 中的逐题解析 (【36题详解】格式)."""
    parts = re.split(r'[【\[]\s*(\d+)\s*题详解\s*[】\]]', analysis)
    items = []
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            q_num = int(parts[i])
            text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            skills = _detect_skills(text)
            items.append({
                "parent_id": qid, "year": year, "question_type": qtype,
                "sub_question_number": q_num,
                "analysis_excerpt": text[:300],
                "skills": skills,
            })
    else:
        other = re.split(r'\[(\d+)题详解\]|\[详解\]', analysis)
        if len(other) >= 3:
            for i in range(1, len(other), 2):
                if other[i] and other[i].isdigit():
                    q_num = int(other[i])
                    text = other[i + 1].strip() if i + 1 < len(other) else ""
                    items.append({
                        "parent_id": qid, "year": year, "question_type": qtype,
                        "sub_question_number": q_num,
                        "analysis_excerpt": text[:300],
                        "skills": _detect_skills(text),
                    })
    if not items:
        items.append({
            "parent_id": qid, "year": year, "question_type": qtype,
            "sub_question_number": 0,
            "analysis_excerpt": analysis[:300],
            "skills": _detect_skills(analysis),
        })
    return items


def _detect_skills(text: str) -> list[str]:
    found = []
    for skill, keywords in SKILL_RULES:
        if any(kw in text for kw in keywords):
            found.append(skill)
    return found if found else ["未分类"]


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = annotate(con)
    finally:
        con.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"细粒度标注完成: {OUTPUT}")
    print(f"  真题块: {result['total_blocks']}, 拆分子题: {result['total_sub_items']}")
    print(f"  年份: {result['years']}")
    print(f"\n考点分布 (逐题级):")
    for skill, n in result["skill_distribution"].items():
        print(f"  {skill}: {n}")


if __name__ == "__main__":
    main()
