"""二阶段追问: 根据错题 tag 抽 3-5 题深挖弱点 (Codex Q6).

流程:
  一阶段 9-11 题答完 → scorer 输出 wrong_qids + verdict
  若 verdict in (consolidate, below) → 触发本模块抽追问题
  追问策略: 每错点抽 1-2 题同 tag 不同题, 总共 3-5 题
  最终综合两阶段 → final verdict (二阶段权重高)
"""
from __future__ import annotations

import duckdb


def pick_followup_questions(con: duckdb.DuckDBPyConnection,
                            wrong_qids: list[int],
                            exclude_qids: list[int],
                            n: int = 5) -> dict:
    """抽追问题: 按错题的 word/grammar tag 从 question_bank 抽同 tag 不同题.

    Args:
        wrong_qids: 一阶段错题 qb_id list
        exclude_qids: 一阶段全部题 (排除不重抽)
        n: 目标追问题数 (3-5)
    Returns:
        {questions: [...], tag_coverage: [...]}
    """
    if not wrong_qids:
        return {"questions": [], "tag_coverage": []}

    weak_tags = _extract_weak_tags(con, wrong_qids)
    if not weak_tags:
        return {"questions": [], "tag_coverage": []}

    exclude_set = set(exclude_qids)
    chosen = _pick_by_tags(con, weak_tags, exclude_set, n)
    covered_tags = set()
    for q in chosen:
        covered_tags.update(q.get("matched_tags", []))

    return {
        "questions": chosen,
        "n_questions": len(chosen),
        "tag_coverage": sorted(covered_tags),
        "weak_tags_targeted": sorted(weak_tags),
    }


def compute_final_score(first_result: dict, followup_answers: dict[int, str],
                        followup_questions: list[dict]) -> dict:
    """综合两阶段, 二阶段权重 1.5x."""
    n2 = len(followup_questions)
    if n2 == 0:
        return first_result

    from backend.services.course.loader import get_threshold
    n2_correct = _count_correct(followup_answers, followup_questions)
    acc1 = first_result.get("accuracy", 0)
    acc2 = n2_correct / n2
    w1 = get_threshold("placement.followup_weight_phase1", 1.0)
    w2 = get_threshold("placement.followup_weight_phase2", 1.5)
    combined = (acc1 * w1 + acc2 * w2) / (w1 + w2)

    target = first_result.get("target_layer", "G1")
    rec = _combined_verdict(combined, target)
    return {
        "grade": first_result.get("grade"),
        "target_layer": target,
        "phase1_accuracy": acc1,
        "phase2_accuracy": round(acc2, 3),
        "phase2_correct": n2_correct,
        "phase2_total": n2,
        "combined_accuracy": round(combined, 3),
        "layer_recommendation": rec,
        "weak_concepts": first_result.get("weak_concepts", []),
        "recommended_courses": first_result.get("recommended_courses", []),
    }


def _count_correct(answers: dict[int, str], questions: list[dict]) -> int:
    n = 0
    for q in questions:
        student = (answers.get(q["qb_id"]) or "").strip().upper()
        correct = (q.get("answer") or "").strip().upper()
        if student and student == correct:
            n += 1
    return n


def _combined_verdict(combined: float, target: str) -> dict:
    from backend.services.course.loader import get_threshold
    pass_t = get_threshold("placement.pass_threshold", 0.80)
    consol_t = get_threshold("placement.consolidate_floor", 0.65)
    next_layer = {"G1": "G2", "G2": "G3", "G3": "G_FINAL"}.get(target, target)
    if combined >= pass_t:
        return {"verdict": "pass", "next_layer": next_layer,
                "msg": f"综合水平已达 {target}, 推入 {next_layer} 课节"}
    if combined >= consol_t:
        return {"verdict": "consolidate", "next_layer": target,
                "msg": f"综合水平接近 {target}, 巩固 {target} 课节"}
    return {"verdict": "below", "next_layer": target,
            "msg": f"综合水平低于 {target}, 从 {target} 基础课节开始"}


def _extract_weak_tags(con: duckdb.DuckDBPyConnection,
                       wrong_qids: list[int]) -> list[str]:
    """从错题提取 word/grammar tag (去重, 按频次降序)."""
    placeholders = ",".join("?" * len(wrong_qids))
    rows = con.execute(
        f"SELECT qt.tag_id, COUNT(*) as cnt "
        f"FROM question_tags qt "
        f"JOIN tag_dictionary td ON td.tag_id = qt.tag_id "
        f"WHERE qt.qb_id IN ({placeholders}) "
        f"AND td.tag_kind IN ('word', 'grammar') "
        f"GROUP BY qt.tag_id ORDER BY cnt DESC",
        wrong_qids,
    ).fetchall()
    return [r[0] for r in rows]


def _pick_by_tags(con: duckdb.DuckDBPyConnection,
                  weak_tags: list[str], exclude: set[int],
                  n: int) -> list[dict]:
    """每 weak_tag 抽 1-2 题, 总不超 n, 轮询分散覆盖."""
    chosen: list[dict] = []
    chosen_ids: set[int] = set()
    tag_quota = max(1, n // len(weak_tags)) if weak_tags else 1
    # 第一轮: 每 tag 配额内抽
    chosen, chosen_ids = _fill_from_tags(con, weak_tags, exclude, chosen, chosen_ids, n, tag_quota)
    # 第二轮: 不够则补
    if len(chosen) < n:
        chosen, chosen_ids = _fill_from_tags(con, weak_tags, exclude, chosen, chosen_ids, n, 2)
    return chosen


def _fill_from_tags(con, tags, exclude, chosen, chosen_ids, n, quota):
    for tag in tags:
        if len(chosen) >= n:
            break
        candidates = _questions_with_tag(con, tag, exclude | chosen_ids)
        for c in candidates[:quota]:
            if len(chosen) >= n:
                break
            chosen.append({**c, "matched_tags": [tag]})
            chosen_ids.add(c["qb_id"])
    return chosen, chosen_ids


def _questions_with_tag(con: duckdb.DuckDBPyConnection,
                        tag_id: str, exclude: set[int]) -> list[dict]:
    """查含指定 tag 的题 (排除已用)."""
    rows = con.execute(
        "SELECT DISTINCT qb.qb_id, qb.question_type, qb.stem, "
        "qb.options_json, qb.answer, qb.difficulty "
        "FROM question_bank qb "
        "JOIN question_tags qt ON qt.qb_id = qb.qb_id "
        "WHERE qt.tag_id = ? "
        "ORDER BY qb.qb_id",
        [tag_id],
    ).fetchall()
    return [
        {"qb_id": r[0], "question_type": r[1], "stem": r[2],
         "options_json": r[3], "answer": r[4], "difficulty": r[5]}
        for r in rows if r[0] not in exclude
    ]
