"""Materials 合成 — 给 course → 出 (kind, ref_id, year_level, position, source, reason) list.

源:
  - core_items (yaml manual)
  - related_concepts (R1 graph 自动加)
  - 真题溯源 (question_bank tag 命中)
"""
from __future__ import annotations

import duckdb

from . import relations
from .lexicon_filter import grammar_position, word_position


def build_materials_for_course(con: duckdb.DuckDBPyConnection, course: dict) -> list[dict]:
    """合成 1 节 materials (manual + R1 关联 + 真题溯源)."""
    out: list[dict] = []
    seq_counter = [1]   # 用 list 包以便 helper 改

    _add_manual_items(out, seq_counter, course)
    _add_relations(con, out, seq_counter, course)
    _add_real_questions(con, out, seq_counter, course)
    return out


def _add_manual_items(out: list[dict], seq: list[int], course: dict) -> None:
    for it in course.get("core_items") or []:
        out.append({
            "course_id": course["course_id"], "seq": seq[0],
            "kind": it["kind"], "ref_id": it["id"],
            "year_level": it.get("year"), "textbook_position": it.get("position"),
            "source": "manual", "reason": "yaml core_item",
        })
        seq[0] += 1


def _add_relations(con: duckdb.DuckDBPyConnection, out: list[dict], seq: list[int], course: dict) -> None:
    seen = {m["ref_id"] for m in out}
    for it in course.get("core_items") or []:
        for r in relations.related_concepts(con, it["id"], n=relations.MIN_RELATIONS):
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            year, pos = _lookup_year_position(con, r["id"], r["type"])
            out.append({
                "course_id": course["course_id"], "seq": seq[0],
                "kind": r["type"], "ref_id": r["id"],
                "year_level": year, "textbook_position": pos,
                "source": "auto_from_relations", "reason": f"R1 related via {r['relation']}",
            })
            seq[0] += 1


def _add_real_questions(con: duckdb.DuckDBPyConnection, out: list[dict], seq: list[int], course: dict) -> None:
    htags = course.get("homework_tags") or []
    if not htags:
        return
    seen = {m["ref_id"] for m in out}
    placeholders = ",".join("?" * len(htags))
    rows = con.execute(
        f"SELECT DISTINCT qb.qb_id FROM question_bank qb "
        f"JOIN question_tags qt ON qt.qb_id = qb.qb_id "
        f"WHERE qt.tag_id IN ({placeholders}) AND qb.origin='real' "
        f"ORDER BY qb.qb_id LIMIT 5",
        htags,
    ).fetchall()
    for (qb_id,) in rows:
        if str(qb_id) in seen:
            continue
        seen.add(str(qb_id))
        out.append({
            "course_id": course["course_id"], "seq": seq[0],
            "kind": "exam_question", "ref_id": str(qb_id),
            "year_level": None, "textbook_position": None,
            "source": "auto_from_trend", "reason": "近真题命中本节 homework_tags",
        })
        seq[0] += 1


def _lookup_year_position(con: duckdb.DuckDBPyConnection, ref_id: str, kind: str) -> tuple[int | None, str | None]:
    if kind == "word":
        w = ref_id.split(":", 1)[-1] if ref_id.startswith("word:") else ref_id
        r = word_position(con, w)
        return r if r else (None, None)
    if kind == "grammar":
        gid = ref_id if ref_id.startswith("grammar:") else f"grammar:{ref_id}"
        r = grammar_position(con, gid.split(":", 1)[-1])
        return r if r else (None, None)
    return None, None
