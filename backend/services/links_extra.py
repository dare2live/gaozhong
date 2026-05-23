"""Extra link builders (STEP "数据补全"): tests_word / tests_grammar / theme_of_unit.

为避免 backend/services/links.py 超 250L god-module, 拆到本文件;
init_db 在 links.build_all 后调 links_extra.build_all_extra.
"""
from __future__ import annotations

import json
import re

import duckdb

from .audit.grammar_4q import TERM_TO_LABEL_KEYWORD

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")

# Unit title 关键词 → 主题语境. 简短 keyword 子串匹配 (broad覆盖).
UNIT_THEME_HINTS = {
    "TEENAGE": "人与自我/生活与学习", "LIFE": "人与自我/生活与学习",
    "LEARNING": "人与自我/生活与学习", "SCHOOL": "人与自我/生活与学习",
    "STUDY": "人与自我/生活与学习", "LANGUAGE": "人与社会/历史、社会与文化",
    "TRAVEL": "人与社会/历史、社会与文化", "JOURNEY": "人与社会/历史、社会与文化",
    "SPORT": "人与自我/做人与做事", "FITNESS": "人与自我/做人与做事",
    "ACHIEVEMENT": "人与自我/做人与做事", "MORALS": "人与自我/做人与做事",
    "VALUE": "人与自我/做人与做事", "VIRTUE": "人与自我/做人与做事",
    "CAREER": "人与自我/做人与做事", "WORK": "人与自我/做人与做事",
    "JOB": "人与自我/做人与做事", "PURSUIT": "人与自我/做人与做事",
    "BODY": "人与自我/生活与学习", "HEALTHY": "人与自我/生活与学习",
    "HEALTH": "人与自我/生活与学习", "FIRST AID": "人与自我/生活与学习",
    "FOOD": "人与自我/生活与学习",
    "DISASTER": "人与自然/灾害防范",
    "WILDLIFE": "人与自然/自然生态", "ANIMAL": "人与自然/自然生态",
    "NATURE": "人与自然/自然生态", "PLANT": "人与自然/自然生态",
    "ENVIRONMENT": "人与自然/环境保护", "PROTECTION": "人与自然/环境保护",
    "SPACE": "人与自然/宇宙探索", "SEA": "人与自然/宇宙探索",
    "EXPLORATION": "人与自然/宇宙探索", "FUTURE": "人与自然/宇宙探索",
    "PARK": "人与自然/自然生态", "LAND": "人与自然/自然生态",
    "CULTURAL": "人与社会/历史、社会与文化", "CULTURE": "人与社会/历史、社会与文化",
    "HISTORY": "人与社会/历史、社会与文化", "HERITAGE": "人与社会/历史、社会与文化",
    "TRADITION": "人与社会/历史、社会与文化", "FESTIVAL": "人与社会/历史、社会与文化",
    "DIVERSE": "人与社会/历史、社会与文化", "BRIDGING": "人与社会/历史、社会与文化",
    "ATTRACTION": "人与社会/历史、社会与文化",
    "INTERNET": "人与社会/科学与技术", "TECHNOLOGY": "人与社会/科学与技术",
    "SCIENCE": "人与社会/科学与技术", "SCIENTIST": "人与社会/科学与技术",
    "ART": "人与社会/文学、艺术与体育", "POEM": "人与社会/文学、艺术与体育",
    "FICTION": "人与社会/文学、艺术与体育",
    "SHARING": "人与社会/社会服务与人际沟通",
    "MONEY": "人与社会/历史、社会与文化",
    "WELCOME": "人与自我/生活与学习",   # Welcome Unit fallback
}


def _replace(con: duckdb.DuckDBPyConnection, relation: str, rows: list) -> int:
    con.execute("DELETE FROM edges WHERE relation = ?", [relation])
    if not rows:
        return 0
    con.executemany(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
        "VALUES (?, ?, ?, ?, ?)",
        [(s, d, relation, w, ev) for s, d, w, ev in rows],
    )
    return len(rows)


def build_tests_word(con: duckdb.DuckDBPyConnection) -> int:
    """question → word: 题面 token 在 cefr_vocab 中即建 edge (评估考点)."""
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    rows: list[tuple] = []
    for qid, qtext in con.execute(
        "SELECT question_id, raw_question FROM exam_questions"
    ).fetchall():
        if not qtext:
            continue
        toks = {t.lower() for t in _TOKEN_RE.findall(qtext)} & cefr
        for w in toks:
            rows.append((f"question:{qid}", f"word:{w}", 1.0, None))
    return _replace(con, "tests_word", rows)


def build_tests_grammar(con: duckdb.DuckDBPyConnection) -> int:
    """question → grammar: 题面 / analysis 含中文语法术语即建 edge."""
    items = con.execute(
        "SELECT grammar_item_id, label FROM grammar_items"
    ).fetchall()
    rows: list[tuple] = []
    for qid, qtext, anl in con.execute(
        "SELECT question_id, raw_question, analysis FROM exam_questions"
    ).fetchall():
        blob = (qtext or "") + " " + (anl or "")
        for term, kw in TERM_TO_LABEL_KEYWORD.items():
            if term in blob:
                for gid, label in items:
                    if kw in (label or ""):
                        rows.append((f"question:{qid}", f"grammar:{gid}",
                                     1.0, json.dumps({"term": term},
                                                      ensure_ascii=False)))
    # dedup (src, dst)
    dedup = {}
    for r in rows:
        dedup[(r[0], r[1])] = r
    return _replace(con, "tests_grammar", list(dedup.values()))


def build_theme_of_unit(con: duckdb.DuckDBPyConnection) -> int:
    """unit → theme: hardcoded UNIT_THEME_HINTS + title_en substring match."""
    units = con.execute(
        "SELECT version_key, volume_key, unit_number, title_en FROM units"
    ).fetchall()
    rows: list[tuple] = []
    for ver, vol, un, title in units:
        title_upper = (title or "").upper()
        for keyword, theme_id in UNIT_THEME_HINTS.items():
            if keyword in title_upper:
                rows.append((
                    f"unit:{ver}/{vol}/U{un}", f"theme:{theme_id}", 1.0,
                    json.dumps({"matched_keyword": keyword,
                                 "title": title}, ensure_ascii=False),
                ))
                break   # one theme per unit
    return _replace(con, "theme_of_unit", rows)


def build_introduces_phrase(con: duckdb.DuckDBPyConnection) -> int:
    """unit → phrase. Auto-create phrase nodes (concept_id = 'phrase:<sha8>')."""
    import hashlib
    rows_p = con.execute(
        "SELECT version_key, volume_key, unit_number, canonical, phrase_type, evidence "
        "FROM phrases"
    ).fetchall()
    node_rows: list[tuple] = []
    edge_rows: list[tuple] = []
    seen_nodes: set[str] = set()
    for ver, vol, un, canon, ptype, ev in rows_p:
        sha = hashlib.sha1(f"{canon}/{ptype}".encode("utf-8")).hexdigest()[:8]
        cid = f"phrase:{sha}"
        if cid not in seen_nodes:
            seen_nodes.add(cid)
            attrs = ('{"canonical": "%s", "type": "%s"}'
                     % (canon.replace('"', '\\"'), ptype))
            node_rows.append((cid, "phrase", canon, attrs))
        ev_short = (ev or "")[:200].replace('"', "'")
        edge_rows.append((
            f"unit:{ver}/{vol}/U{un}", cid, 1.0,
            '{"evidence": "%s"}' % ev_short,
        ))
    if node_rows:
        con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", node_rows)
    return _replace(con, "introduces_phrase", edge_rows)


def build_all_extra(con: duckdb.DuckDBPyConnection) -> dict:
    return {
        "tests_word": build_tests_word(con),
        "tests_grammar": build_tests_grammar(con),
        "theme_of_unit": build_theme_of_unit(con),
        "introduces_phrase": build_introduces_phrase(con),
    }
