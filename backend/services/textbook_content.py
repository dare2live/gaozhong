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
from backend.services.extraction.example_text import clean_example as _clean_example
from backend.services.trend import scope


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


# 坑(2026-07-05 教师视角审计): grammar_occurrences.example_sentence 抓的是 Grammar section 原始
# 页首文本, 常以"Review: tenses 1 Look at the sentences from the reading passage..."这类练习
# 指令开头, 真正的例句(教材惯用 a/b/c 字母编号短句, 如 "a He was friendly. b The exam made me
# quite nervous.")有的排在指令之后、有的整段就是纯指令没有例句。展示成"e.g."若截在指令中间会
# 显得破碎误导(坑: 词被切一半)。改用正向信号判断: 找不到 a/b/c 字母编号例句模式就不展示"e.g."
# (诊断不出真例句就不展示, 好过展示错的/纯指令冒充例句, 同一套哲学见 exam_grammar_stats.PHRASE_LIB_NOTE)。
# 逻辑收口于 backend/services/extraction/example_text.py (坑: 根因审计发现 lesson_plan.py 独立
# 一份 [:120] 硬截, 与此处不一致, Rule5 抽共享后两处复用同一实现)。


def _grammar(con, v, vol, u, cat_pct_new, cat_pct_old):
    """语法点 (grammar_occurrences join grammar_items 取人话标签 + 例句 + 课标第二级类目辽宁考查占比).

    category/category_pct 用同一个 split_part 表达式取课标第二级父类 (与 exam_grammar_stats
    单一计算点一致, 不重派生新口径); cat_pct_new/cat_pct_old 由调用方传入 (整单元只需各算一次真实占比 map)。

    坑(2026-07-06 数据关联设计审查): 原只吃 grammar_category_pct()默认(仅ERA_NEW=2021+新高考II),
    但当前全部 tests_grammar 边 100% 来自 ERA_OLD(2015-2020旧课标II), 导致该徽章对几乎全部教材
    语法条目(51条实测0/51命中)系统性显示"暂无考查数据"——不是数据真的没有, 是只看了没数据的那个
    era。改为: ERA_NEW 有数据优先展示(当前卷制真值); 无数据则展示 ERA_OLD 历史占比, 但显式标注
    "历史参考"(category_pct_era 字段), 不与当前卷制真值混同——不是"冒用历史数据充当前真值"
    (那正是 grammar_category_pct 当初要防的坑12), 而是"诚实展示仅有的数据, 讲清楚它是哪个卷制的"。
    """
    rows = rows_to_dicts(con.execute(
        "SELECT go.grammar_item_id AS grammar_item_id, gi.label AS label, go.example_sentence AS example, "
        "cat.label AS category "
        "FROM grammar_occurrences go LEFT JOIN grammar_items gi ON gi.grammar_item_id = go.grammar_item_id "
        "LEFT JOIN grammar_items cat ON cat.grammar_item_id = "
        "  CASE WHEN instr(go.grammar_item_id,'/')>0 "
        "       THEN split_part(go.grammar_item_id,'/',1)||'/'||split_part(go.grammar_item_id,'/',2) "
        "       ELSE go.grammar_item_id END "
        "WHERE go.version_key=? AND go.volume_key=? AND go.unit_number=? ORDER BY go.occ_id", [v, vol, u]))
    for r in rows:
        cat = r.get("category")
        pct_new = cat_pct_new.get(cat)
        pct_old = cat_pct_old.get(cat)
        if pct_new is not None:
            r["category_pct"], r["category_pct_era"] = pct_new, None
        elif pct_old is not None:
            r["category_pct"], r["category_pct_era"] = pct_old, "历史参考(仅旧课标II 2015-2020, 非当前卷制真值)"
        else:
            r["category_pct"], r["category_pct_era"] = None, None  # 该类目两卷制均暂无考查边 (诚实, 非0)
        r["example"] = _clean_example(r.get("example"))
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
    # 整单元只各算一次 (Rule1 单一计算点, 供每条语法occurrence查); ERA_OLD 兜底见 _grammar() 坑注释。
    cat_pct_new = grammar_category_pct(con)
    cat_pct_old = grammar_category_pct(con, era=scope.ERA_OLD)
    grammar = _grammar(con, version, volume, unit, cat_pct_new, cat_pct_old)
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
