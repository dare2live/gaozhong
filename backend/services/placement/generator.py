"""按 spec 从 question_bank 抽题, 覆盖最多 concept (M5 巧妙设计).

策略 (D0 100% 准):
  1. 按 type + difficulty 抽 candidate pool
  2. 优先选未覆盖 tag 的题 (确保 N 题覆盖 N 不同 concept)
  3. 若不够, 接受重复 tag 但题不重复
"""
from __future__ import annotations

import hashlib
import random

import duckdb


def _seed_for(student_id: str | None, grade: str) -> int:
    """Codex Q5: 按 student_id + grade 派生 seed, 每人不同卷, 仍可复现."""
    raw = f"{student_id or 'anon'}::{grade}::placement-v1"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def generate_paper(con: duckdb.DuckDBPyConnection, spec: dict,
                     student_id: str | None = None) -> dict:
    """按 spec 抽完整一套 placement. Codex Q5: per-student seed."""
    rng = random.Random(_seed_for(student_id, spec["grade"]))
    out_blocks: list[dict] = []
    used_qb_ids: set[int] = set()
    for blk in spec["blocks"]:
        questions = _pick_block_questions(con, blk, used_qb_ids, rng)
        used_qb_ids.update(q["qb_id"] for q in questions)
        out_blocks.append({"kind": blk["kind"], "type": blk["type"],
                           "n_expected": blk["n"], "n_actual": len(questions),
                           "questions": questions})
    return {
        "grade": spec["grade"],
        "target_layer": spec["target_layer"],
        "student_id": student_id,
        "total_expected": spec["total_questions"],
        "total_actual": sum(b["n_actual"] for b in out_blocks),
        "blocks": out_blocks,
    }


def _pick_block_questions(con: duckdb.DuckDBPyConnection,
                            blk: dict, exclude_ids: set[int],
                            rng: random.Random) -> list[dict]:
    """从 candidate pool (按 type + difficulty 过滤) 抽 N 题, 加权 greedy."""
    pool = _candidate_pool(con, blk["type"], blk.get("difficulty"))
    pool = [q for q in pool if q["qb_id"] not in exclude_ids]
    if not pool:
        return []
    # Codex Q5: 随机打乱 pool — 同候选不同顺序, per-student 不同
    rng.shuffle(pool)
    target_n = blk["n"]
    target_kind = blk.get("tag_kind", "word")
    tag_freq = _tag_frequencies(con, target_kind)
    chosen, _ = _greedy_cover(con, pool, target_n, target_kind, tag_freq)
    return chosen


def _candidate_pool(con: duckdb.DuckDBPyConnection,
                      qtype: str, difficulty: str | None) -> list[dict]:
    """先严格按 type+difficulty, 不够再放宽到任意 difficulty (deterministic 排序)."""
    strict = _query_pool(con, qtype, difficulty) if difficulty else []
    if strict:
        return strict
    return _query_pool(con, qtype, None)


def _query_pool(con: duckdb.DuckDBPyConnection,
                  qtype: str, difficulty: str | None) -> list[dict]:
    sql = ("SELECT qb_id, question_type, stem, options_json, answer, difficulty "
           "FROM question_bank WHERE question_type = ?")
    args: list = [qtype]
    if difficulty:
        sql += " AND difficulty = ?"
        args.append(difficulty)
    sql += " ORDER BY qb_id"
    return [
        {"qb_id": r[0], "question_type": r[1], "stem": r[2],
         "options_json": r[3], "answer": r[4], "difficulty": r[5]}
        for r in con.execute(sql, args).fetchall()
    ]


def _greedy_cover(con: duckdb.DuckDBPyConnection, pool: list[dict],
                    n: int, tag_kind: str,
                    tag_freq: dict[str, int]) -> tuple[list[dict], set[str]]:
    """加权 greedy (Codex Q2): score = sum(rarity) over new tags.

    rarity(tag) = log(1 + total_questions / max(1, tag_freq[tag]))
    稀有 tag 优先抽, 让短卷覆盖更分散的概念.
    """
    import math
    total_q = sum(tag_freq.values()) or 1
    chosen: list[dict] = []
    covered: set[str] = set()
    remaining = list(pool)
    while remaining and len(chosen) < n:
        best_score, best_q, best_tags = -1.0, None, set()
        for q in remaining:
            tags = _question_tags_of_kind(con, q["qb_id"], tag_kind)
            new = tags - covered
            score = sum(math.log(1 + total_q / max(1, tag_freq.get(t, 1))) for t in new)
            if score > best_score:
                best_score, best_q, best_tags = score, q, tags
        if best_q is None:
            break
        chosen.append({**best_q, "tags": sorted(best_tags)})
        covered.update(best_tags)
        remaining.remove(best_q)
    return chosen, covered


def _tag_frequencies(con: duckdb.DuckDBPyConnection, tag_kind: str) -> dict[str, int]:
    """每 tag 在 question_tags 出现次数 — 用于加权 greedy."""
    rows = con.execute(
        "SELECT qt.tag_id, COUNT(*) FROM question_tags qt "
        "JOIN tag_dictionary td ON td.tag_id = qt.tag_id "
        "WHERE td.tag_kind = ? GROUP BY qt.tag_id",
        [tag_kind],
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _question_tags_of_kind(con: duckdb.DuckDBPyConnection,
                             qb_id: int, kind: str) -> set[str]:
    rows = con.execute(
        "SELECT qt.tag_id FROM question_tags qt JOIN tag_dictionary td "
        "ON td.tag_id = qt.tag_id "
        "WHERE qt.qb_id = ? AND td.tag_kind = ?",
        [qb_id, kind],
    ).fetchall()
    return {r[0] for r in rows}
