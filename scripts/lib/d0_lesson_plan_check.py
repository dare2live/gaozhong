"""D0 备课整合校验 — generate_lesson_plan 一体视图的派生正确性 (单一计算点 + 确定性).

备课整合把 unit → 词/语法/主题考点/真题对齐 收口到 lesson_plan 单一 service。D0 守:
  1. **单一计算点守恒 (Rule 1)**: recommend.unit_exam_alignment 与 vocab.unit_word_exam_alignment
     与 lesson_plan.alignment_summary 三方必须**字节一致** (同一原语, 无双算分叉);
  2. **确定性 (100% 可复现)**: generate_lesson_plan 两次跑必相同 (修了原 LIMIT 无序 + 同频 tie 的非确定性);
  3. **语法轴 FK 完整**: grammar_occurrences → grammar_items 0 悬挂;
  4. **词序**: words 按 exam_freq_count 降序 (备课贴高考频次, 非任意序)。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import json

import duckdb

from backend.services import lesson_plan, recommend, vocab

# 覆盖两版本 + 必修/选必 + 有/无语法的代表单元 (诚实抽样, 非全量但跨维度)
_SAMPLE_UNITS = [
    "unit:waiyan/bixiu_1/U1",
    "unit:renjiao/bixiu_1/U4",
    "unit:waiyan/bixiu_2/U5",
    "unit:renjiao/xuanze_1/U5",
]


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _c1_single_compute_point(con, check) -> None:
    """单一计算点守恒: recommend == vocab == lesson_plan.alignment_summary (无双算分叉)."""
    div = [u for u in _SAMPLE_UNITS
           if not (_canon(recommend.unit_exam_alignment(con, u))
                   == _canon(vocab.unit_word_exam_alignment(con, u))
                   == _canon(lesson_plan.generate_lesson_plan(con, u)["alignment_summary"]))]
    check("词∩真题 单一计算点守恒 (recommend==vocab==lesson_plan)", not div,
          "三方一致" if not div else f"分叉: {div}")


def _c2_deterministic(con, check) -> None:
    """确定性: generate_lesson_plan 多跑字节一致 (DuckDB 并行下无序查询会变序, 所有 SELECT 须全序 ORDER BY)."""
    nondet = [u for u in _SAMPLE_UNITS
              if len({_canon(lesson_plan.generate_lesson_plan(con, u)) for _ in range(3)}) != 1]
    check("generate_lesson_plan 确定性 (3跑一致)", not nondet,
          "可复现" if not nondet else f"非确定: {nondet}")


def _c3_grammar_fk(con, check) -> None:
    """语法轴 FK 完整: grammar_occurrences → grammar_items 0 悬挂."""
    orphan = con.execute(
        "SELECT COUNT(*) FROM grammar_occurrences g "
        "LEFT JOIN grammar_items gi ON gi.grammar_item_id = g.grammar_item_id "
        "WHERE gi.grammar_item_id IS NULL"
    ).fetchone()[0]
    check("grammar_occurrences → grammar_items 0 悬挂", orphan == 0, f"orphan={orphan}")


def _c4_word_order(con, check) -> None:
    """词按高考频次降序 (备课贴高考, 非任意序)."""
    bad = [u for u in _SAMPLE_UNITS
           if (fs := [w["exam_freq_count"] for w in lesson_plan.generate_lesson_plan(con, u)["words"]])
           != sorted(fs, reverse=True)]
    check("words 按 exam_freq_count 降序", not bad,
          "有序" if not bad else f"乱序: {bad}")


def _grammar_trace_qids(con, unit_id: str) -> list[str]:
    return [t["question_id"]
            for g in lesson_plan.generate_lesson_plan(con, unit_id)["grammar"]
            for t in g["recent_exam_trace"]]


def _c5_grammar_province(con, check) -> None:
    """语法轴真题溯源 province 锚定辽宁 (§7; 与 word/related_exams 同省, 不混外省冒充辽宁备课锚)."""
    leak = []
    for u in _SAMPLE_UNITS:
        qids = _grammar_trace_qids(con, u)
        if not qids:
            continue
        ph = ",".join("?" * len(qids))
        non_ln = con.execute(
            f"SELECT COUNT(*) FROM exam_questions "
            f"WHERE question_id IN ({ph}) AND province NOT LIKE '辽宁%'", qids,
        ).fetchone()[0]
        if non_ln:
            leak.append((u, non_ln))
    check("语法轴真题溯源全辽宁卷 (§7 不混外省)", not leak,
          "全辽宁" if not leak else f"外省泄漏: {leak[:3]}")


def check_lesson_plan(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (24) 备课整合一体视图 (单一计算点 + 确定性) ===")
    for fn in (_c1_single_compute_point, _c2_deterministic, _c3_grammar_fk,
               _c4_word_order, _c5_grammar_province):
        fn(con, check)
