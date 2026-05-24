"""组卷器 — 按标签条件抽题.

spec:
  type_mix: {qtype: count}      eg {"阅读理解": 4, "语法填空": 10, "选义单选": 10}
  require_tags: [tag_id, ...]   必含 (题至少有这些 tag 之一)
  exclude_tags: [tag_id, ...]   必避
  difficulty:    "mixed"|"easy"|"mid"|"hard"
  year_in:       [2020, 2021, 2022]   仅在这些年的真题
  seed:          int

输出:
  paper_id (内存生成, 不入库; 入库走 /api/paper/save)
  questions: [{qb_id, qtype, stem, options, answer, analysis, tags}]
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from typing import Iterable

import duckdb


def _candidate_qids(con: duckdb.DuckDBPyConnection, qtype: str,
                     require_tags: list[str] | None,
                     exclude_tags: list[str] | None,
                     difficulty: str | None,
                     year_in: list[int] | None) -> list[int]:
    where = ["qb.question_type = ?"]
    args: list = [qtype]
    if difficulty and difficulty != "mixed":
        where.append("qb.difficulty = ?"); args.append(difficulty)
    sql = (
        "SELECT DISTINCT qb.qb_id FROM question_bank qb"
    )
    if require_tags:
        sql += (" INNER JOIN question_tags qt_r ON qt_r.qb_id = qb.qb_id "
                "AND qt_r.tag_id IN (" + ",".join(["?"] * len(require_tags)) + ")")
        args += require_tags
    sql += " WHERE " + " AND ".join(where)
    if exclude_tags:
        sql += (" AND NOT EXISTS (SELECT 1 FROM question_tags qt_e "
                "WHERE qt_e.qb_id = qb.qb_id AND qt_e.tag_id IN ("
                + ",".join(["?"] * len(exclude_tags)) + "))")
        args += exclude_tags
    if year_in:
        # year tags
        ytags = [f"year:{y}" for y in year_in]
        sql += (" AND EXISTS (SELECT 1 FROM question_tags qt_y "
                "WHERE qt_y.qb_id = qb.qb_id AND qt_y.tag_id IN ("
                + ",".join(["?"] * len(ytags)) + "))")
        args += ytags
    return [r[0] for r in con.execute(sql, args).fetchall()]


def _full_question(con: duckdb.DuckDBPyConnection, qb_id: int) -> dict:
    row = con.execute("""
        SELECT qb_id, origin, origin_ref, question_type, stem, options_json,
               answer, analysis, difficulty
        FROM question_bank WHERE qb_id = ?
    """, [qb_id]).fetchone()
    if not row:
        return {}
    tags = [r[0] for r in con.execute(
        "SELECT tag_id FROM question_tags WHERE qb_id = ?", [qb_id]
    ).fetchall()]
    return {
        "qb_id": row[0], "origin": row[1], "origin_ref": row[2],
        "qtype": row[3], "stem": row[4][:2000],
        "options": json.loads(row[5]) if row[5] else None,
        "answer": row[6], "analysis": row[7], "difficulty": row[8],
        "tags": tags,
    }


def compose(con: duckdb.DuckDBPyConnection, spec: dict) -> dict:
    rng = random.Random(spec.get("seed"))
    type_mix: dict = spec.get("type_mix", {})
    require = spec.get("require_tags") or None
    exclude = spec.get("exclude_tags") or None
    difficulty = spec.get("difficulty")
    year_in = spec.get("year_in")
    out_questions: list[dict] = []
    misses: dict = {}
    seq = 1
    for qtype, want in type_mix.items():
        pool = _candidate_qids(con, qtype, require, exclude, difficulty, year_in)
        rng.shuffle(pool)
        picked = pool[:want]
        misses[qtype] = max(0, want - len(picked))
        for qb_id in picked:
            q = _full_question(con, qb_id)
            q["seq"] = seq; seq += 1
            out_questions.append(q)
    paper_id = "paper-" + uuid.uuid4().hex[:8]
    return {
        "paper_id": paper_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "spec": spec,
        "target_total": sum(type_mix.values()),
        "actual_total": len(out_questions),
        "shortfalls": misses,
        "questions": out_questions,
    }


def save_paper(con: duckdb.DuckDBPyConnection, paper: dict,
                teacher_id: str | None = None, class_id: str | None = None,
                title: str | None = None) -> str:
    pid = paper["paper_id"]
    con.execute("""
        INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?)
    """, [pid, teacher_id, class_id, title or "untitled",
          json.dumps(paper.get("spec", {}), ensure_ascii=False),
          paper["created_at"]])
    for q in paper["questions"]:
        con.execute(
            "INSERT INTO paper_questions VALUES (?, ?, ?, 1.0)",
            [pid, q["seq"], q["qb_id"]],
        )
    return pid
