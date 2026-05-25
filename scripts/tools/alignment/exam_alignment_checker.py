#!/usr/bin/env python3
"""考试对齐度检测器 — 8 维度检查生成内容与真题命题模式偏离度. JSON 模式供 Optuna."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"

# 高考真实结构 (新课标 II 卷, 2021+)
GAOKAO_STRUCTURE = {
    "听力": {"score": 30, "questions": 20, "weight": 0.20},
    "阅读理解": {"score": 50, "questions": 15, "weight": 0.333},
    "完形填空": {"score": 15, "questions": 15, "weight": 0.10},
    "语法填空": {"score": 15, "questions": 10, "weight": 0.10},
    "应用文": {"score": 15, "questions": 1, "weight": 0.10},
    "续写": {"score": 25, "questions": 1, "weight": 0.167},
}

GAOKAO_LISTENING_STRUCTURE = {
    "短对话": {"n_dialogs": 5, "q_per": 1, "total_q": 5},
    "长对话": {"n_dialogs": 2, "q_per": 3, "total_q": 6},
    "独白": {"n_dialogs": 2, "q_per": 3, "total_q": 6},
    "填空": {"n_dialogs": 1, "q_per": 3, "total_q": 3},
}

LISTENING_SKILL_CATEGORIES = ["场所推断", "职业/关系推断", "时间/数字", "态度/情感",
                              "原因/目的", "建议/计划", "主旨大意", "细节信息"]

APPLIED_WRITING_TYPES = [
    "邀请信", "感谢信", "建议信", "通知", "申请信",
    "求助信", "道歉信", "推荐信", "投稿", "回信",
]

APPLIED_FORMAT_ELEMENTS = [
    "Dear", "Yours", "Li Hua", "I am writing",
]

NARRATIVE_ELEMENTS = [
    "Paragraph 1:", "Paragraph 2:", "续写两段",
]

THRESHOLDS = {
    "type_coverage": 60,
    "difficulty_alignment": 50,
    "vocab_overlap": 30,
    "topic_alignment": 40,
    "analysis_completeness": 70,
    "listening_structure": 50,
    "writing_format": 60,
    "overall": 55,
}

def _kl_divergence(p: dict, q: dict) -> float:
    """Symmetric KL divergence (Jensen-Shannon-like)."""
    all_keys = set(p) | set(q)
    total_p = max(sum(p.values()), 1)
    total_q = max(sum(q.values()), 1)
    kl = 0.0
    for k in all_keys:
        pi = max(p.get(k, 0) / total_p, 1e-10)
        qi = max(q.get(k, 0) / total_q, 1e-10)
        m = (pi + qi) / 2
        kl += 0.5 * (pi * math.log(pi / m) + qi * math.log(qi / m))
    return kl

def _score_from_kl(kl: float, max_kl: float = 0.5) -> float:
    """KL → 0-100 score (0 divergence = 100)."""
    return max(0, 100 * (1 - kl / max_kl))

def _extract_words(text: str) -> list[str]:
    """Extract English words from text."""
    return [w.lower() for w in re.findall(r"[a-zA-Z']+", text) if len(w) > 1]

def check_type_coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 1: 高考 6 大题型覆盖率."""
    rows = con.execute("""
        SELECT question_type, COUNT(*) FROM question_bank
        WHERE origin IN ('real', 'listening_exercise', 'writing_exercise')
        GROUP BY 1
    """).fetchall()
    have = {r[0] for r in rows}
    gaokao_types = set(GAOKAO_STRUCTURE.keys())
    mapped = set()
    for gt in gaokao_types:
        for h in have:
            if gt in h or (gt == "听力" and "听力" in h):
                mapped.add(gt)
    score = 100 * len(mapped) / max(len(gaokao_types), 1)
    missing = gaokao_types - mapped
    return {
        "name": "题型覆盖率",
        "score": round(score, 1),
        "detail": f"覆盖 {len(mapped)}/{len(gaokao_types)}: {sorted(mapped)}",
        "missing": sorted(missing),
        "pass": score >= THRESHOLDS["type_coverage"],
    }

def check_difficulty_alignment(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 2: 难度分布 vs 真题分布."""
    real = dict(con.execute("""
        SELECT difficulty, COUNT(*) FROM question_bank WHERE origin = 'real'
        GROUP BY 1
    """).fetchall())
    gen = dict(con.execute("""
        SELECT difficulty, COUNT(*) FROM question_bank
        WHERE origin IN ('listening_exercise', 'writing_exercise', 'rule_synth')
        GROUP BY 1
    """).fetchall())
    if not gen:
        return {"name": "难度分布偏离", "score": 0, "detail": "无生成题", "pass": False}
    kl = _kl_divergence(real, gen)
    score = _score_from_kl(kl, max_kl=0.6)
    return {
        "name": "难度分布偏离",
        "score": round(score, 1),
        "detail": f"真题={real}, 生成={gen}, JSD={kl:.4f}",
        "pass": score >= THRESHOLDS["difficulty_alignment"],
    }

def check_vocab_overlap(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 3: 生成题词汇 vs 真题词汇重叠."""
    real_stems = con.execute(
        "SELECT stem FROM question_bank WHERE origin = 'real' AND stem IS NOT NULL"
    ).fetchall()
    gen_stems = con.execute(
        "SELECT stem FROM question_bank WHERE origin IN ('listening_exercise', 'writing_exercise') AND stem IS NOT NULL"
    ).fetchall()
    real_words = set()
    for (s,) in real_stems:
        real_words.update(_extract_words(s))
    gen_words = set()
    for (s,) in gen_stems:
        gen_words.update(_extract_words(s))
    if not gen_words:
        return {"name": "词汇重叠度", "score": 0, "detail": "无生成题", "pass": False}
    overlap = real_words & gen_words
    score = 100 * len(overlap) / max(len(gen_words), 1)
    return {
        "name": "词汇重叠度",
        "score": round(score, 1),
        "detail": f"真题词={len(real_words)}, 生成词={len(gen_words)}, 重叠={len(overlap)}, 比={score:.1f}%",
        "pass": score >= THRESHOLDS["vocab_overlap"],
    }

CURRICULUM_KEYWORDS = {
    "生活学习": "school class study homework exam learn family friend daily weekend".split(),
    "做人做事": "honest responsible brave kind help effort goal plan dream".split(),
    "社会沟通": "volunteer community invite thank advice letter communicate".split(),
    "文艺体育": "story novel art music sport basketball exercise drama museum".split(),
    "历史文化": "history culture tradition festival ancient heritage society".split(),
    "科学技术": "science technology computer experiment discover research robot".split(),
    "自然生态": "nature animal plant ocean forest river ecology species".split(),
    "环境保护": "environment pollution recycle climate protect green waste".split(),
    "灾害防范": "disaster earthquake flood safety emergency rescue prevent".split(),
    "宇宙探索": "space Mars planet universe astronaut star satellite explore".split(),
}

def check_topic_alignment(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 4: 听力/写作场景 vs 课标主题语境 (双语关键词匹配)."""
    gen_stems = con.execute(
        "SELECT stem, answer FROM question_bank "
        "WHERE origin IN ('listening_exercise', 'writing_exercise') AND stem IS NOT NULL"
    ).fetchall()
    topic_hits = 0
    total = len(gen_stems)
    for stem, answer in gen_stems:
        text = ((stem or "") + " " + (answer or "")).lower()
        for keywords in CURRICULUM_KEYWORDS.values():
            if any(kw in text for kw in keywords):
                topic_hits += 1
                break
    score = 100 * topic_hits / max(total, 1)
    return {
        "name": "话题对齐 (课标主题语境)",
        "score": round(score, 1),
        "detail": f"{topic_hits}/{total} 题命中课标主题 (10 主题群双语匹配)",
        "pass": score >= THRESHOLDS["topic_alignment"],
    }

def check_analysis_completeness(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 5: 生成题 analysis 完整度."""
    rows = con.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE analysis IS NOT NULL AND analysis != ''),
               AVG(LENGTH(analysis)) FILTER (WHERE analysis IS NOT NULL AND analysis != '')
        FROM question_bank
        WHERE origin IN ('listening_exercise', 'writing_exercise')
    """).fetchone()
    total, has_analysis, avg_len = rows
    if total == 0:
        return {"name": "解析完整度", "score": 0, "detail": "无生成题", "pass": False}
    coverage = 100 * has_analysis / total
    len_score = min(100, (avg_len or 0) / 2)
    score = coverage * 0.6 + len_score * 0.4
    return {
        "name": "解析完整度",
        "score": round(score, 1),
        "detail": f"{has_analysis}/{total} 有解析, avg={avg_len:.0f} chars" if avg_len else f"{has_analysis}/{total}",
        "pass": score >= THRESHOLDS["analysis_completeness"],
    }

def check_listening_structure(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 6: 听力 Section 结构对齐."""
    rows = dict(con.execute("""
        SELECT question_type, COUNT(*) FROM question_bank
        WHERE origin = 'listening_exercise'
        GROUP BY 1
    """).fetchall())
    if not rows:
        return {"name": "听力结构对齐", "score": 0, "detail": "无听力题", "pass": False}
    actual = {
        "短对话": rows.get("听力短对话", 0),
        "长对话": rows.get("听力长对话", 0),
        "独白": rows.get("听力独白", 0),
    }
    expected = {k: v["total_q"] for k, v in GAOKAO_LISTENING_STRUCTURE.items() if k != "填空"}
    kl = _kl_divergence(expected, actual)
    score = _score_from_kl(kl, max_kl=0.4)
    transcript_count = con.execute("""
        SELECT COUNT(*) FROM question_bank
        WHERE origin = 'listening_exercise' AND transcript IS NOT NULL AND transcript != ''
    """).fetchone()[0]
    total_listen = sum(actual.values())
    transcript_pct = 100 * transcript_count / max(total_listen, 1)
    score = score * 0.7 + min(100, transcript_pct) * 0.3
    return {
        "name": "听力结构对齐",
        "score": round(score, 1),
        "detail": f"实际={actual}, 期望~={expected}, transcript={transcript_count}/{total_listen}",
        "pass": score >= THRESHOLDS["listening_structure"],
    }

def _score_narrative(stem, answer, analysis) -> float:
    text = (stem or "") + (answer or "") + (analysis or "")
    has_para = sum(1 for e in NARRATIVE_ELEMENTS if e in text)
    has_answer = len(answer or "") > 100
    has_analysis = len(analysis or "") > 30
    return 100 * (has_para / len(NARRATIVE_ELEMENTS) * 0.4 + has_answer * 0.3 + has_analysis * 0.3)

def _score_applied(answer, analysis) -> float:
    text = (answer or "")
    has_fmt = sum(1 for e in APPLIED_FORMAT_ELEMENTS if e in text)
    has_analysis = len(analysis or "") > 30
    word_ok = 60 <= len(_extract_words(text)) <= 200
    return 100 * (has_fmt / len(APPLIED_FORMAT_ELEMENTS) * 0.4 + has_analysis * 0.3 + word_ok * 0.3)

def check_writing_format(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 7: 写作格式对齐 (续写段落结构 + 应用文格式)."""
    narrative_rows = con.execute(
        "SELECT stem, answer, analysis FROM question_bank "
        "WHERE question_type = '续写' AND origin = 'writing_exercise'"
    ).fetchall()
    applied_rows = con.execute(
        "SELECT stem, answer, analysis FROM question_bank "
        "WHERE question_type = '应用文' AND origin = 'writing_exercise'"
    ).fetchall()
    scores = [_score_narrative(*r) for r in narrative_rows]
    scores += [_score_applied(r[1], r[2]) for r in applied_rows]
    if not scores:
        return {"name": "写作格式对齐", "score": 0, "detail": "无写作题", "pass": False}
    avg = sum(scores) / len(scores)
    types_used = {t for _, _, _ in applied_rows for t in APPLIED_WRITING_TYPES
                  if t in (_ or "").lower()}
    return {
        "name": "写作格式对齐",
        "score": round(avg, 1),
        "detail": f"续写={len(narrative_rows)}, 应用文={len(applied_rows)}, 格式均分={avg:.1f}, 应用文类型={len(types_used)}种",
        "pass": avg >= THRESHOLDS["writing_format"],
    }

def check_listening_skill_coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """维度 8: 听力考查技能覆盖 (场所/关系/数字/态度/主旨等)."""
    rows = con.execute("""
        SELECT stem, analysis FROM question_bank
        WHERE origin = 'listening_exercise'
    """).fetchall()
    if not rows:
        return {"name": "听力技能覆盖", "score": 0, "detail": "无听力题", "pass": False}
    skill_hits = Counter()
    skill_keywords = {
        "场所推断": ["where", "place", "take place", "场所", "场景"],
        "职业/关系推断": ["relationship", "who", "occupation", "关系", "职业"],
        "时间/数字": ["when", "time", "how much", "how many", "时间", "数字"],
        "态度/情感": ["feel", "think", "attitude", "opinion", "情感", "态度"],
        "原因/目的": ["why", "reason", "purpose", "原因"],
        "建议/计划": ["will", "plan", "suggest", "should", "计划", "建议"],
        "主旨大意": ["mainly", "about", "topic", "purpose of", "主旨"],
        "细节信息": ["what", "which", "NOT", "细节"],
    }
    for stem, analysis in rows:
        text = ((stem or "") + " " + (analysis or "")).lower()
        for skill, keywords in skill_keywords.items():
            if any(kw.lower() in text for kw in keywords):
                skill_hits[skill] += 1
    covered = sum(1 for s in LISTENING_SKILL_CATEGORIES if skill_hits.get(s, 0) > 0)
    score = 100 * covered / len(LISTENING_SKILL_CATEGORIES)
    return {
        "name": "听力技能覆盖",
        "score": round(score, 1),
        "detail": f"覆盖 {covered}/{len(LISTENING_SKILL_CATEGORIES)}: {dict(skill_hits)}",
        "pass": score >= 50,
    }

def run_all(con: duckdb.DuckDBPyConnection, sections: list[str] | None = None) -> dict:
    """Run all checks, return overall report."""
    checks = [
        ("type_coverage", check_type_coverage),
        ("difficulty_alignment", check_difficulty_alignment),
        ("vocab_overlap", check_vocab_overlap),
        ("topic_alignment", check_topic_alignment),
        ("analysis_completeness", check_analysis_completeness),
        ("listening_structure", check_listening_structure),
        ("listening_skill_coverage", check_listening_skill_coverage),
        ("writing_format", check_writing_format),
    ]
    if sections:
        if "listening" in sections:
            checks = [c for c in checks if "listening" in c[0]]
        elif "writing" in sections:
            checks = [c for c in checks if "writing" in c[0] or c[0] in ("analysis_completeness",)]
    results = {}
    for key, fn in checks:
        results[key] = fn(con)
    scores = [r["score"] for r in results.values()]
    overall = sum(scores) / max(len(scores), 1)
    results["overall"] = {
        "name": "综合对齐度",
        "score": round(overall, 1),
        "detail": f"{len(scores)} 维度加权平均",
        "pass": overall >= THRESHOLDS["overall"],
    }
    return results

def _print_report(results: dict) -> None:
    print("=" * 60)
    print("考试对齐度检测报告 (Exam Alignment Report)")
    print("=" * 60)
    for key, r in results.items():
        if key == "overall":
            continue
        status = "✅" if r["pass"] else "⚠️"
        print(f"\n{status} [{r['score']:5.1f}] {r['name']}")
        print(f"   {r['detail']}")
        if r.get("missing"):
            print(f"   缺失: {r['missing']}")
    ov = results["overall"]
    status = "✅" if ov["pass"] else "❌"
    print(f"\n{'=' * 60}")
    print(f"{status} 综合对齐度: {ov['score']:.1f} / 100")
    print(f"{'=' * 60}")
    if not ov["pass"]:
        print("\n改进建议:")
        for key, r in results.items():
            if key != "overall" and not r["pass"]:
                print(f"  - {r['name']}: 当前 {r['score']:.1f}, 需 ≥ {THRESHOLDS.get(key, '?')}")

def main():
    parser = argparse.ArgumentParser(description="考试对齐度检测器")
    parser.add_argument("--listening", action="store_true")
    parser.add_argument("--writing", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    sections = ["listening"] if args.listening else (["writing"] if args.writing else None)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        results = run_all(con, sections)
    finally:
        con.close()

    if args.json:
        print(json.dumps({k: {"score": v["score"], "pass": v["pass"]}
                          for k, v in results.items()}, ensure_ascii=False, indent=2))
    else:
        _print_report(results)
        if not results["overall"]["pass"]:
            sys.exit(1)

if __name__ == "__main__":
    main()
