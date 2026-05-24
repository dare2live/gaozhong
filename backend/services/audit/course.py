"""第五阶段 8 audit (R1-R6 + 听力 + 政治) — Stop hook 集成.

每函数签名: (con) -> list[dict {audit_kind, severity (OK/WARN/FAIL), target, expected, actual, ...}]
"""
from __future__ import annotations

import duckdb

from backend.services.course import (homework as hw_mod, loader, relations,
                                      scenarios)
from backend.services.course.lexicon_filter import (allowed_words_for,
                                                     word_position)


# ===== R1 =====
def audit_course_relations(con: duckdb.DuckDBPyConnection) -> list[dict]:
    out: list[dict] = []
    rows = con.execute(
        "SELECT course_id, ref_id FROM course_materials "
        "WHERE kind IN ('word','grammar') AND source='manual'"
    ).fetchall()
    if not rows:
        return [_o("audit_course_relations", "WARN", "(empty)", "any", "no manual core_items in DB")]
    fail_n = 0
    for cid, ref in rows:
        n = relations.count_relations(con, ref)
        if n < relations.MIN_RELATIONS:
            out.append(_o("audit_course_relations", "FAIL", f"course={cid} item={ref}",
                          f">={relations.MIN_RELATIONS}", str(n)))
            fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_course_relations", "OK", "all course core items", "≥3 relations", "all pass"))
    return out


# ===== R2 =====
def audit_course_no_textbook_copy(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """R2: 讲义里去除 HTML 后, 与教材 section_text 无 ≥10 词连续重叠.

    P1.2 实装: 从 course_handouts 表读 md (init_db 灌), 调 scenarios.has_textbook_copy.
    若 course_handouts 空 → WARN; 否则真扫.
    """
    n_handouts = con.execute("SELECT COUNT(*) FROM course_handouts").fetchone()[0]
    if n_handouts == 0:
        return [_o("audit_course_no_textbook_copy", "WARN", "(no handouts)",
                   "course_handouts table populated",
                   "init_db 未灌讲义, 跑 init_db 后再 audit")]
    rows = con.execute("SELECT course_id, md FROM course_handouts").fetchall()
    out: list[dict] = []
    fail_n = 0
    for cid, md in rows:
        clean = _strip_html(md)
        hit = scenarios.has_textbook_copy(con, clean)
        if hit:
            out.append(_o("audit_course_no_textbook_copy", "FAIL", f"course={cid}",
                          "no 10-gram overlap", f"hit: {hit!r}"))
            fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_course_no_textbook_copy", "OK", f"{len(rows)} handouts",
                      "no overlap >= 10 words", "all pass"))
    return out


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", s or "")


# ===== R3 =====
def audit_course_scenarios(con: duckdb.DuckDBPyConnection) -> list[dict]:
    courses = loader.load_course_templates()
    out: list[dict] = []
    fail_n = 0
    for c in courses:
        n = scenarios.count_scenarios(c)
        if n < scenarios.MIN_SCENARIOS:
            out.append(_o("audit_course_scenarios", "FAIL", f"course={c['course_id']}",
                          f">={scenarios.MIN_SCENARIOS}", str(n)))
            fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_course_scenarios", "OK", f"{len(courses)} courses", "≥3 scenarios", "all pass"))
    return out


# ===== R4 =====
def audit_homework_alignment(con: duckdb.DuckDBPyConnection) -> list[dict]:
    courses = loader.load_course_templates()
    out: list[dict] = []
    fail_n = 0
    for c in courses:
        htags = c.get("homework_tags") or []
        qs = hw_mod.pick_homework(con, htags)
        qb_ids = [q["qb_id"] for q in qs]
        res = hw_mod.homework_tag_alignment(con, qb_ids, htags)
        if res["n_outside"] > 0:
            out.append(_o("audit_homework_alignment", "FAIL", f"course={c['course_id']}",
                          "0 outside tags", f"{res['n_outside']} outside: {res['outside_examples']}"))
            fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_homework_alignment", "OK", f"{len(courses)} courses",
                      "all hw tags ⊆ course tags", "all pass"))
    return out


# ===== R5 =====
def audit_course_lexical_layer(con: duckdb.DuckDBPyConnection) -> list[dict]:
    courses = loader.load_course_templates()
    out: list[dict] = []
    fail_n = 0
    for c in courses:
        layer = c["layer"]
        words = [it["id"].split(":", 1)[-1] for it in (c.get("core_items") or [])
                 if it.get("kind") == "word"]
        if not words:
            continue
        allowed = allowed_words_for(con, layer)
        unknown = [w for w in words if w.lower() not in allowed]
        if unknown:
            out.append(_o("audit_course_lexical_layer", "FAIL", f"course={c['course_id']}({layer})",
                          "all words ⊆ layer", f"unknown: {unknown[:5]}"))
            fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_course_lexical_layer", "OK", f"{len(courses)} courses",
                      "0 unknown words", "all pass"))
    return out


# ===== R6 =====
def audit_course_textbook_position(con: duckdb.DuckDBPyConnection) -> list[dict]:
    courses = loader.load_course_templates()
    out: list[dict] = []
    fail_n = 0
    for c in courses:
        for it in c.get("core_items") or []:
            if not it.get("position") or it.get("year") not in (1, 2, 3, 99):
                out.append(_o("audit_course_textbook_position", "FAIL", f"course={c['course_id']} item={it.get('id')}",
                              "year(1-3/99) + position", f"year={it.get('year')} position={it.get('position')!r}"))
                fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_course_textbook_position", "OK", f"{len(courses)} courses",
                      "all items have year+position", "all pass"))
    return out


# ===== 听力 =====
def audit_listening_transcript_required(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = con.execute(
        "SELECT qb_id, transcript FROM question_bank WHERE has_audio=true"
    ).fetchall()
    if not rows:
        return [_o("audit_listening_transcript_required", "OK", "(no audio questions)",
                   "n/a", "0 has_audio rows, vacuously pass")]
    bad = [r for r in rows if not (r[1] and len(r[1]) >= 50)]
    if bad:
        return [_o("audit_listening_transcript_required", "FAIL", f"qb_ids={[r[0] for r in bad[:5]]}",
                   "transcript >=50 chars", f"{len(bad)} rows missing/short transcript")]
    return [_o("audit_listening_transcript_required", "OK", f"{len(rows)} audio questions",
               "transcript filled", "all pass")]


# ===== 政治 =====
def audit_no_political(con: duckdb.DuckDBPyConnection) -> list[dict]:
    courses = loader.load_course_templates()
    out: list[dict] = []
    fail_n = 0
    for c in courses:
        for field in ("title", "themes_main", "description"):
            txt = c.get(field) or ""
            hit = scenarios.has_political_word(txt)
            if hit:
                out.append(_o("audit_no_political", "FAIL", f"course={c['course_id']}.{field}",
                              "no political", f"hit: {hit!r}"))
                fail_n += 1
        for t in c.get("themes_aux") or []:
            hit = scenarios.has_political_word(t)
            if hit:
                out.append(_o("audit_no_political", "FAIL", f"course={c['course_id']}.themes_aux",
                              "no political", f"hit: {hit!r}"))
                fail_n += 1
    if fail_n == 0:
        out.append(_o("audit_no_political", "OK", f"{len(courses)} courses",
                      "no political words", "all pass"))
    return out


def _o(kind: str, severity: str, target: str, expected: str, actual: str) -> dict:
    return {"audit_kind": kind, "severity": severity, "target": target,
            "expected": expected, "actual": actual, "delta": None, "note": None}
