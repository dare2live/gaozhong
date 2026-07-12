"""摸底弱点 → 教学提纲课节高亮 (单一计算点).

路径: student_weakness(exam_point:theme_l2:*) → syllabus lessons focus 匹配.
genre/cognitive 弱点无主题课节映射 → 诚实列入 unmatched_weaknesses, 不高亮假匹配.
零作答/无弱点 → empty=True (不伪造推荐).
"""
from __future__ import annotations

import duckdb

from backend.services.course.syllabus import syllabus


def gap_highlights(con: duckdb.DuckDBPyConnection, student_id: str) -> dict:
    """返学习者缺口闭环: 弱点主题群 ↔ 课节 seq 高亮清单."""
    sid = (student_id or "").strip()
    if not sid:
        return {"error": "student_id required", "empty": True, "highlights": []}

    n_ans = con.execute(
        "SELECT COUNT(*) FROM student_answers WHERE student_id = ?", [sid]
    ).fetchone()[0]
    weak = con.execute(
        "SELECT concept_id, weakness_score, sample_n FROM student_weakness "
        "WHERE student_id = ? ORDER BY weakness_score DESC",
        [sid],
    ).fetchall()

    if n_ans == 0 or not weak:
        return {
            "student_id": sid,
            "empty": True,
            "n_answers": n_ans,
            "highlights": [],
            "unmatched_weaknesses": [],
            "note": "无真实作答/弱点 → 不高亮不伪造 (坑4); 先完成摸底再看缺口课节.",
        }

    syl = syllabus(con)
    by_focus: dict[str, list[int]] = {}
    for les in syl["lessons"]:
        by_focus.setdefault(les["focus"], []).append(les["seq"])

    highlights: list[dict] = []
    unmatched: list[dict] = []
    for cid, score, n in weak:
        if not cid.startswith("exam_point:theme_l2:"):
            unmatched.append({
                "concept_id": cid, "score": score, "sample_n": n,
                "reason": "非 theme_l2 考点, 无课节焦点映射",
            })
            continue
        theme = cid.split(":", 2)[-1]
        seqs = by_focus.get(theme) or []
        if not seqs:
            unmatched.append({
                "concept_id": cid, "score": score, "sample_n": n,
                "reason": f"主题群 {theme!r} 未分配课节",
            })
            continue
        highlights.append({
            "concept_id": cid,
            "focus": theme,
            "weakness_score": score,
            "sample_n": n,
            "lesson_seqs": seqs,
        })

    return {
        "student_id": sid,
        "empty": False,
        "n_answers": n_ans,
        "highlights": highlights,
        "unmatched_weaknesses": unmatched,
        "note": "高亮=弱点 theme_l2 与教学提纲 focus 对齐的课节; 作业仍为辽宁真题非生成.",
    }
