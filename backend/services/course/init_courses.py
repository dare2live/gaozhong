"""yaml → DB 灌 — 给 init_db.py 调用.

灌:
  courses          (from course_templates.yaml)
  course_materials (build_materials_for_course 生成)
  course_handouts  (handout.render_handout 持久化, P1.2 R2 audit 前提)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from . import handout, lexicon_filter, loader, materials


COURSE_HANDOUTS_DDL = """
CREATE TABLE IF NOT EXISTS course_handouts (
    course_id     INTEGER PRIMARY KEY,
    md            VARCHAR NOT NULL,
    md_chars      INTEGER NOT NULL,
    generated_at  VARCHAR NOT NULL
);
"""


def run(con: duckdb.DuckDBPyConnection) -> dict:
    # P1.2: idempotent DDL (schema.sql 主表已有, 此表为 audit 真扫支持新增)
    con.execute(COURSE_HANDOUTS_DDL)
    courses = loader.load_course_templates()
    con.execute("DELETE FROM course_handouts")
    con.execute("DELETE FROM course_materials")
    con.execute("DELETE FROM courses")

    n_courses = 0
    n_materials = 0
    n_handouts = 0
    now = datetime.now(timezone.utc).isoformat()
    for c in courses:
        _insert_course(con, c)
        n_courses += 1
        for m in materials.build_materials_for_course(con, c):
            _insert_material(con, m)
            n_materials += 1
        # P1.2 持久化讲义 md → 让 audit_course_no_textbook_copy 真扫
        md = handout.render_handout(con, c)["md"]
        # R5 程序级超纲拦截: enriched content 必须通过词汇校验
        beyond = lexicon_filter.validate_content_vocab(con, md, c["layer"])
        if beyond:
            print(f"  ⚠️ #{c['course_id']} [{c['layer']}] R5 超纲词 {len(beyond)}: {beyond[:10]}")
        con.execute(
            "INSERT INTO course_handouts (course_id, md, md_chars, generated_at) "
            "VALUES (?, ?, ?, ?)",
            [c["course_id"], md, len(md), now],
        )
        n_handouts += 1

    return {"courses": n_courses, "materials": n_materials, "handouts": n_handouts}


def _insert_course(con, c: dict) -> None:
    con.execute(
        "INSERT INTO courses (course_id, layer, title, block_kind, block_order, "
        "duration_min, listening_required, description, themes_main, themes_aux) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [c["course_id"], c["layer"], c.get("title", ""), c["block_kind"],
         c["block_order"], c.get("duration_min", 120),
         bool(c.get("listening_required", False)),
         c.get("description", ""),
         c.get("themes_main", ""),
         json.dumps(c.get("themes_aux") or [], ensure_ascii=False)],
    )


def _insert_material(con, m: dict) -> None:
    con.execute(
        "INSERT INTO course_materials "
        "(course_id, seq, kind, ref_id, year_level, textbook_position, source, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [m["course_id"], m["seq"], m["kind"], m["ref_id"],
         m["year_level"], m["textbook_position"], m["source"], m["reason"]],
    )
