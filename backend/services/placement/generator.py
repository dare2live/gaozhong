"""按 spec 从 question_bank 抽题, 覆盖最多 concept (M5 巧妙设计).

策略 (D0 100% 准):
  1. 按 type + difficulty 抽 candidate pool
  2. 优先选未覆盖 tag 的题 (确保 N 题覆盖 N 不同 concept)
  3. 若不够, 接受重复 tag 但题不重复
"""
from __future__ import annotations

import random

import duckdb

random.seed(20260525)   # deterministic placement test (D0 可 reproduce)


def generate_paper(con: duckdb.DuckDBPyConnection, spec: dict) -> dict:
    """按 spec 抽完整一套 placement. 返 {grade, blocks: [{kind, questions: [...]}, ...]}"""
    out_blocks: list[dict] = []
    used_qb_ids: set[int] = set()
    for blk in spec["blocks"]:
        questions = _pick_block_questions(con, blk, used_qb_ids)
        used_qb_ids.update(q["qb_id"] for q in questions)
        out_blocks.append({"kind": blk["kind"], "type": blk["type"],
                           "n_expected": blk["n"], "n_actual": len(questions),
                           "questions": questions})
    return {
        "grade": spec["grade"],
        "target_layer": spec["target_layer"],
        "total_expected": spec["total_questions"],
        "total_actual": sum(b["n_actual"] for b in out_blocks),
        "blocks": out_blocks,
    }


def _pick_block_questions(con: duckdb.DuckDBPyConnection,
                            blk: dict, exclude_ids: set[int]) -> list[dict]:
    """从 candidate pool (按 type + difficulty 过滤) 抽 N 题, 优先未覆盖 tag."""
    pool = _candidate_pool(con, blk["type"], blk.get("difficulty"))
    pool = [q for q in pool if q["qb_id"] not in exclude_ids]
    if not pool:
        return []
    # 按 tag 覆盖优先 (greedy set cover 简版)
    target_n = blk["n"]
    target_kind = blk.get("tag_kind", "word")
    chosen, covered_tags = _greedy_cover(con, pool, target_n, target_kind)
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
                    n: int, tag_kind: str) -> tuple[list[dict], set[str]]:
    """按 tag_kind 覆盖最多 greedy: 每题贪心选"贡献最多新 tag" 的."""
    chosen: list[dict] = []
    covered: set[str] = set()
    remaining = list(pool)
    while remaining and len(chosen) < n:
        # 查每题的此 kind tag
        scored = []
        for q in remaining:
            tags = _question_tags_of_kind(con, q["qb_id"], tag_kind)
            new = len(tags - covered)
            scored.append((new, q, tags))
        scored.sort(key=lambda x: (-x[0], x[1]["qb_id"]))
        _, q, tags = scored[0]
        chosen.append({**q, "tags": sorted(tags)})
        covered.update(tags)
        remaining.remove(q)
    return chosen, covered


def _question_tags_of_kind(con: duckdb.DuckDBPyConnection,
                             qb_id: int, kind: str) -> set[str]:
    rows = con.execute(
        "SELECT qt.tag_id FROM question_tags qt JOIN tag_dictionary td "
        "ON td.tag_id = qt.tag_id "
        "WHERE qt.qb_id = ? AND td.tag_kind = ?",
        [qb_id, kind],
    ).fetchall()
    return {r[0] for r in rows}
