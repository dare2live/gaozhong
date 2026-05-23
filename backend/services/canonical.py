"""Canonical concept builder — 把 Layer 2 主表行折成统一 nodes 行.

输入: cefr_vocab / grammar_items / theme_contexts / textbooks / units (后续) /
      liaoning_allowed_publishers / liaoning_city_textbook_choice / exam_questions
输出: nodes 表 (concept_id, node_type, label, attrs_json)

调用者: scripts/init_db.py (装载完主表后调一次).
        日后增量数据后, links/build 之前需重跑.
"""
from __future__ import annotations

import json
from typing import Iterable

import duckdb


CEFR_LEVEL_VALUES = ("义教", "必修", "选必", "选修")


def build_all(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Replace-all build (MVP 不做增量). 返回各 node_type 的行数."""
    con.execute("DELETE FROM nodes")
    counts: dict[str, int] = {}

    # 1) cefr_level 节点 (常量 4 个)
    rows = [(f"cefr_level:{lv}", "cefr_level", lv, None) for lv in CEFR_LEVEL_VALUES]
    _bulk_insert(con, rows)
    counts["cefr_level"] = len(rows)

    # 2) word
    rows = [
        (f"word:{w[0]}", "word", w[0], json.dumps({"cefr_level": w[1], "raw_suffix": w[2]}, ensure_ascii=False))
        for w in con.execute("SELECT word, cefr_level, raw_suffix FROM cefr_vocab").fetchall()
    ]
    _bulk_insert(con, rows)
    counts["word"] = len(rows)

    # 3) grammar
    rows = [
        (f"grammar:{r[0]}", "grammar", r[1],
         json.dumps({"depth": r[2], "parent_id": r[3], "category": r[4], "cefr_level": r[5]}, ensure_ascii=False))
        for r in con.execute(
            "SELECT grammar_item_id, label, depth, parent_id, category, cefr_level FROM grammar_items"
        ).fetchall()
    ]
    _bulk_insert(con, rows)
    counts["grammar"] = len(rows)

    # 4) theme
    rows = [
        (f"theme:{r[0]}", "theme", r[0], json.dumps({"level1": r[1], "level2": r[2]}, ensure_ascii=False))
        for r in con.execute("SELECT theme_context_id, level1, level2 FROM theme_contexts").fetchall()
    ]
    _bulk_insert(con, rows)
    counts["theme"] = len(rows)

    # 5) publisher (allowed in Liaoning) — short label normalize
    pub_short_map = {
        "外语教学与研究出版社": "外研版",
        "人民教育出版社": "人教版",
        "北京师范大学出版社": "北师大版",
        "译林出版社": "译林版",
    }
    rows = []
    for (pub,) in con.execute("SELECT DISTINCT publisher FROM liaoning_allowed_publishers").fetchall():
        short = pub_short_map.get(pub, pub.split("/")[0].split("、")[0])
        rows.append((f"publisher:{short}", "publisher", short, json.dumps({"full": pub}, ensure_ascii=False)))
    _bulk_insert(con, rows)
    counts["publisher"] = len(rows)

    # 6) city
    rows = [
        (f"city:{c}", "city", c, None)
        for (c,) in con.execute("SELECT DISTINCT city FROM liaoning_city_textbook_choice").fetchall()
    ]
    _bulk_insert(con, rows)
    counts["city"] = len(rows)

    # 7) volume (= textbooks 行)
    rows = [
        (f"volume:{ver}/{vol}", "volume", f"{lbl} {vol}",
         json.dumps({"version": ver, "volume_key": vol, "pages": pages}, ensure_ascii=False))
        for ver, vol, lbl, pages in con.execute(
            "SELECT version_key, volume_key, publisher_label, pdf_pages FROM textbooks"
        ).fetchall()
    ]
    _bulk_insert(con, rows)
    counts["volume"] = len(rows)

    # 8) exam_year (从 exam_questions year distinct)
    try:
        years = con.execute("SELECT DISTINCT year FROM exam_questions WHERE year IS NOT NULL").fetchall()
        rows = [(f"exam_year:{y[0]}", "exam_year", str(y[0]), None) for y in years]
        _bulk_insert(con, rows)
        counts["exam_year"] = len(rows)
    except duckdb.CatalogException:
        counts["exam_year"] = 0

    # 9) question
    try:
        rows = [
            (f"question:{qid}", "question",
             f"{yr or '?'} {qtype or '?'}",
             json.dumps({"year": yr, "province": prov, "type": qtype}, ensure_ascii=False))
            for qid, yr, prov, qtype in con.execute(
                "SELECT question_id, year, province, question_type FROM exam_questions"
            ).fetchall()
        ]
        _bulk_insert(con, rows)
        counts["question"] = len(rows)
    except duckdb.CatalogException:
        counts["question"] = 0

    return counts


def _bulk_insert(con: duckdb.DuckDBPyConnection, rows: Iterable[tuple]) -> None:
    rows = list(rows)
    if not rows:
        return
    con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", rows)
