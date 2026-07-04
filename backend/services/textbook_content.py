"""教材单元内容直出 DB (北极星 基础库; 用户: 教材已入库, 上半知识点 + 下半正文, 不依赖 PDF).

单一计算点: 一个单元聚合 (全读已落库, 铁律1) —
  知识点: 单词(unit_vocab_intro, 挂 exam_vocabulary 真实辽宁命中次数) /
          短语(phrases verb_phrase) / 句型(phrases sentence_pattern) /
          语法(grammar_occurrences + grammar_items 标签 + 例句, 挂 exam_grammar_stats 真实课标类目考查占比) /
          表达方式(phrases function_expression)
  正文: section_text.raw_text (join sections 取段标题/类型, 按 seq)
数据真值, 无则空 (不假填)。考察重点标注只用已有真实边/统计 (坑16 不臆测): 词=真题命中次数,
语法=课标第二级子类辽宁考查占比 (grammar_category_pct, 单一计算点复用 exam_grammar_stats);
短语/句型/表达无短语级考查边, 诚实标"出现非考查" (PHRASE_LIB_NOTE), 不伪造考查标签。
"""
from __future__ import annotations

import duckdb

from backend.api.db import rows_to_dicts
from backend.services.exam_grammar_stats import PHRASE_LIB_NOTE, grammar_category_pct


def _vocab(con, v, vol, u):
    """单词 + 真实辽宁高考命中次数 (exam_vocabulary.gaokao_hit_ln, 真值非估算)."""
    return rows_to_dicts(con.execute(
        "SELECT uvi.word AS word, uvi.pos AS pos, uvi.zh_def AS zh_def, uvi.in_curriculum AS in_curriculum, "
        "COALESCE(ev.gaokao_hit_ln, 0) AS gaokao_hit_ln "
        "FROM unit_vocab_intro uvi LEFT JOIN exam_vocabulary ev ON ev.word = LOWER(uvi.word) "
        "WHERE uvi.version_key=? AND uvi.volume_key=? AND uvi.unit_number=? ORDER BY uvi.word", [v, vol, u]))


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


def _grammar(con, v, vol, u, cat_pct):
    """语法点 (grammar_occurrences join grammar_items 取人话标签 + 例句 + 课标第二级类目辽宁考查占比).

    category/category_pct 用同一个 split_part 表达式取课标第二级父类 (与 exam_grammar_stats
    单一计算点一致, 不重派生新口径); cat_pct 由调用方传入 (整单元只需算一次真实占比 map)。
    """
    rows = rows_to_dicts(con.execute(
        "SELECT gi.label AS label, go.example_sentence AS example, "
        "cat.label AS category "
        "FROM grammar_occurrences go LEFT JOIN grammar_items gi ON gi.grammar_item_id = go.grammar_item_id "
        "LEFT JOIN grammar_items cat ON cat.grammar_item_id = "
        "  CASE WHEN instr(go.grammar_item_id,'/')>0 "
        "       THEN split_part(go.grammar_item_id,'/',1)||'/'||split_part(go.grammar_item_id,'/',2) "
        "       ELSE go.grammar_item_id END "
        "WHERE go.version_key=? AND go.volume_key=? AND go.unit_number=? ORDER BY go.occ_id", [v, vol, u]))
    for r in rows:
        r["category_pct"] = cat_pct.get(r.get("category"))  # None = 该类目辽宁卷暂无考查边 (诚实, 非0)
    return rows


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
    cat_pct = grammar_category_pct(con)   # 整单元只算一次 (Rule1 单一计算点, 供每条语法occurrence查)
    grammar = _grammar(con, version, volume, unit, cat_pct)
    passages = _passages(con, version, volume, unit)
    return {
        "version_key": version, "volume_key": volume, "unit_number": unit,
        "knowledge": {
            "vocab": vocab, "vocab_n": len(vocab),
            "collocation": ph["collocation"], "sentence_pattern": ph["sentence_pattern"],
            "expression": ph["expression"], "phrase_note": PHRASE_LIB_NOTE,
            "grammar": grammar,
        },
        "passages": passages, "passages_n": len(passages),
        "note": "教材已解析入库, 知识点(词/短语/句型/语法/表达)+正文 均直出 DB (unit_vocab_intro/phrases/grammar_occurrences/section_text), 不依赖 PDF。"
                "词后数字=该词辽宁高考命中次数(exam_vocabulary真值); 语法后百分比=该类语法辽宁卷考查占比(exam_grammar_stats真值); "
                "短语/句型/表达 出现非考查(诚实分层, 见 phrase_note)。",
    }
