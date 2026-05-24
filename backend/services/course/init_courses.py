"""yaml → DB 灌 — 给 init_db.py 调用.

灌:
  courses          (from course_templates.yaml)
  course_materials (build_materials_for_course 生成)
"""
from __future__ import annotations

import json

import duckdb

from . import loader, materials


def run(con: duckdb.DuckDBPyConnection) -> dict:
    courses = loader.load_course_templates()
    con.execute("DELETE FROM course_materials")
    con.execute("DELETE FROM courses")

    n_courses = 0
    n_materials = 0
    for c in courses:
        con.execute(
            "INSERT INTO courses (course_id, layer, title, block_kind, block_order, "
            "duration_min, listening_required, description, themes_main, themes_aux) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                c["course_id"], c["layer"], c.get("title", ""), c["block_kind"],
                c["block_order"], c.get("duration_min", 120),
                bool(c.get("listening_required", False)),
                c.get("description", ""),
                c.get("themes_main", ""),
                json.dumps(c.get("themes_aux") or [], ensure_ascii=False),
            ],
        )
        n_courses += 1

        for m in materials.build_materials_for_course(con, c):
            con.execute(
                "INSERT INTO course_materials "
                "(course_id, seq, kind, ref_id, year_level, textbook_position, source, reason) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [m["course_id"], m["seq"], m["kind"], m["ref_id"],
                 m["year_level"], m["textbook_position"], m["source"], m["reason"]],
            )
            n_materials += 1

    return {"courses": n_courses, "materials": n_materials}
