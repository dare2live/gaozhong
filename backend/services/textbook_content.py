"""教材单元内容直出 DB (北极星 基础库; 用户: 教材已入库, 上半知识点 + 下半正文, 不依赖 PDF).

单一计算点: 一个单元聚合 (全读已落库, 铁律1) —
  知识点: 单词(unit_vocab_intro) / 短语(phrases verb_phrase) / 句型(phrases sentence_pattern) /
          语法(grammar_occurrences + grammar_items 标签 + 例句) / 表达方式(phrases function_expression)
  正文: section_text.raw_text (join sections 取段标题/类型, 按 seq)
数据真值, 无则空 (不假填)。
"""
from __future__ import annotations

import duckdb

from backend.api.db import rows_to_dicts


def _vocab(con, v, vol, u):
    return rows_to_dicts(con.execute(
        "SELECT word, pos, zh_def, in_curriculum FROM unit_vocab_intro "
        "WHERE version_key=? AND volume_key=? AND unit_number=? ORDER BY word", [v, vol, u]))


def _phrases(con, v, vol, u):
    """短语/句型/表达方式 (phrases 按 phrase_type 分三组)."""
    rows = con.execute(
        "SELECT canonical, phrase_type FROM phrases "
        "WHERE version_key=? AND volume_key=? AND unit_number=? ORDER BY phrase_type, canonical", [v, vol, u]).fetchall()
    out = {"collocation": [], "sentence_pattern": [], "expression": []}
    for canonical, ptype in rows:
        if ptype == "verb_phrase":
            out["collocation"].append(canonical)
        elif ptype == "sentence_pattern":
            out["sentence_pattern"].append(canonical)
        elif (ptype or "").startswith("function_expression"):
            out["expression"].append({"text": canonical, "intent": (ptype.split(":", 1)[1] if ":" in ptype else "")})
    return out


def _grammar(con, v, vol, u):
    """语法点 (grammar_occurrences join grammar_items 取人话标签 + 例句)."""
    return rows_to_dicts(con.execute(
        "SELECT gi.label AS label, go.example_sentence AS example "
        "FROM grammar_occurrences go LEFT JOIN grammar_items gi ON gi.grammar_item_id = go.grammar_item_id "
        "WHERE go.version_key=? AND go.volume_key=? AND go.unit_number=? ORDER BY go.occ_id", [v, vol, u]))


def _passages(con, v, vol, u):
    """教材正文: section_text.raw_text join sections 取标题/类型, 按 seq."""
    return rows_to_dicts(con.execute(
        "SELECT st.seq AS seq, s.kind AS kind, s.title AS title, st.raw_text AS text, st.n_chars AS n_chars, "
        "s.is_narrative AS is_narrative, s.is_applied AS is_applied, s.is_listening AS is_listening "
        "FROM section_text st "
        "LEFT JOIN sections s ON s.version_key=st.version_key AND s.volume_key=st.volume_key "
        "  AND s.unit_number=st.unit_number AND s.seq=st.seq "
        "WHERE st.version_key=? AND st.volume_key=? AND st.unit_number=? ORDER BY st.seq", [v, vol, u]))


def unit_content(con: duckdb.DuckDBPyConnection, version: str, volume: str, unit: int) -> dict:
    """单元内容: 上半知识点(单词/短语/句型/语法/表达) + 下半教材正文 (全 DB, 不依赖 PDF)."""
    ph = _phrases(con, version, volume, unit)
    vocab = _vocab(con, version, volume, unit)
    grammar = _grammar(con, version, volume, unit)
    passages = _passages(con, version, volume, unit)
    return {
        "version_key": version, "volume_key": volume, "unit_number": unit,
        "knowledge": {
            "vocab": vocab, "vocab_n": len(vocab),
            "collocation": ph["collocation"], "sentence_pattern": ph["sentence_pattern"],
            "expression": ph["expression"], "grammar": grammar,
        },
        "passages": passages, "passages_n": len(passages),
        "note": "教材已解析入库, 知识点(词/短语/句型/语法/表达)+正文 均直出 DB (unit_vocab_intro/phrases/grammar_occurrences/section_text), 不依赖 PDF。",
    }
