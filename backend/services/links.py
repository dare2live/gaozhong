"""Edge builder — 把 N:M 关系从 Layer 2 主表算出来灌进 edges 表.

每个 build_* 函数 = 一类 relation, 幂等 (先 DELETE 该 relation 再 INSERT).
新增 relation 只加新函数, 不改主表.

调用者: scripts/init_db.py canonical.build_all 之后.
"""
from __future__ import annotations

import json
from typing import Iterable

import duckdb


def build_all(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts: dict[str, int] = {}
    counts["cefr_level"] = build_cefr_level(con)
    counts["cat_of"] = build_grammar_parent(con)
    counts["city_uses"] = build_city_uses(con)
    counts["allowed_in_ln"] = build_allowed_in_ln(con)
    counts["vol_in_ver"] = build_volume_publisher(con)
    counts["in_year"] = build_question_in_year(con)
    counts["question_type"] = build_question_type(con)
    counts["in_volume"] = build_unit_in_volume(con)
    # 教材层 (sections/vocab_intro/phrases) STEP 2 第二刀输出后再补 build_*
    # 真题→考点 (tests_word/tests_grammar/tests_theme) STEP 3 LLM 抽出后再补
    return counts


def _replace_relation(con: duckdb.DuckDBPyConnection, relation: str, rows: Iterable[tuple]) -> int:
    """rows: (src_id, dst_id, weight, evidence_json_or_None)"""
    con.execute("DELETE FROM edges WHERE relation = ?", [relation])
    rs = [(src, dst, relation, w, ev) for (src, dst, w, ev) in rows]
    if not rs:
        return 0
    con.executemany(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
        rs,
    )
    return len(rs)


def build_cefr_level(con: duckdb.DuckDBPyConnection) -> int:
    rows: list[tuple] = []
    rows.extend((f"word:{w}", f"cefr_level:{lv}", 1.0, None)
                for w, lv in con.execute("SELECT word, cefr_level FROM cefr_vocab").fetchall())
    rows.extend((f"grammar:{g}", f"cefr_level:{lv}", 1.0, None)
                for g, lv in con.execute("SELECT grammar_item_id, cefr_level FROM grammar_items").fetchall())
    return _replace_relation(con, "cefr_level", rows)


def build_question_in_year(con: duckdb.DuckDBPyConnection) -> int:
    rows = [(f"question:{qid}", f"exam_year:{yr}", 1.0, None)
            for qid, yr in con.execute(
                "SELECT question_id, year FROM exam_questions WHERE year IS NOT NULL"
            ).fetchall()]
    return _replace_relation(con, "in_year", rows)


def build_question_type(con: duckdb.DuckDBPyConnection) -> int:
    """question → label-node 'qtype:<name>'. Auto-create label nodes if missing."""
    types = [t for (t,) in con.execute(
        "SELECT DISTINCT question_type FROM exam_questions WHERE question_type IS NOT NULL"
    ).fetchall()]
    # ensure label nodes exist (special "qtype:<x>" nodes — registered here on demand)
    if types:
        con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, 'qtype', ?, NULL)",
                        [(f"qtype:{t}", t) for t in types])
    rows = [(f"question:{qid}", f"qtype:{t}", 1.0, None)
            for qid, t in con.execute(
                "SELECT question_id, question_type FROM exam_questions WHERE question_type IS NOT NULL"
            ).fetchall()]
    return _replace_relation(con, "question_type", rows)


def build_grammar_parent(con: duckdb.DuckDBPyConnection) -> int:
    rows = [
        (f"grammar:{gid}", f"grammar:{pid}", 1.0, None)
        for gid, pid in con.execute(
            "SELECT grammar_item_id, parent_id FROM grammar_items WHERE parent_id IS NOT NULL"
        ).fetchall()
    ]
    return _replace_relation(con, "cat_of", rows)


def build_city_uses(con: duckdb.DuckDBPyConnection) -> int:
    rows = [
        (f"city:{city}", f"publisher:{pub}", 1.0,
         json.dumps({"source": src}, ensure_ascii=False))
        for city, pub, src in con.execute(
            "SELECT city, publisher_short, source FROM liaoning_city_textbook_choice"
        ).fetchall()
    ]
    return _replace_relation(con, "city_uses", rows)


def build_allowed_in_ln(con: duckdb.DuckDBPyConnection) -> int:
    """publisher → subject:英语 (恒定 8 条, 现在只有 subject=英语 一类)."""
    # 8 个 publisher 抽 short — 复用 canonical 里的映射
    pub_short_map = {
        "外语教学与研究出版社": "外研版",
        "人民教育出版社": "人教版",
        "北京师范大学出版社": "北师大版",
        "译林出版社": "译林版",
    }
    rows = []
    for (full,) in con.execute("SELECT DISTINCT publisher FROM liaoning_allowed_publishers").fetchall():
        short = pub_short_map.get(full, full.split("/")[0].split("、")[0])
        rows.append((f"publisher:{short}", "subject:英语", 1.0,
                     json.dumps({"full": full}, ensure_ascii=False)))
    return _replace_relation(con, "allowed_in_ln", rows)


def build_volume_publisher(con: duckdb.DuckDBPyConnection) -> int:
    """volume → publisher (短名). version_key → publisher_short 简单映射."""
    ver_to_short = {"waiyan": "外研版", "renjiao": "人教版"}
    rows = []
    for ver, vol in con.execute("SELECT version_key, volume_key FROM textbooks").fetchall():
        short = ver_to_short.get(ver, ver)
        rows.append((f"volume:{ver}/{vol}", f"publisher:{short}", 1.0, None))
    return _replace_relation(con, "vol_in_ver", rows)


def build_unit_in_volume(con: duckdb.DuckDBPyConnection) -> int:
    """unit → volume. unit concept_id = unit:<ver>/<vol>/U<n>; ensure unit nodes exist first."""
    units = con.execute("""
        SELECT version_key, volume_key, unit_number, title_en, page_start, page_end
        FROM units ORDER BY version_key, volume_key, unit_number
    """).fetchall()
    if not units:
        return 0
    # ensure unit nodes
    node_rows = []
    for ver, vol, un, title, ps, pe in units:
        cid = f"unit:{ver}/{vol}/U{un}"
        attrs = '{"page_start": %d, "page_end": %d}' % (ps or 0, pe or 0)
        node_rows.append((cid, "unit", title or f"Unit {un}", attrs))
    con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", node_rows)
    # edges
    rows = [
        (f"unit:{ver}/{vol}/U{un}", f"volume:{ver}/{vol}", 1.0, None)
        for ver, vol, un, *_ in units
    ]
    return _replace_relation(con, "in_volume", rows)
