"""L1 课时词汇题 PoC — 给定 unit, 出 N 道"选义" 单选 (符合 docs/exercise_design.md L1).

不依赖 LLM, 走纯 graph 查询:
  1. unit_id → introduces_word edge → 该 Unit 引入词 (含 zh_def)
  2. 同 cefr_level 池 (优先 core/standard) → 干扰项词的 zh_def
  3. 4 选 1 标准结构, 答案 evidence 关联 unit_id + word concept_id

设计原则 (架构 §0):
  - 单一计算点: 所有逻辑在 this file, API/前端只展示
  - 走 graph, 不 ad-hoc SQL JOIN
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _unit_words(con: duckdb.DuckDBPyConnection, unit_id: str) -> list[dict]:
    """Pull words for a unit + their zh_def from edges evidence."""
    rows = con.execute("""
        SELECT e.dst_id, e.evidence_json
        FROM edges e
        WHERE e.src_id = ? AND e.relation = 'introduces_word'
    """, [unit_id]).fetchall()
    out = []
    for dst, ev in rows:
        word = dst.split(":", 1)[1] if dst.startswith("word:") else dst
        try:
            data = json.loads(ev or "{}")
        except json.JSONDecodeError:
            data = {}
        zh = (data.get("zh_def") or "").strip()
        if zh:
            out.append({"word": word, "zh_def": zh,
                        "in_curriculum": data.get("in_curriculum", False)})
    return out


def _distractor_pool(con: duckdb.DuckDBPyConnection, level: str = "义教") -> list[dict]:
    """Pool of (word, zh_def) for distractors — pulled from any unit_vocab_intro.
    Filter to 'standard' or 'core' words (avoid LV_extra noise)."""
    try:
        rows = con.execute("""
            SELECT v.word, v.zh_def
            FROM unit_vocab_intro v
            INNER JOIN cefr_vocab c ON c.word = v.word
            WHERE c.cefr_level = ?
              AND v.zh_def IS NOT NULL AND LENGTH(v.zh_def) > 0
        """, [level]).fetchall()
    except duckdb.CatalogException:
        rows = []
    return [{"word": w, "zh_def": zh.strip()} for w, zh in rows if zh and zh.strip()]


def generate_l4_paper(con: duckdb.DuckDBPyConnection, province: str = "辽宁",
                       year_min: int = 2020, n: int = 25,
                       seed: int | None = None) -> dict:
    """L4 模拟卷 — 从真题抽组合, 题型分布对齐辽宁新课标 II 卷.
    不押题, 不合成 — 直接复用历年真题, 标 paper_level=L4_replay.
    """
    rng = random.Random(seed)
    rows = con.execute("""
        SELECT question_id, year, province, question_type, raw_question, answer, analysis
        FROM exam_questions
        WHERE province LIKE ? AND year >= ?
        ORDER BY year DESC
    """, [f"%{province}%", year_min]).fetchall()
    if not rows:
        rows = con.execute("""
            SELECT question_id, year, province, question_type, raw_question, answer, analysis
            FROM exam_questions WHERE year >= ?
        """, [year_min]).fetchall()
    by_type: dict[str, list] = {}
    for r in rows:
        by_type.setdefault(r[3], []).append(r)
    # 新课标 II 卷比例 (近似): 阅读 5 + 完形 1 + 语法填空 1 + 单选 N + 改错 1
    target_mix = {
        "阅读理解": max(5, n // 4),
        "完形填空": max(2, n // 8),
        "语法填空": max(2, n // 12),
        "单选(语法/词汇)": max(5, n // 4),
        "短文改错": 1,
    }
    picked = []
    for qtype, want in target_mix.items():
        pool = by_type.get(qtype, [])[:]
        rng.shuffle(pool)
        for r in pool[:want]:
            picked.append({
                "question_id": r[0], "year": r[1], "province": r[2],
                "question_type": r[3], "stem": (r[4] or "")[:1200],
                "answer": (r[5] or "")[:600], "analysis": (r[6] or "")[:600],
            })
    rng.shuffle(picked)
    for i, p in enumerate(picked):
        p["seq"] = i + 1
    return {
        "paper_level": "L4_replay", "scope": f"province={province} year>={year_min}",
        "target_count": n, "actual_count": len(picked),
        "mix": target_mix, "questions": picked,
        "note": "L4 模拟卷 = 历年真题重组, 非押题/非合成. 见 docs/exercise_design.md",
    }


def generate_l2_quiz(con: duckdb.DuckDBPyConnection, version_key: str, volume_key: str,
                     n: int = 20, seed: int | None = None) -> dict:
    """L2 单元试卷 — 给一整册或一个 unit, 出 N 题混合 (词义 + 填空)."""
    rng = random.Random(seed)
    units = con.execute("""
        SELECT version_key, volume_key, unit_number FROM units
        WHERE version_key=? AND volume_key=? ORDER BY unit_number
    """, [version_key, volume_key]).fetchall()
    if not units:
        return {"error": f"no units for {version_key}/{volume_key}"}
    per_unit = max(1, n // len(units))
    all_questions: list[dict] = []
    for ver, vol, un in units:
        sub = generate_l1_quiz(con, f"unit:{ver}/{vol}/U{un}", n=per_unit,
                                seed=rng.randint(0, 99999))
        for q in sub.get("questions", []):
            q["unit_origin"] = un
            all_questions.append(q)
    rng.shuffle(all_questions)
    for i, q in enumerate(all_questions[:n]):
        q["seq"] = i + 1
    return {
        "paper_level": "L2", "scope": f"{version_key}/{volume_key}",
        "target_count": n, "actual_count": min(n, len(all_questions)),
        "questions": all_questions[:n],
        "compose_note": f"{len(units)} units × {per_unit} 题/unit, shuffle",
    }


def generate_l1_quiz(con: duckdb.DuckDBPyConnection, unit_id: str, n: int = 5,
                     seed: int | None = None) -> dict:
    """生成 N 道 L1 单选 (词义匹配, mid 难度). 两种格式交替: 英→中 / 中→英."""
    rng = random.Random(seed)
    targets = _unit_words(con, unit_id)
    if not targets:
        return {"error": "no words for unit_id", "unit_id": unit_id, "questions": []}
    rng.shuffle(targets)
    picked = targets[:n]
    pool = _distractor_pool(con, level="义教") + _distractor_pool(con, level="必修")
    questions = []
    used_zh = {t["zh_def"] for t in picked}
    for i, t in enumerate(picked):
        distractors_src = [p for p in pool if p["zh_def"] not in used_zh and p["zh_def"] != t["zh_def"]]
        rng.shuffle(distractors_src)
        d3 = distractors_src[:3]
        if len(d3) < 3:
            continue
        q = _build_vocab_question(i, t, d3, rng, unit_id)
        questions.append(q)
    return {
        "paper_level": "L1", "unit_id": unit_id,
        "target_count": n, "actual_count": len(questions),
        "questions": questions,
    }


def _build_vocab_question(seq, target, distractors, rng, unit_id) -> dict:
    """交替出题: 偶数题 英→中 (选中文释义), 奇数题 中→英 (选英文单词)."""
    if seq % 2 == 0:
        stem = f"Choose the correct Chinese meaning of \"{target['word']}\"."
        opts = [target["zh_def"]] + [d["zh_def"] for d in distractors]
    else:
        stem = f"选出与「{target['zh_def']}」对应的英语单词."
        opts = [target["word"]] + [d["word"] for d in distractors]
    rng.shuffle(opts)
    answer_idx = opts.index(target["zh_def"] if seq % 2 == 0 else target["word"])
    return {
        "seq": seq + 1,
        "stem": stem,
        "options": [{"label": chr(65 + k), "text": opt} for k, opt in enumerate(opts)],
        "answer": chr(65 + answer_idx),
        "evidence": {"word_concept": f"word:{target['word']}", "unit_concept": unit_id,
                      "in_curriculum": target["in_curriculum"]},
    }
