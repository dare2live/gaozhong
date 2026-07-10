"""D0: 考查的"高中知识点"占比 (backend/services/exam_point/senior_knowledge.py, 2026-07-07)。

用户质疑 cloze_answer_word_stage 只测词汇难度不够本质, 追加语法结构/短语句式/完形搭配
三项分析(workflow并行调研+对抗设计评审后落地)。校验内部自洽 + 不越界报百分比/占比。
"""
from __future__ import annotations

import duckdb


def check_grammar_structural_coverage(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (44) 高中语法知识点结构性覆盖 (语法填空+短文改错, 坑25修复后) ===")
    from backend.services.exam_point.senior_knowledge import grammar_structural_coverage
    d = grammar_structural_coverage(con)

    check("report_as 显式声明只报绝对数量(不报占比, 35题vs108课标点非同一统计总体)",
          d["report_as"] == "absolute_count_and_list_not_percentage", d["report_as"])
    check("confirmed_items 长度 == n_grammar_items_confirmed (计数自洽)",
          len(d["confirmed_items"]) == d["n_grammar_items_confirmed"], f"{len(d['confirmed_items'])}")
    check("n_grammar_items_confirmed <= n_grammar_items_total (无越界)",
          d["n_grammar_items_confirmed"] <= d["n_grammar_items_total"],
          f"{d['n_grammar_items_confirmed']}/{d['n_grammar_items_total']}")
    check("junior_high_deepens_edge_count + senior_only_grammar_item_count == 108 (对账)",
          d["junior_high_deepens_edge_count"] + d["senior_only_grammar_item_count"] == d["n_grammar_items_total"],
          f"{d['junior_high_deepens_edge_count']}+{d['senior_only_grammar_item_count']}")
    bad = [it for it in d["confirmed_items"] if not it.get("label")]
    check("confirmed_items 每条 label 非空(无杜撰空标签)", not bad, f"空label={len(bad)}")


def check_phrase_pattern_exam_relevance(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (45) 短语/句型/表达 真题文本共现 (初中已学/高中新学分层, 坑hujiao短语补齐后) ===")
    from backend.services.exam_point.senior_knowledge import phrase_pattern_exam_relevance
    d = phrase_pattern_exam_relevance(con)

    check("scope_note 显式声明初中已学vs高中新学分层依据(颗粒度对齐说明)",
          "junior_known" in d["scope_note"] and "senior_only" in d["scope_note"], "")
    check("n_matched_in_exam_text <= n_senior_phrases_total (无越界)",
          d["n_matched_in_exam_text"] <= d["n_senior_phrases_total"],
          f"{d['n_matched_in_exam_text']}/{d['n_senior_phrases_total']}")
    check("phrase_type_breakdown 分组求和 == n_senior_phrases_total (计数自洽)",
          sum(d["phrase_type_breakdown"].values()) == d["n_senior_phrases_total"],
          f"{sum(d['phrase_type_breakdown'].values())} vs {d['n_senior_phrases_total']}")
    check("phrase_stage_breakdown 求和 == n_senior_phrases_total (计数自洽)",
          sum(d["phrase_stage_breakdown"].values()) == d["n_senior_phrases_total"],
          f"{sum(d['phrase_stage_breakdown'].values())} vs {d['n_senior_phrases_total']}")
    check("n_overlap_junior_known + n_senior_only == n_senior_phrases_total (对账)",
          d["n_overlap_junior_known"] + d["n_senior_only"] == d["n_senior_phrases_total"],
          f"{d['n_overlap_junior_known']}+{d['n_senior_only']}")
    check("matched_by_stage 求和 == n_matched_in_exam_text (计数自洽)",
          sum(d["matched_by_stage"].values()) == d["n_matched_in_exam_text"],
          f"{sum(d['matched_by_stage'].values())} vs {d['n_matched_in_exam_text']}")
    check("caveat 含'出现非考查'诚实披露(复用既有PHRASE_LIB_NOTE)",
          "出现非考查" in d["caveat"] or "出现≠考查" in d["caveat"], "")
    n_tp = con.execute("SELECT COUNT(*) FROM edges WHERE relation='tests_phrase'").fetchone()[0]
    check("无 tests_phrase 边 (短语级真题考查未建; introduces_phrase=教材出现, 防冒充考查)",
          n_tp == 0, f"{n_tp}")


def check_cloze_collocation_structural_subset(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (46) 完形填空搭配 结构性子集+人工转录分桶 (两层物理隔离不混淆) ===")
    from backend.services.exam_point.senior_knowledge import cloze_collocation_structural_subset
    d = cloze_collocation_structural_subset(con)
    sf, ht = d["structural_flags"], d["human_transcribed"]

    check("n_passages == 10 (同 cloze_answer_word_stage 范围限定, 单一计算点)",
          d["n_passages"] == 10, f"{d['n_passages']}")
    check("structural_flags: n_structurally_flagged + unclassified_count == n_blanks_total (计数自洽)",
          sf["n_structurally_flagged"] + sf["unclassified_count"] == d["n_blanks_total"],
          f"{sf['n_structurally_flagged']}+{sf['unclassified_count']} vs {d['n_blanks_total']}")
    check("structural_flags: explicit_ceiling_caveat 声明'下限'非'真实占比' (防误读)",
          "下限" in sf["explicit_ceiling_caveat"], "")
    check("structural_flags: flagged_examples 长度 == n_structurally_flagged (无隐藏丢弃)",
          len(sf["flagged_examples"]) == sf["n_structurally_flagged"], f"{len(sf['flagged_examples'])}")
    check("human_transcribed: provenance 显式标 human_transcribed (物理隔离不当D0客观事实)",
          ht.get("provenance") == "human_transcribed_from_official_analysis", str(ht.get("provenance")))
    check("human_transcribed: by_category 求和 == n_labels_extracted (计数自洽)",
          sum(ht["by_category"].values()) == ht["n_labels_extracted"],
          f"{sum(ht['by_category'].values())} vs {ht['n_labels_extracted']}")
    check("两层物理隔离: structural_flags 与 human_transcribed 是不同顶层key (不混进同一'客观'桶)",
          "structural_flags" in d and "human_transcribed" in d and
          "n_structurally_flagged" not in d and "by_category" not in d, "")
