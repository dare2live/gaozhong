"""中考真题(2025真题面45条) → question_bank 镶入 + question:节点 (域A; Phase E3 tests_word层).

背景: exam_questions 视图硬过滤 exam_type='高考'(见 03_exam.sql), question_bank 装载
(load_real_questions) 只读该视图 — 中考题从未进过 question_bank/tests_word 体系, 是设计
上的隔离(非疏漏)。此处补一条平行入口, 不改视图/不改 load_real_questions 签名(Rule1
单一计算点: 复用 autotag/insert_question/difficulty, 不重写打标逻辑)。

数据现状(2026-07-07 直接查库核实, 不臆测):
  - 2024年45题(6题型): raw_question 全部 walled(各免费源门控), 但完形填空/阅读理解等
    答案字母/analysis 有(OCR官方答案图产)。stem 不可得 → 不入 question_bank(schema
    NOT NULL 约束, 且'walled(...)'冒充题面违反D0诚实), 只在 exam_questions_all 留存
    供 tests_grammar 等答案驱动分析用(见 grammar.py::link_zhongkao_grammar)。
  - 2025年45题(6题型): raw_question 全部真实(题面驱动获取), 但仅语篇填空(语法填空)
    10题 answer 非空, 其余35题(完形/阅读理解/阅读表达/书面表达) answer 为 NULL(题面
    有, 官方判分答案未获取)。→ 这45题入 question_bank(stem真实, answer 可 NULL,
    schema 允许); answer 缺失诚实体现为 NULL, 不伪造正确答案。

question:节点: canonical.build_all 的 _build_question_rows 只读 exam_questions(高考
视图), 中考题从未建 question: 节点。此处按同一 concept_id 格式(question:{qid}) 独立
补建(同 junior/sections.py 的 Layer3x 时点独立重建 volume/unit 节点先例), 覆盖全部
90题(节点是分析锚点, 不要求 stem 存在, 与 question_bank 的"能否呈现给消费者"要求不同)。
"""
from __future__ import annotations

import json

from backend.services.question_bank.loader import autotag, difficulty, insert_question

_EXAM_TYPE = "中考"


def _question_rows(con) -> list[tuple]:
    """question: 节点(全部90题, 含walled — 节点是锚点非呈现物, 同高中_build_question_rows口径)."""
    rows = con.execute(
        "SELECT question_id, year, province, question_type FROM exam_questions_all "
        "WHERE exam_type = ?", [_EXAM_TYPE],
    ).fetchall()
    return [
        (f"question:{qid}", "question", f"{yr or '?'} {qtype or '?'}",
         json.dumps({"year": yr, "province": prov, "type": qtype, "exam_type": _EXAM_TYPE},
                    ensure_ascii=False))
        for qid, yr, prov, qtype in rows
    ]


def _tests_word_edges(con) -> list[tuple]:
    """题面实词(cefr∩lemmatize token−停用词) → tests_word 边 (Rule1: 复用 links_extra.
    build_tests_word 同款 _lemma_tokens 口径, 不重新定义分词/停用词规则)。只覆盖45条2025
    真题面题(2024全walled无文本信号, 不建边)。"""
    from nltk.stem import WordNetLemmatizer

    from backend.services.exam_vocab import _lemma_tokens
    lemm = WordNetLemmatizer()
    classifiable = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    classifiable |= {r[0] for r in con.execute(
        "SELECT DISTINCT word FROM unit_vocab_intro WHERE unit_number>0").fetchall()}
    rows = []
    for qid, qtext in con.execute(
        "SELECT question_id, raw_question FROM exam_questions_all "
        "WHERE exam_type = ? AND raw_question NOT LIKE '%walled%'", [_EXAM_TYPE],
    ).fetchall():
        if not qtext:
            continue
        for w in _lemma_tokens(qtext, lemm) & classifiable:
            rows.append((f"question:{qid}", f"word:{w}", "tests_word", 1.0, None))
    return rows


def link_tests_word(con) -> dict:
    """qbank.load() 之后调: 45条真题面题 → tests_word 边(question:ZK-% 前缀独立scoped delete,
    不动 links_extra.build_tests_word 已建的高考边)。"""
    con.execute("DELETE FROM edges WHERE relation='tests_word' AND src_id LIKE 'question:ZK-%'")
    edges = _tests_word_edges(con)
    if edges:
        con.executemany(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)", edges)
    return {"中考tests_word边": len(edges)}


def prune_orphan_question_nodes(con) -> dict:
    """须在 qbank.load() + grammar.link_zhongkao_grammar() + link_tests_word() 全部跑完后
    最后调: 删除仍无任何边的 question:ZK-% 节点(D0"孤立critical node=0"门, 同E1 unit:节点
    先例) — 90题里目前只有部分(2025有文本信号的45题 + 2024语篇填空里能精确匹配语法点的题)
    实际进图, 其余诚实地"不建节点"而非建了却孤立(节点是图分析锚点, 无边的节点不是分析锚点,
    是伪完整感)。"""
    orphans = con.execute(
        "SELECT concept_id FROM nodes n WHERE concept_id LIKE 'question:ZK-%' "
        "AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.src_id = n.concept_id "
        "OR e.dst_id = n.concept_id)"
    ).fetchall()
    if orphans:
        con.executemany("DELETE FROM nodes WHERE concept_id = ?", orphans)
    return {"剪除孤立question节点": len(orphans)}


def _mirror_to_qbank(con) -> dict:
    """题面驱动的45条(2025全量, stem真实) → question_bank(Rule1: 复用 autotag/insert_question)."""
    con.execute(
        "DELETE FROM question_tags WHERE qb_id IN "
        "(SELECT qb_id FROM question_bank WHERE origin_ref LIKE 'ZK-%')")
    con.execute("DELETE FROM question_bank WHERE origin_ref LIKE 'ZK-%'")
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    rows = con.execute(
        "SELECT question_id, year, question_type, raw_question, answer, analysis "
        "FROM exam_questions_all WHERE exam_type = ? AND raw_question NOT LIKE '%walled%'",
        [_EXAM_TYPE],
    ).fetchall()
    inserted, tags = 0, 0
    for qid, yr, qtype, stem, ans, anl in rows:
        if not stem:
            continue
        diff = difficulty(stem)
        qb_id = insert_question(con, "real", qid, qtype or "未知", stem, None, ans, anl, diff)
        tags += autotag(con, qb_id, stem, yr, qtype or "未知", cefr, origin_ref=qid,
                         exam_type=_EXAM_TYPE)
        inserted += 1
    return {"中考题入question_bank": inserted, "tags_attached": tags}


def load(con) -> dict:
    """question:节点(90) + question_bank镶入(45真题面题).

    须在 Layer4 load_real_questions 之后调(该函数 DELETE FROM question_bank 全表,
    顺序颠倒会被清空; 同 junior_phrases.py 对 Layer2 高中 phrases blanket DELETE 的
    先例)。"""
    rows = _question_rows(con)
    con.execute("DELETE FROM nodes WHERE concept_id LIKE 'question:ZK-%'")
    if rows:
        con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", rows)
    qbank_result = _mirror_to_qbank(con)
    return {"中考question节点": len(rows), **qbank_result}
