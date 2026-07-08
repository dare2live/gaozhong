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


def check_junior_grammar_occurrences(con: duckdb.DuckDBPyConnection, check) -> None:
    """D0: 初中Grammar section主题 → grammar_occurrences lineage (Phase E4, 2026-07-08).

    用户"仔细研究"后要求做到与高中同等深度的教材单元语法lineage, 而非跳过。46个Grammar
    section标题人工核验映射到71项课标语法点(见 hujiao_grammar_topic_map.yaml), 诚实跳过
    4条71项taxonomy无清晰对应的主题(不强配)。
    """
    print("\n=== (51) 初中Grammar单元lineage (grammar_occurrences, Phase E4) ===")
    n_occ = con.execute("SELECT count(*) FROM grammar_occurrences WHERE version_key='hujiao'").fetchone()[0]
    check("初中grammar_occurrences == 39 (46个Grammar section, 62个主题标题人工核验, "
          "4条71项taxonomy无对应诚实跳过)", n_occ == 39, f"{n_occ}")
    bad_gid = con.execute("""
        SELECT count(*) FROM grammar_occurrences go
        WHERE go.version_key='hujiao' AND NOT EXISTS (
            SELECT 1 FROM nodes n WHERE n.concept_id = 'grammar:jr:' || go.grammar_item_id
        )
    """).fetchone()[0]
    check("全部grammar_item_id能反查回真实grammar:jr:节点(无捏造id)", bad_gid == 0, f"{bad_gid}")
    n_units_covered = con.execute(
        "SELECT count(DISTINCT volume_key || '-' || unit_number) FROM grammar_occurrences "
        "WHERE version_key='hujiao'"
    ).fetchone()[0]
    check("覆盖单元数 == 30 (46单元里16个纯练习/复习单元Grammar板块无可提取主题标题, 诚实反映"
          "教材真实分布不强配)", n_units_covered == 30, f"{n_units_covered}")
