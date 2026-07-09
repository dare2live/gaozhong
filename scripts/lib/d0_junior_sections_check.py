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


def check_junior_vocab_unit(con: duckdb.DuckDBPyConnection, check) -> None:
    """D0: 初中词汇单元lineage (unit_vocab_intro, Phase E4, 2026-07-08).

    真相源: 6册卷末"Words and expressions in each unit"附录(与已用的"alphabetical order"
    版是同一批词的两种排布, 逐条核实"Unit N"标题后的词条属该单元, 非估算)。高中侧的塌缩/
    跨单元重复地板(scripts/data_accuracy_check.py _check_2_vocab)已按version_key排除
    hujiao(该口径专为renjiao/waiyan"单一区段抽取"回归而设, hujiao真实分布[部分单元15-19词/
    31词跨单元重现]是逐条核实过的教材事实非提取误差)。
    """
    print("\n=== (52) 初中词汇单元lineage (unit_vocab_intro, Phase E4) ===")
    n_uvi = con.execute("SELECT count(*) FROM unit_vocab_intro WHERE version_key='hujiao'").fetchone()[0]
    check("初中unit_vocab_intro == 947 (6册卷末in-each-unit附录, 逐条Unit N标题核验归属)",
          n_uvi == 947, f"{n_uvi}")
    n_vol = con.execute(
        "SELECT count(DISTINCT volume_key) FROM unit_vocab_intro WHERE version_key='hujiao'"
    ).fetchone()[0]
    check("6册全覆盖", n_vol == 6, f"{n_vol}")
    n_no_gloss = con.execute(
        "SELECT count(*) FROM unit_vocab_intro WHERE version_key='hujiao' AND zh_def IS NULL"
    ).fetchone()[0]
    check("无法匹配hujiao_vocab.jsonl释义的词 <= 5 (诚实计数, 不强配)", n_no_gloss <= 5, f"{n_no_gloss}")
    n_intro_edge = con.execute(
        "SELECT count(*) FROM edges WHERE relation='introduces_word' AND src_id LIKE 'unit:hujiao/%'"
    ).fetchone()[0]
    check("introduces_word边(初中) == unit_vocab_intro行数 (1:1覆盖, build_introduces_word"
          "已重跑纳入初中)", n_intro_edge == n_uvi, f"{n_intro_edge} vs {n_uvi}")


def check_junior_syllabus(con: duckdb.DuckDBPyConnection, check) -> None:
    """D0: 初中课程生成器 junior_syllabus (Phase E4, 2026-07-08).

    组织轴=46真实教材单元(非命题频次, 用户明确纠正不套用高中syllabus.py那套), 默认
    n_lessons=None不压缩(1单元1节); 三轴(语法/词汇/短语)lineage逐单元整合, 只读聚合
    已有边(grammar_occurrences/unit_vocab_intro/phrases/deepens/tests_grammar/
    tests_word), 不重算(Rule1)。
    """
    print("\n=== (53) 初中课程生成器 junior_syllabus (Phase E4) ===")
    from backend.services.course.junior_knowledge import junior_syllabus
    r = junior_syllabus(con)
    check("默认不压缩: n_lessons == n_units_total == 46",
          r["n_lessons"] == 46 and r["n_units_total"] == 46,
          f"{r['n_lessons']} / {r['n_units_total']}")
    lessons = r["lessons"]
    check("每节课都有volume_key/unit_number(真实单元锚定, 非虚构)",
          all("volume_key" in l and "unit_number" in l for l in lessons),
          f"{sum(1 for l in lessons if 'volume_key' in l)}/{len(lessons)}")
    n_with_grammar = sum(1 for l in lessons if l.get("grammar"))
    check("覆盖语法lineage的课节数 == 30 (同check_junior_grammar_occurrences的30单元)",
          n_with_grammar == 30, f"{n_with_grammar}")
    total_vocab = sum(l["vocab"]["n_total"] for l in lessons)
    check("全部课节词汇总数 == 947 (同unit_vocab_intro总行数, 无遗漏无重算)",
          total_vocab == 947, f"{total_vocab}")
    check("content 字段全为 None (Phase D 内容生成需就绪门, 本函数只搭框架)",
          r.get("content") is None, f"{r.get('content')}")


def check_junior_unit_content(con: duckdb.DuckDBPyConnection, check) -> None:
    """D0: 初中单元内容直出 junior_knowledge.unit_content (基础库 jr_jichu 页, 2026-07-08).

    /api/course/junior/unit_content 薄壳消费; 校验output结构闭合(knowledge三轴+passages)
    与已被 check_junior_grammar_occurrences/check_junior_vocab_unit/check_junior_sections
    验证过的底层边/表数据一致(不重复验底层正确性, 只验组合函数的输出结构不丢字段/不重算)。
    """
    print("\n=== (54) 初中单元内容直出 unit_content (基础库) ===")
    from backend.services.course.junior_knowledge import unit_content
    r = unit_content(con, "7a", 1)
    check("顶层结构闭合: version_key/volume_key/unit_number/title_en/knowledge/passages",
          all(k in r for k in ("version_key", "volume_key", "unit_number", "title_en", "knowledge", "passages")),
          f"{sorted(r.keys())}")
    check("version_key == hujiao (初中单版本锚定)", r["version_key"] == "hujiao", f"{r['version_key']}")
    k = r["knowledge"]
    check("knowledge 三轴齐全: grammar/vocab/phrases", all(a in k for a in ("grammar", "vocab", "phrases")), f"{sorted(k.keys())}")
    check("vocab_n 与 vocab 列表长度一致 (无重算, 直接count)", k["vocab_n"] == len(k["vocab"]), f"{k['vocab_n']} vs {len(k['vocab'])}")
    check("passages_n 与 passages 列表长度一致", r["passages_n"] == len(r["passages"]), f"{r['passages_n']} vs {len(r['passages'])}")
    # 全单元遍历: knowledge三轴总数与底层表逐单元求和一致 (对账, 防组合函数漏单元/重复单元)
    units = con.execute(
        "SELECT volume_key, unit_number, title_en FROM units WHERE version_key='hujiao'"
    ).fetchall()
    total_vocab = sum(unit_content(con, v, u)["knowledge"]["vocab_n"] for v, u, _ in units)
    check("遍历46单元vocab_n总和 == 947 (同check_junior_vocab_unit已验证的unit_vocab_intro总行数)",
          total_vocab == 947, f"{total_vocab}")
    # 2026-07-09覆盖率审计后新增: 词性分布(backend/services/vocab_pos.py, Rule5高中/初中共享helper)
    pd = k.get("vocab_pos_distribution")
    check("vocab_pos_distribution 结构闭合(by_pos/n_tagged/n_untagged/caveat)",
          isinstance(pd, dict) and all(kk in pd for kk in ("by_pos", "n_tagged", "n_untagged", "caveat")),
          f"{sorted(pd.keys()) if isinstance(pd, dict) else pd}")
