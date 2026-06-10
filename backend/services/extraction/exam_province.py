"""真题省份精炼 (F) — 用题面 + 年份 + 卷型推断 → 更新 exam_questions.province.

旧启发式: 2021+ 默认推断辽宁 → 实际 32/334 标"辽宁"
新启发式 (实际辽宁卷型映射):
  - 2010-2014: 辽宁卷 (独立命题)
  - 2015-2016: 新课标 II 卷 (全国 II)
  - 2017-2020: 全国 II 卷 (省份合并阶段)
  - 2021+ : 新课标 II 卷
  - 题面 grep "辽宁"/"新课标 II" → 强证据
"""
from __future__ import annotations

import duckdb

from backend.services.extraction import exam as exam_extract


def _infer_v2(year: int | None, text: str) -> str:
    return exam_extract.infer_province(year, text)


def refine_province(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT question_id, year, raw_question FROM exam_questions"
    ).fetchall()
    updated = 0
    counts: dict[str, int] = {}
    for qid, yr, q in rows:
        new_prov = _infer_v2(yr, q or "")
        con.execute("UPDATE exam_questions SET province=? WHERE question_id=?",
                    [new_prov, qid])
        counts[new_prov] = counts.get(new_prov, 0) + 1
        updated += 1
    return {"updated": updated, "counts": counts}
