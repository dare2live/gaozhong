"""4.7.E 弱点真算 service — 从 student_answers 算 student_weakness, 替 demo 写死.

算法 (P0 简单可解释):
  弱化度 = 1 - (正确率 * sqrt(min(n,10)/10))
  即 正确率低 + 样本足 → 弱化度高
  样本 < 3 不入弱点 (避免单样本误判)

2026-06-16 (件2 拱心石落地后): 弱点维度从 **word token(假象)** 改为 **exam_point 真考点**
  (genre/theme/主题群; critic 盲点#2 修复)。每题考的真考点(tests_exam_point 边)归入该生命中点 —
  错题 → 其真考点 → 薄弱环节。取代"把整篇实词当考点"的 token 假象 (一题错≠该篇每个词都弱)。
  路径: student_answers → question_bank.origin_ref(=exam_questions.id) → 'question:'||id → tests_exam_point 边 → exam_point 节点。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import duckdb

MIN_SAMPLES = 3
WEAK_THRESHOLD = 0.40  # 弱化度 ≥ 0.40 才入表


def recompute_all(con: duckdb.DuckDBPyConnection) -> dict:
    """重算所有学生的 student_weakness. 返回 {students_processed, weakness_rows}.

    Guard: 若 student_answers 总行 = 0, 不清旧弱点 (保 demo, 避免 UI 空白).
    """
    n_answers = con.execute("SELECT COUNT(*) FROM student_answers").fetchone()[0]
    if n_answers == 0:
        return {"students_processed": 0, "weakness_rows": 0,
                "note": "student_answers 表为空, 保留旧弱点 (demo); "
                        "等 4.7.D csv 导真答题数据再调."}
    sids = [r[0] for r in con.execute("SELECT student_id FROM students").fetchall()]
    con.execute("DELETE FROM student_weakness")
    total_rows = 0
    for sid in sids:
        total_rows += _compute_one_student(con, sid)
    return {"students_processed": len(sids), "weakness_rows": total_rows}


def recompute_one(con: duckdb.DuckDBPyConnection, student_id: str) -> dict:
    con.execute("DELETE FROM student_weakness WHERE student_id = ?", [student_id])
    n = _compute_one_student(con, student_id)
    return {"student_id": student_id, "weakness_rows": n}


def _compute_one_student(con: duckdb.DuckDBPyConnection, sid: str) -> int:
    """算 1 学生的弱点, 写表, 返回新增行数."""
    rows = con.execute(
        "SELECT e.dst_id AS concept_id, sa.is_correct "
        "FROM student_answers sa "
        "JOIN question_bank qb ON qb.qb_id = sa.question_id::BIGINT "
        "JOIN edges e ON e.src_id = ('question:' || qb.origin_ref) "
        "  AND e.relation = 'tests_exam_point' "
        "WHERE sa.student_id = ?",
        [sid],
    ).fetchall()
    # 聚合 concept → (n, n_correct)
    agg: dict[str, list[int]] = {}
    for tag_id, is_correct in rows:
        a = agg.setdefault(tag_id, [0, 0])
        a[0] += 1
        if is_correct:
            a[1] += 1
    # 算弱化度 + 写表
    now = datetime.now(timezone.utc).isoformat()
    n_written = 0
    for concept_id, (n, n_correct) in agg.items():
        if n < MIN_SAMPLES:
            continue
        accuracy = n_correct / n
        weakness = _weakness_score(accuracy, n)
        if weakness < WEAK_THRESHOLD:
            continue
        con.execute(
            "INSERT INTO student_weakness "
            "(student_id, concept_id, weakness_score, sample_n, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [sid, concept_id, round(weakness, 3), n, now],
        )
        n_written += 1
    return n_written


def _weakness_score(accuracy: float, n: int) -> float:
    """弱化度 = (1 - 正确率) × 样本可信度因子.

    n < 10  → 因子线性 sqrt(n/10) (样本越足越可信)
    n ≥ 10  → 因子 1.0
    """
    confidence = math.sqrt(min(n, 10) / 10)
    return (1 - accuracy) * confidence


def class_weakness(con: duckdb.DuckDBPyConnection, class_id: str, limit: int = 30) -> dict:
    """班级 × 真考点弱点聚合 (域B 学情热力; 派生事实单算点 — 路由不重写 AVG/COUNT agg, Rule1/审计MEDIUM).

    返回 {rows: [(concept_id, label, avg_score, n_weak_students, total_sample)], n_students}.
    """
    rows = con.execute(
        "SELECT w.concept_id, COALESCE(n.label, w.concept_id) AS label, "
        "       AVG(w.weakness_score) AS avg_score, COUNT(DISTINCT w.student_id) AS n_stu, "
        "       SUM(w.sample_n) AS total_n "
        "FROM student_weakness w "
        "JOIN students s ON s.student_id = w.student_id AND s.class_id = ? "
        "LEFT JOIN nodes n ON n.concept_id = w.concept_id "
        "GROUP BY w.concept_id, label ORDER BY avg_score DESC LIMIT ?", [class_id, limit]
    ).fetchall()
    n_stu = con.execute("SELECT COUNT(*) FROM students WHERE class_id = ?", [class_id]).fetchone()[0]
    return {"rows": rows, "n_students": n_stu}
