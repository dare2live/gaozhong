"""考查的"高中知识点"占比 (语法结构 / 短语句式 / 完形搭配) — 2026-07-07 用户追问方法论落地.

背景: cloze_answer_word_stage (attribution.py) 只测了得分点词本身的**词汇难度**, 用户指出
这不够本质 —— 完形填空/语法填空很多时候考的不是"这个词认不认识", 而是"哪个短语/固定搭配/
语法结构符合语境"这类知识, 用词汇难度衡量不出来。本模块是 workflow 三路并行调研(短语基线
可行性/空格知识类型可分类性/语法高中独有占比复算)+对抗设计评审后的最终落地范围, 三份交付
物 + 一处明确拒绝(诚实标缺口, 不造假替代指标):

1. grammar_structural_coverage(): 语法填空+短文改错(题型定义即排除语义辨析, 零主观判断
   成本) — 108个课标语法点辽宁真题精确印证覆盖, 只报绝对数量+名单, 不报占比(35题 vs 108
   语法点不是同一统计总体的抽样关系, 24是关键词匹配抠出的**下限**非精确测量值)。复用
   grammar_4q.py 坑31 修复后的精确匹配逻辑。
2. phrase_pattern_exam_relevance(): 短语/句型/表达(phrases表)与辽宁真题文本的共现关联,
   分"初中已学(junior_known) vs 高中新学(senior_only)"。历史记录(2026-07-07 首次调研):
   曾误判"初中基线不存在"(调研1只查了 data/junior_high/structured/*.jsonl 结构化产物,
   没查到 data/junior_high/textbooks/hujiao/{7a..9b}.pdf 教材原文其实本地已有)——用户
   指出后核实原文确在, 用 scripts/extract_hujiao_phrases.py 复用高中同一套
   _scan_text 规则(颗粒度对齐, 非另起标准)抽取, 补上了这条线(初中50个短语, 高中93个
   里44个初中已学/49个高中新学)。
3. cloze_collocation_structural_subset(): 完形填空180空(10篇, 同 attribution.py 范围
   限定)里两层判断并存不混淆(坑16对称: 客观规则 vs 转录人工标注不能装进同一个"客观"桶):
   (a) 结构规则(≥2个多词选项共享token)可客观确认的"像固定搭配"子集, 明确标"下限,
   非真实占比"; (b) 官方解析文本"考查XX"标签转录统计(词义辨析/搭配/篇章衔接三分桶),
   明确标 provenance=human_transcribed(未独立验证, 不当D0客观事实)。

单一计算点(Rule1): 语法维度复用 grammar_4q.py 的 TERM_TO_LABEL_KEYWORD/match_ids_for_term
(不重写匹配算法); 完形填空维度复用 attribution.py 的 qualifying_cloze_rows/parse_cloze_options
(不重新解析选项); 短语维度复用 exam_grammar_stats.py 的 PHRASE_LIB_NOTE(不重写"出现非考查"
caveat) + backend.services.extraction.phrases._scan_text(初高中同一套抽取规则)。
"""
from __future__ import annotations

import re

import duckdb

from backend.services.audit.grammar_4q import TERM_TO_LABEL_KEYWORD, match_ids_for_term
from backend.services.exam_grammar_stats import PHRASE_LIB_NOTE

from .attribution import parse_cloze_options, qualifying_cloze_rows

_GRAMMAR_STRUCTURAL_QTYPES = ("语法填空", "短文改错")


def _n_tests_phrase(con: duckdb.DuckDBPyConnection) -> int:
    return con.execute("SELECT COUNT(*) FROM edges WHERE relation='tests_phrase'").fetchone()[0]


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


_JUNIOR_VERSION = "hujiao"


def _phrase_stage(canonical: str, junior_set: set[str]) -> str:
    return "junior_known" if canonical.strip().lower() in junior_set else "senior_only"


def _phrase_exam_match(senior: list[tuple], junior_set: set[str], blob_all: str) -> dict:
    """遍历高中短语库, 按学段分组统计 + 找真题文本命中. 拆出降 phrase_pattern_exam_relevance CC."""
    by_type: dict[str, int] = {}
    by_stage: dict[str, int] = {"junior_known": 0, "senior_only": 0}
    matched: list[dict] = []
    matched_by_stage: dict[str, int] = {"junior_known": 0, "senior_only": 0}
    for canonical, ptype in senior:
        group = ptype.split(":", 1)[0] if ptype else "unknown"
        by_type[group] = by_type.get(group, 0) + 1
        stage = _phrase_stage(canonical, junior_set)
        by_stage[stage] += 1
        if canonical and canonical.strip() and canonical.strip() in blob_all:
            matched.append({"canonical": canonical.strip(), "phrase_type": ptype, "stage": stage})
            matched_by_stage[stage] += 1
    return {"by_type": by_type, "by_stage": by_stage, "matched": matched, "matched_by_stage": matched_by_stage}


def phrase_pattern_exam_relevance(con: duckdb.DuckDBPyConnection) -> dict:
    """短语/句型/表达(phrases表)与辽宁真题文本的共现关联, 分"初中已学 vs 高中新学".

    2026-07-07 补 STEP1 缺口: 此前(见本模块 docstring 历史记录)因未找全本地 hujiao 教材
    PDF 原文, 误判"初中基线不存在"。现已用 scripts/extract_hujiao_phrases.py 复用高中
    同一套 _scan_text 规则(颗粒度对齐, 非另起一套判断标准)抽取 6 册沪教牛津教材短语/句型/
    表达, 写入同一张 phrases 表(version_key='hujiao')。"初中已学"= canonical 同时出现在
    hujiao 版; "高中新学"= 只出现在 renjiao/waiyan 版。
    """
    junior_set = {c.strip().lower() for (c,) in con.execute(
        "SELECT DISTINCT canonical FROM phrases WHERE version_key = ?", [_JUNIOR_VERSION]
    ).fetchall()}
    senior = con.execute(
        "SELECT DISTINCT canonical, phrase_type FROM phrases WHERE version_key != ?",
        [_JUNIOR_VERSION],
    ).fetchall()
    senior_canonicals = {c.strip().lower() for c, _t in senior}

    exam_rows = con.execute(
        "SELECT raw_question, analysis FROM exam_questions WHERE province LIKE '辽宁%'"
    ).fetchall()
    blob_all = " ".join((q or "") + " " + (a or "") for q, a in exam_rows)

    agg = _phrase_exam_match(senior, junior_set, blob_all)
    by_type, by_stage = agg["by_type"], agg["by_stage"]
    matched, matched_by_stage = agg["matched"], agg["matched_by_stage"]

    return {
        "scope_note": (
            "高中教材短语/句型/表达库(93个, renjiao/waiyan) 与初中沪教牛津库(50个, hujiao)"
            "对齐后分层: junior_known=初中已出现(高中复现巩固), senior_only=只在高中教材"
            "出现(真正新学)。两库均用同一套规则(backend.services.extraction.phrases."
            "_scan_text)抽取, 颗粒度一致, 非各自发明标准。"
        ),
        "n_junior_phrases_total": len(junior_set),
        "n_senior_phrases_total": len(senior_canonicals),
        "n_overlap_junior_known": len(senior_canonicals & junior_set),
        "n_senior_only": len(senior_canonicals - junior_set),
        "phrase_type_breakdown": by_type,
        "phrase_stage_breakdown": by_stage,
        "n_matched_in_exam_text": len(matched),
        "matched_by_stage": matched_by_stage,
        "match_method": "exact_substring_of_canonical_phrase",
        "matched_examples": matched[:20],
        "tests_phrase_edges": _n_tests_phrase(con),
        "honesty": {
            "cooccurrence_is_not_tested": True,
            "tests_phrase_sealed": False,
            "tests_phrase_only_human_verified": True,
            "curated_sample": True,
            "note": (
                "文本共现≠考查; 解析「考查搭配」是类别桶不是 phrase_id; "
                "tests_phrase 仅接受 phrase_human_verified.jsonl 人工抽样核验边(非全量)"
            ),
        },
        "caveat": PHRASE_LIB_NOTE + " 本函数额外核实: tests_phrase 仅 human_verified curated 抽样"
                  "(见 phrase_truth.load_tests_phrase), 与本共现统计物理隔离。"
                  "junior_known/senior_only 是教材库层面的学段对齐,"
                  "不是'这道真题的这个短语按学段考查'的逐题归因(同 word 学段口径的颗粒度边界)。",
        "tested_sample": {
            "relation": "tests_phrase",
            "n_edges": _n_tests_phrase(con),
            "grain": "human_verified_curated_sample",
            "note": "抽样考查边; 不得用共现命中率冒充考查覆盖",
        },
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


def _structural_flags(rows: list[tuple]) -> tuple[int, list[dict]]:
    total = 0
    flagged = []
    for qid, year, opts, _letters in rows:
        for opt4 in opts:
            total += 1
            texts = [o.strip() for o in opt4]
            if _shares_multiword_token(texts):
                flagged.append({"qid": qid, "year": year, "options": texts})
    return total, flagged


_ANALYSIS_LABEL_RE = re.compile(r"考查([^.．。\n]{2,25})[.．。]")


def _classify_analysis_label(label: str) -> str:
    label = label.strip()
    if "短语" in label or "搭配" in label or "固定" in label:
        return "collocation"
    if "语境" in label or "串联" in label or "衔接" in label or "呼应" in label or "语篇" in label:
        return "context_cohesion"
    if "辨析" in label:
        return "word_meaning"
    return "other"


def _human_transcribed_breakdown(con: duckdb.DuckDBPyConnection, qids: list[str]) -> dict:
    """从官方解析文本里逐空抠"考查XX"标签, 按语义分3桶. provenance=human_transcribed:
    这是转录解析作者的人工判断, 不是我方独立验证的客观事实(同坑16对称: dual-model一致
    不代表对, 转录单一人工来源同样不能升格成D0客观事实), 物理隔离在独立字段, 不与
    structural_flags(零语义判断的规则输出)混进同一个"客观"桶。
    """
    if not qids:
        return {"n_labels_extracted": 0, "by_category": {}, "coverage_note": "无可解析题目"}
    qmarks = ",".join(["?"] * len(qids))
    rows = con.execute(
        f"SELECT analysis FROM exam_questions WHERE question_id IN ({qmarks})", qids
    ).fetchall()
    by_cat: dict[str, int] = {}
    for (a,) in rows:
        if not a:
            continue
        for label in _ANALYSIS_LABEL_RE.findall(a):
            cat = _classify_analysis_label(label)
            by_cat[cat] = by_cat.get(cat, 0) + 1
    n = sum(by_cat.values())
    return {
        "provenance": "human_transcribed_from_official_analysis",
        "confidence": "secondary_source_not_independently_verified",
        "n_labels_extracted": n,
        "by_category": by_cat,
        "category_meaning": {
            "word_meaning": "解析标'XX词义辨析/XX的辨析' — 纯词义/词性辨析",
            "collocation": "解析标'短语/搭配/固定X' — 搭配知识",
            "context_cohesion": "解析标'语境理解/上下文串联/衔接/呼应' — 篇章衔接非词汇本身",
        },
        "coverage_note": (
            f"{n} 个空有可读'考查XX'标签(源: 7/10篇有完整逐空解析, 另3篇无解析文本或为占位);"
            " 这是解析作者的人工判断转录, 不是我方独立验证的客观事实, 不作为D0数据入库"
        ),
    }


def cloze_collocation_structural_subset(con: duckdb.DuckDBPyConnection) -> dict:
    """完形填空(10篇, 同 attribution.qualifying_cloze_rows 范围) 两层判断并存不混淆:

    (1) structural_flags: 结构规则(≥2个多词选项共享token, 如"put up with"/"stand up for"
        共享"up")可客观确认的"像固定搭配"子集 — 零语义判断, 但只是**规则能抓到的下限**
        (会漏判"harmful to/mixed with/different from/applied to"这类表层不同根但语义
        仍是固定搭配的空), 不代表"搭配题真实占比"。
    (2) human_transcribed: 官方解析文本"考查XX"标签转录统计(词义辨析/搭配/篇章衔接三桶)。
        **物理隔离成独立字段**(坑16对称: 转录人工标注≠我方独立验证的客观事实), 不与(1)
        的规则输出混进同一个"客观"桶, 防止读者把两种不同置信度的数字当同等可信。
    """
    rows = qualifying_cloze_rows(con)
    total, flagged = _structural_flags(rows)
    qids = [r[0] for r in rows]

    return {
        "province_scope": "辽宁卷",
        "n_passages": len(rows),
        "n_blanks_total": total,
        "structural_flags": {
            "n_structurally_flagged": len(flagged),
            "structurally_flagged_pct": round(100 * len(flagged) / total, 1) if total else None,
            "flag_method": "shared_token_across_multiword_options (共享token, 非语义判断, 零LLM介入)",
            "explicit_ceiling_caveat": (
                "这是规则能抓到的下限, 不是搭配题真实占比。规则只能识别表层token重叠的多词"
                "选项组; 表层不同根但语义仍是固定搭配的空规则漏判, 计入未分类。"
            ),
            "unclassified_count": total - len(flagged),
            "flagged_examples": flagged,
        },
        "human_transcribed": _human_transcribed_breakdown(con, qids),
        "honesty": {
            "tests_phrase_edges": _n_tests_phrase(con),
            "collocation_label_is_not_phrase_id": True,
            "curated_sample": True,
            "phrase_table_exact_option_hits_note": (
                "解析「考查搭配」≈类别统计, 不是 phrase_id; "
                "tests_phrase 仅接受 phrase_human_verified.jsonl 人工抽样, 禁止共现/类别桶 bulk"
            ),
        },
    }
