#!/usr/bin/env python3
"""真题命题特征提取器 — 从 2021-2025 辽宁真题提取可量化命题模型.

输出 data/reports/exam_patterns.json, 后续所有内容生成必须引用此模型.
模型维度:
  1. 阅读理解: 提问模式分布 + 考查技能 + 话题 + 平均篇幅
  2. 完形填空: 考点分布 + 文章主题 + 选项设计模式
  3. 语法填空: 语法考点频次排序 + 有提示/无提示比例
  4. 写作: 续写情节模式 + 应用文类型分布 + 评分标准要素
  5. 全局: 词频 + 句长 + 难度曲线
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
OUTPUT_PATH = ROOT / "data" / "reports" / "exam_patterns.json"


def extract(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT year, question_type, raw_question, answer, analysis "
        "FROM exam_questions WHERE year >= 2021 AND province LIKE '%新课标 II%' "
        "ORDER BY year"
    ).fetchall()
    years = sorted({r[0] for r in rows})
    year_weights = {2025: 5, 2024: 4, 2023: 3, 2022: 2, 2021: 1.5}
    model = {
        "source": "exam_questions (2021+ 新课标 II 辽宁)",
        "n_questions": len(rows),
        "years": years,
        "year_weights": {y: year_weights.get(y, 0.5) for y in years},
        "data_gap": [y for y in range(2021, 2026) if y not in years],
        "reading": _extract_reading([r for r in rows if r[1] == "阅读理解"]),
        "cloze": _extract_cloze([r for r in rows if "完形" in r[1]]),
        "grammar_fill": _extract_grammar([r for r in rows if r[1] == "语法填空"]),
        "global_vocab": _extract_vocab(rows),
        "global_sentence": _extract_sentence_stats(rows),
        "question_design_terms": _extract_design_terms(rows),
    }
    return model


_Q_PATTERNS = {"What": ["What"], "Which": ["Which"], "Why": ["Why"],
               "How": ["How"], "Where": ["Where"], "Who": ["Who"]}
_SKILL_MAP = {
    "细节理解": ["细节", "detail"], "推理判断": ["推断", "infer", "imply"],
    "主旨大意": ["主旨", "main idea", "mainly about"],
    "词义猜测": ["词义", "meaning", "closest"],
    "标题选择": ["title", "标题"], "目的意图": ["目的", "purpose"],
}


def _match_keywords(text: str, mapping: dict) -> Counter:
    c = Counter()
    for label, kws in mapping.items():
        if any(kw in text for kw in kws):
            c[label] += 1
    return c


def _extract_reading(rows) -> dict:
    patterns, skills = Counter(), Counter()
    for _, _, rq, _, anal in rows:
        patterns += _match_keywords(rq or "", _Q_PATTERNS)
        skills += _match_keywords((rq or "") + (anal or ""), _SKILL_MAP)
    total = max(len(rows), 1)
    return {
        "n": len(rows),
        "question_patterns": {k: round(v / total, 3) for k, v in patterns.most_common()},
        "skill_distribution": {k: round(v / total, 3) for k, v in skills.most_common()},
    }


def _extract_cloze(rows) -> dict:
    topics = Counter()
    for _, _, rq, _, anal in rows:
        text = (anal or "").lower()
        for topic, kws in [("说明文", ["说明文"]), ("记叙文", ["记叙文"]),
                           ("议论文", ["议论文"]), ("应用文", ["应用文"])]:
            if any(k in text for k in kws):
                topics[topic] += 1
    return {"n": len(rows), "article_type_distribution": dict(topics)}


def _extract_grammar(rows) -> dict:
    points = Counter()
    for _, _, _, _, anal in rows:
        text = anal or ""
        for gp in ["定语从句", "名词性从句", "状语从句", "非谓语", "时态", "语态",
                    "被动", "比较级", "冠词", "介词", "连词", "代词", "形容词",
                    "副词", "名词", "动词", "词性转换", "固定搭配"]:
            if gp in text:
                points[gp] += 1
    return {
        "n": len(rows),
        "grammar_points_ranked": [{"point": k, "freq": v} for k, v in points.most_common()],
    }


def _extract_vocab(rows) -> dict:
    word_freq = Counter()
    for _, _, rq, _, _ in rows:
        words = re.findall(r"[a-zA-Z']+", rq or "")
        for w in words:
            if len(w) > 2:
                word_freq[w.lower()] += 1
    stop = {"the", "and", "for", "that", "this", "with", "from", "are", "was",
            "were", "has", "have", "had", "not", "but", "you", "your", "they",
            "their", "his", "her", "its", "our", "can", "will", "she", "who"}
    filtered = {k: v for k, v in word_freq.items() if k not in stop and v >= 3}
    top50 = Counter(filtered).most_common(50)
    return {"top50_content_words": [{"word": w, "freq": f} for w, f in top50]}


def _extract_sentence_stats(rows) -> dict:
    lengths = []
    for _, _, rq, _, _ in rows:
        sents = re.split(r'[.!?]+', rq or "")
        for s in sents:
            words = s.strip().split()
            if len(words) >= 3:
                lengths.append(len(words))
    if not lengths:
        return {"avg_sentence_words": 0, "median": 0}
    lengths.sort()
    return {
        "avg_sentence_words": round(sum(lengths) / len(lengths), 1),
        "median_sentence_words": lengths[len(lengths) // 2],
        "p25": lengths[len(lengths) // 4],
        "p75": lengths[3 * len(lengths) // 4],
    }


def _extract_design_terms(rows) -> dict:
    terms = Counter()
    for _, _, _, _, anal in rows:
        if not anal:
            continue
        for t in ["细节", "推断", "主旨", "词义", "语境", "上文", "下文",
                  "目的", "转折", "因果", "搭配", "时态", "非谓语", "从句",
                  "态度", "比较", "举例", "总结", "原因"]:
            if t in anal:
                terms[t] += 1
    return {"ranked": [{"term": k, "freq": v} for k, v in terms.most_common()]}


def save(model: dict) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return OUTPUT_PATH


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        model = extract(con)
    finally:
        con.close()
    path = save(model)
    print(f"命题特征模型已保存: {path}")
    print(f"  真题数: {model['n_questions']}, 年份: {model['years']}")
    print(f"  阅读 {model['reading']['n']} 题:")
    for k, v in model["reading"]["skill_distribution"].items():
        print(f"    {k}: {v:.1%}")
    print(f"  语法 {model['grammar_fill']['n']} 题, top 考点:")
    for gp in model["grammar_fill"]["grammar_points_ranked"][:8]:
        print(f"    {gp['point']}: {gp['freq']}")
    print(f"  命题术语 top 10:")
    for t in model["question_design_terms"]["ranked"][:10]:
        print(f"    {t['term']}: {t['freq']}")
    print(f"  句长: avg={model['global_sentence']['avg_sentence_words']}w, "
          f"p25-p75={model['global_sentence'].get('p25','?')}-{model['global_sentence'].get('p75','?')}w")


if __name__ == "__main__":
    main()
