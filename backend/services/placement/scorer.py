"""答案打分 → layer 推荐 + 弱点 concepts (D0 100% 准 — 推荐必须可 trace).

输入: paper (generator 输出) + answers {qb_id: 学生填的答案}
输出: {accuracy, layer_recommendation, weak_concepts, recommended_courses}
"""
from __future__ import annotations

import duckdb


def score_paper(con: duckdb.DuckDBPyConnection,
                  paper: dict, answers: dict[int, str], spec: dict) -> dict:
    """评分完整 placement.

    answers: {qb_id: str} — 学生提交的每题答案
    """
    all_q = [q for blk in paper["blocks"] for q in blk["questions"]]
    n = len(all_q)
    if n == 0:
        return {"error": "empty paper"}
    n_correct = 0
    wrong_qids: list[int] = []
    for q in all_q:
        student = (answers.get(q["qb_id"]) or "").strip().upper()
        correct = (q.get("answer") or "").strip().upper()
        if student and student == correct:
            n_correct += 1
        else:
            wrong_qids.append(q["qb_id"])
    accuracy = n_correct / n
    layer_rec = _layer_recommendation(accuracy, spec)
    weak = _weak_concepts(con, wrong_qids)
    rec_courses = _recommend_courses_for_weak(con, weak)
    return {
        "grade": paper["grade"],
        "target_layer": paper["target_layer"],
        "n_total": n,
        "n_correct": n_correct,
        "accuracy": round(accuracy, 3),
        "layer_recommendation": layer_rec,
        "weak_concepts": weak,
        "recommended_courses": rec_courses,
    }


def _layer_recommendation(accuracy: float, spec: dict) -> dict:
    sc = spec.get("scoring") or {}
    pass_t = sc.get("pass_threshold", 0.80)
    strong_t = sc.get("strong_threshold", 0.60)
    target = spec["target_layer"]
    next_layer = {"G1": "G2", "G2": "G3", "G3": "G_FINAL"}.get(target, target)
    if accuracy >= pass_t:
        return {"verdict": "pass", "next_layer": next_layer,
                "msg": f"水平已达 {target}, 推入 {next_layer} 课节"}
    if accuracy >= strong_t:
        return {"verdict": "consolidate", "next_layer": target,
                "msg": f"水平接近 {target}, 巩固 {target} 课节"}
    return {"verdict": "below", "next_layer": target,
            "msg": f"水平低于 {target}, 从 {target} 基础课节开始"}


def _weak_concepts(con: duckdb.DuckDBPyConnection, wrong_qids: list[int]) -> list[dict]:
    """错题的 word/grammar tag → 弱点 concept (去重)."""
    if not wrong_qids:
        return []
    placeholders = ",".join("?" * len(wrong_qids))
    rows = con.execute(
        f"SELECT DISTINCT tag_id FROM question_tags "
        f"WHERE qb_id IN ({placeholders}) "
        f"AND (tag_id LIKE 'word:%' OR tag_id LIKE 'grammar:%') "
        f"LIMIT 30",
        wrong_qids,
    ).fetchall()
    return [
        {"concept_id": r[0], "kind": r[0].split(":", 1)[0]}
        for r in rows
    ]


def _recommend_courses_for_weak(con: duckdb.DuckDBPyConnection,
                                  weak: list[dict]) -> list[dict]:
    """弱点 concept → 推 course (course_materials.ref_id 匹配)."""
    if not weak:
        return []
    concepts = [w["concept_id"] for w in weak]
    placeholders = ",".join("?" * len(concepts))
    rows = con.execute(
        f"SELECT DISTINCT c.course_id, c.layer, c.title, cm.ref_id "
        f"FROM course_materials cm "
        f"JOIN courses c ON c.course_id = cm.course_id "
        f"WHERE cm.ref_id IN ({placeholders}) "
        f"ORDER BY c.layer, c.course_id LIMIT 10",
        concepts,
    ).fetchall()
    return [
        {"course_id": r[0], "layer": r[1], "title": r[2], "weak_concept": r[3]}
        for r in rows
    ]
