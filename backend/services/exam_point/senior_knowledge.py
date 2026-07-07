"""考查的"高中知识点"占比 (语法结构 / 短语句式 / 完形搭配) — 2026-07-07 用户追问方法论落地.

背景: cloze_answer_word_stage (attribution.py) 只测了得分点词本身的**词汇难度**, 用户指出
这不够本质 —— 完形填空/语法填空很多时候考的不是"这个词认不认识", 而是"哪个短语/固定搭配/
语法结构符合语境"这类知识, 用词汇难度衡量不出来。本模块是 workflow 三路并行调研(短语基线
可行性/空格知识类型可分类性/语法高中独有占比复算)+对抗设计评审后的最终落地范围, 三份交付
物 + 一处明确拒绝(诚实标缺口, 不造假替代指标):

1. grammar_structural_coverage(): 语法填空+短文改错(题型定义即排除语义辨析, 零主观判断
   成本) — 108个课标语法点辽宁真题精确印证覆盖, 只报绝对数量+名单, 不报占比(35题 vs 108
   语法点不是同一统计总体的抽样关系)。复用 grammar_4q.py 坑31 修复后的精确匹配逻辑。
2. phrase_pattern_exam_relevance(): 短语/句型/表达(phrases表, 高中教材来源) 与辽宁真题
   文本的共现关联 —— 不做初高中对比(见下方"明确拒绝"), 只做"高中教材短语库有哪些在真题
   出现"这一单向查询, 明确标"出现≠考查"(复用既有 PHRASE_LIB_NOTE)。
3. cloze_collocation_structural_subset(): 完形填空180空(10篇, 同 attribution.py 范围
   限定)里, 结构规则(≥2个多词选项共享token, 如"put up with/stand up for"共享"up")可
   客观确认的"像固定搭配"子集 —— 明确标"下限, 非真实占比"(规则会漏判表层不同根但语义
   仍是固定搭配的空, 如"harmful to/mixed with/different from/applied to")。

明确拒绝(调研1实证, 不做假替代): "初中已学 vs 高中新学"的短语/搭配/句型区分做不了 ——
phrases 表(743行)100%来自高中教材(renjiao/waiyan, version_key×volume_key交叉核实), 零
初中来源; 义务教育英语课程标准(2022版)官方PDF本身只有5个附录(核心素养/语音/词汇/语法/
教学案例), 无"词块/固定搭配表"这类可枚举的官方列表, 短语相关表述只是教学理念叙述; 初中4个
结构化jsonl(curriculum_vocab/hujiao_vocab/grammar_items/stage_refined)里仅18条巧合式多词
词条(教材生词表原始收录形式, 非系统性短语抽取), 与高中93个短语canonical仅1条重合
("instead of")。不拿单词学段替代短语学段(范畴错误, 偷换概念) —— word:节点与phrase:节点
是两套独立实体, at_stage边只挂在word:节点上。真正缺口: 需要初中教材课文原文 + 复用现有
phrases.py 抽取模式思路做初中版短语提取, 是独立的STEP1数据采集任务, 不在本次范围内。

单一计算点(Rule1): 语法维度复用 grammar_4q.py 的 TERM_TO_LABEL_KEYWORD/match_ids_for_term
(不重写匹配算法); 完形填空维度复用 attribution.py 的 qualifying_cloze_rows/parse_cloze_options
(不重新解析选项); 短语维度复用 exam_grammar_stats.py 的 PHRASE_LIB_NOTE(不重写"出现非考查"caveat)。
"""
from __future__ import annotations

import re

import duckdb

from backend.services.audit.grammar_4q import TERM_TO_LABEL_KEYWORD, match_ids_for_term
from backend.services.exam_grammar_stats import PHRASE_LIB_NOTE

from .attribution import parse_cloze_options, qualifying_cloze_rows

_GRAMMAR_STRUCTURAL_QTYPES = ("语法填空", "短文改错")


def _grammar_term_hits(rows: list[tuple]) -> dict[str, int]:
    cnt: dict[str, int] = {t: 0 for t in TERM_TO_LABEL_KEYWORD}
    for q, a in rows:
        blob = (q or "") + " " + (a or "")
        for t in TERM_TO_LABEL_KEYWORD:
            if t in blob:
                cnt[t] += 1
    return cnt


def grammar_structural_coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """语法填空+短文改错: 108个课标语法点辽宁真题精确印证覆盖 (零主观判断成本子集).

    可行性依据(workflow独立调研实证): 语法填空题型定义即排除语义辨析(0/29行含ABCD四选一
    模式, 每空只能填给定词的正确形式/功能词, 无第二种可能, 判定依据是题型结构本身而非语义
    判断); 短文改错58个可解析错误项100%显式"考查XX语法类别"标注, 无占位文本。仅这两个
    题型的知识类型判定不涉及主观语义判断; 完形填空的判定需人工/LLM辅助, 见
    cloze_collocation_structural_subset (只报结构规则能确认的下限, 不报知识类型占比)。

    匹配复用 grammar_4q.py 坑31 修复后的精确匹配(match_ids_for_term), 不重写算法。
    样本量诚实(坑12): 35题 vs 108课标语法点不是同一统计总体的抽样关系, 只报绝对数量+
    具体名单, 不报"N/108=XX%"这类无统计学意义的比例。
    """
    qmarks = ",".join(["?"] * len(_GRAMMAR_STRUCTURAL_QTYPES))
    rows = con.execute(
        "SELECT raw_question, analysis FROM exam_questions "
        f"WHERE question_type IN ({qmarks}) AND province LIKE '辽宁%'",
        list(_GRAMMAR_STRUCTURAL_QTYPES),
    ).fetchall()
    term_counts = _grammar_term_hits(rows)
    hits = {t: n for t, n in term_counts.items() if n > 0}

    items = con.execute("SELECT grammar_item_id, parent_id, label FROM grammar_items").fetchall()
    confirmed: set[str] = set()
    for term, kw in TERM_TO_LABEL_KEYWORD.items():
        if hits.get(term):
            confirmed |= match_ids_for_term(items, term, kw)

    label_map = {gid: label for gid, _pid, label in items}
    ordered = sorted(confirmed, key=lambda g: label_map.get(g, ""))
    n_junior_deepens = con.execute(
        "SELECT count(DISTINCT dst_id) FROM edges WHERE relation='deepens'"
    ).fetchone()[0]

    return {
        "province_scope": "辽宁卷",
        "question_types": list(_GRAMMAR_STRUCTURAL_QTYPES),
        "n_questions": len(rows),
        "n_grammar_items_total": len(items),
        "n_grammar_items_confirmed": len(ordered),
        "confirmed_items": [{"grammar_item_id": gid, "label": label_map[gid]} for gid in ordered],
        "match_method": "exact_label_match_post_fix (坑31, grammar_4q.match_ids_for_term)",
        "report_as": "absolute_count_and_list_not_percentage",
        "sample_size_note": (
            f"{len(rows)}题(语法填空+短文改错) vs {len(items)}个课标语法点不是同一统计总体的"
            "抽样关系, 只报绝对数量+具体名单, 不报占比(报占比会被误读成'高中语法点有XX%考过')"
        ),
        "junior_high_deepens_edge_count": n_junior_deepens,
        "senior_only_grammar_item_count": len(items) - n_junior_deepens,
        "senior_only_note": (
            f"{len(items) - n_junior_deepens}个高中课标语法点在初中义务教育课标(2022版)"
            "无对应内容(deepens边缺失=真实课标范围差异, 非测量误差, 已核实blueprint.py"
            "匹配逻辑对71个初中节点0漏检); 该37个中有多少被辽宁真题实际印证需要逐条人工"
            "核对原文(grammar_4q子串匹配的历史误差已证实, 未独立核实的数字不应报, 故此处"
            "不给具体交集数, 只给分母参考)"
        ),
    }


def phrase_pattern_exam_relevance(con: duckdb.DuckDBPyConnection) -> dict:
    """短语/句型/表达(phrases表, 高中教材来源)与辽宁真题文本的共现关联.

    明确拒绝"初中已学vs高中新学"对比(STEP1数据缺口, 见本模块 docstring); 只做"高中教材
    短语库有哪些能在辽宁真题原文/解析文本里找到"这一单向、不需要初中数据的关联查询。
    """
    phrases = con.execute("SELECT DISTINCT canonical, phrase_type FROM phrases").fetchall()
    exam_rows = con.execute(
        "SELECT raw_question, analysis FROM exam_questions WHERE province LIKE '辽宁%'"
    ).fetchall()
    blob_all = " ".join((q or "") + " " + (a or "") for q, a in exam_rows)

    by_type: dict[str, int] = {}
    matched = []
    for canonical, ptype in phrases:
        group = ptype.split(":", 1)[0] if ptype else "unknown"
        by_type[group] = by_type.get(group, 0) + 1
        if canonical and canonical.strip() and canonical.strip() in blob_all:
            matched.append({"canonical": canonical.strip(), "phrase_type": ptype})

    return {
        "scope_note": (
            "不回答'初中已学vs高中新学'(STEP1数据缺口, 短语/搭配/句式现无初中基线, 已核实"
            "官方义务教育课标2022版无可提取的短语/词块枚举列表, 仅教学理念叙述, 见本模块"
            "docstring); 只回答'phrases表(高中教材来源)有哪些能在辽宁真题原文/解析里找到'"
        ),
        "phrase_type_breakdown": by_type,
        "n_phrases_total": len(phrases),
        "n_matched_in_exam_text": len(matched),
        "match_method": "exact_substring_of_canonical_phrase",
        "matched_examples": matched[:20],
        "caveat": PHRASE_LIB_NOTE + " 本函数额外核实: 无 tests_phrase 边(已确认不存在, phrases"
                  "表只有 introduces_phrase 教材边), 此为教材短语库与真题文本的文本共现证据,"
                  "非考查关系的结构性证据。",
    }


def _shares_multiword_token(texts: list[str]) -> bool:
    multiword = [re.findall(r"[a-z']+", t.lower()) for t in texts if " " in t.strip()]
    if len(multiword) < 2:
        return False
    for i in range(len(multiword)):
        for j in range(i + 1, len(multiword)):
            if set(multiword[i]) & set(multiword[j]):
                return True
    return False


def cloze_collocation_structural_subset(con: duckdb.DuckDBPyConnection) -> dict:
    """完形填空(10篇, 同 attribution.qualifying_cloze_rows 范围) 结构规则可确认的
    "像固定搭配"子集 — 下限, 非真实占比估计.

    规则(透明, 零语义判断): 一空的4个选项里, 若存在≥2个多词选项(含空格)共享至少1个token
    (如"put up with"/"stand up for"共享"up"), 判定为"结构上像固定搭配"。此规则**只能确认
    表层token重叠的情况**, 会漏判表层完全不同根但语义仍是固定搭配的空(如"harmful to/
    mixed with/different from/applied to"这类每个选项用词都不同但仍是介词短语固定搭配
    辨析) —— 故本函数产出是**规则能确认的下限**, 不代表"搭配题真实占比"。
    """
    rows = qualifying_cloze_rows(con)
    total = 0
    flagged = []
    for qid, year, opts, _letters in rows:
        for opt4 in opts:
            total += 1
            texts = [o.strip() for o in opt4]
            if _shares_multiword_token(texts):
                flagged.append({"qid": qid, "year": year, "options": texts})

    return {
        "province_scope": "辽宁卷",
        "n_passages": len(rows),
        "n_blanks_total": total,
        "n_structurally_flagged": len(flagged),
        "structurally_flagged_pct": round(100 * len(flagged) / total, 1) if total else None,
        "flag_method": "shared_token_across_multiword_options (共享token, 非语义判断, 零LLM介入)",
        "explicit_ceiling_caveat": (
            "这是规则能抓到的下限, 不是搭配题真实占比。规则只能识别表层token重叠的多词选项组"
            "(如 put up with/stand up for 共享 up); 表层不同根但语义仍是固定搭配的空"
            "(如 harmful to/mixed with/different from/applied to) 规则漏判, 计入未分类。"
        ),
        "unclassified_count": total - len(flagged),
        "unclassified_note": (
            "未被规则标记≠一定是纯词义辨析, 只是结构规则确认不了; 如需更细分类需人工/LLM"
            "辅助读官方解析文本的'考查XX'标签(provenance=human_transcribed, 未独立验证,"
            "不作为D0客观事实入库)"
        ),
        "flagged_examples": flagged,
    }
