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


def generate_l1_quiz(con: duckdb.DuckDBPyConnection, unit_id: str, n: int = 5,
                     seed: int | None = None) -> dict:
    """生成 N 道 L1 单选 ('选义' 题型). 返回 {paper_id, unit_id, questions:[...]}"""
    rng = random.Random(seed)
    targets = _unit_words(con, unit_id)
    if not targets:
        return {"error": "no words for unit_id", "unit_id": unit_id, "questions": []}
    rng.shuffle(targets)
    picked = targets[:n]
    pool = _distractor_pool(con, level="义教") + _distractor_pool(con, level="必修")
    # Build questions
    questions = []
    used_zh = {t["zh_def"] for t in picked}  # 避免选项重复
    for i, t in enumerate(picked):
        distractors_src = [p for p in pool if p["zh_def"] not in used_zh and p["zh_def"] != t["zh_def"]]
        rng.shuffle(distractors_src)
        d3 = distractors_src[:3]
        if len(d3) < 3:
            continue  # 池不够, skip
        opts = [t["zh_def"]] + [d["zh_def"] for d in d3]
        rng.shuffle(opts)
        answer_idx = opts.index(t["zh_def"])
        questions.append({
            "seq": i + 1,
            "stem": f'"{t["word"]}" 的中文意思是?',
            "options": [{"label": chr(65 + k), "text": opt} for k, opt in enumerate(opts)],
            "answer": chr(65 + answer_idx),
            "evidence": {"word_concept": f"word:{t['word']}", "unit_concept": unit_id,
                          "in_curriculum": t["in_curriculum"]},
        })
    return {
        "paper_level": "L1",
        "unit_id": unit_id,
        "target_count": n,
        "actual_count": len(questions),
        "questions": questions,
    }
