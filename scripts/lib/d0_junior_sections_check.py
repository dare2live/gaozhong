"""D0: 初中教材 units/sections/section_text 地基 (Phase E1, 2026-07-07)。

用户拍板"全深度复刻高中方法论到初中", E1第一步: 沪教牛津6册课文结构化(此前sections=0行)。
"""
from __future__ import annotations

import duckdb


def check_junior_sections(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (47) 初中教材课文结构化 (units/sections/section_text, Phase E1) ===")
    n_units = con.execute("SELECT count(*) FROM units WHERE version_key='hujiao'").fetchone()[0]
    n_vol = con.execute(
        "SELECT count(DISTINCT volume_key) FROM units WHERE version_key='hujiao'"
    ).fetchone()[0]
    n_sections = con.execute("SELECT count(*) FROM sections WHERE version_key='hujiao'").fetchone()[0]
    n_text = con.execute("SELECT count(*) FROM section_text WHERE version_key='hujiao'").fetchone()[0]
    n_kinds = con.execute(
        "SELECT count(DISTINCT kind) FROM sections WHERE version_key='hujiao'"
    ).fetchone()[0]
    n_bad_range = con.execute(
        "SELECT count(*) FROM sections WHERE version_key='hujiao' AND page_start > page_end"
    ).fetchone()[0]
    n_orphan_text = con.execute("""
        SELECT count(*) FROM section_text st
        WHERE st.version_key='hujiao' AND NOT EXISTS (
            SELECT 1 FROM sections s WHERE s.version_key=st.version_key
            AND s.volume_key=st.volume_key AND s.unit_number=st.unit_number AND s.seq=st.seq
        )
    """).fetchone()[0]

    check("初中教材(hujiao) 6册全覆盖", n_vol == 6, f"{n_vol}")
    check("units == 46 (5册×8单元+9b 6单元, 9b经TOC核实真实只有3module/6unit非bug)",
          n_units == 46, f"{n_units}")
    check("sections == 416 (units/sections正确性已实测验证, 见commit)",
          n_sections == 416, f"{n_sections}")
    check("section_text 行数 == sections 行数 (1:1覆盖无缺失)",
          n_text == n_sections, f"{n_text} vs {n_sections}")
    check("section kind 种类 >= 8 (覆盖Reading/Listening/Grammar/Writing/Speaking/Vocabulary/"
          "Comprehension/MorePractice等, 无退化成单一类目)", n_kinds >= 8, f"{n_kinds}")
    check("无 page_start > page_end 的非法区间", n_bad_range == 0, f"{n_bad_range}")
    check("section_text 无孤儿行(每行必有对应 sections 行)", n_orphan_text == 0, f"{n_orphan_text}")
