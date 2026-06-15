"""学生档案 service — demo 数据灌库 (init_db 灌 1 班 5 学生).

D0 修复 (2026-06-15): 旧版直接写死 student_weakness (weakness_score=0.85, sample_n=12)
却无任何 student_answers 支撑 → 热力图在零真实作答上渲染伪造置信度 = D0 假推违反.
新版改为「seed demo 答题 → weakness.recompute_all 派生」, 弱点 100% 从答题算出
(architecture Rule 1 单一计算点), sample_n / weakness_score 都是真实计算值.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import duckdb

DEMO_CLASS_ID = "sy-no2-2024-g3-1"
DEMO_STUDENTS = [
    ("sy-2024-001", "张明",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_ID),
    ("sy-2024-002", "李华",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_ID),
    ("sy-2024-003", "王芳",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_ID),
    ("sy-2024-004", "刘洋",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_ID),
    ("sy-2024-005", "陈静",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_ID),
]

# 每生基础正确率 (确定性梯度): 弱点从「答错的题」自然稀疏浮现, 不人为定向 concept.
# 这样热力图反映真实作答分布, 而非构造 — autotag 粗粒度问题留给独立任务, 不在此放大.
STUDENT_BASE_ACC = [0.72, 0.78, 0.83, 0.88, 0.92]


def seed_demo(con: duckdb.DuckDBPyConnection) -> dict:
    from backend.services import weakness

    now = datetime.now(timezone.utc).isoformat()
    con.execute("DELETE FROM student_weakness")
    con.execute("DELETE FROM student_answers WHERE source = 'demo'")
    con.execute("DELETE FROM students")
    con.execute("DELETE FROM classes")
    con.execute(
        "INSERT INTO classes VALUES (?, ?, ?, ?, ?, ?)",
        [DEMO_CLASS_ID, None, "沈阳市第二中学", "高三", "高三 1 班 (demo)", now],
    )
    for sid, name, school, city, grade, cid in DEMO_STUDENTS:
        con.execute(
            "INSERT INTO students "
            "(student_id, name, school, city, grade, class_id, enroll_year, created_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [sid, name, school, city, grade, cid, 2022, now, "demo"],
        )
    n_answers = _seed_demo_answers(con, [s[0] for s in DEMO_STUDENTS], now)
    wk = weakness.recompute_all(con)
    return {
        "classes": 1, "students": len(DEMO_STUDENTS),
        "demo_answers": n_answers, "weakness_rows": wk.get("weakness_rows", 0),
    }


def _answerable_qbs(con: duckdb.DuckDBPyConnection) -> list[int]:
    """全部带 word/grammar tag 的题 (有 concept 可归弱点)."""
    rows = con.execute(
        "SELECT DISTINCT qb_id FROM question_tags "
        "WHERE tag_id LIKE 'word:%' OR tag_id LIKE 'grammar:%' "
        "ORDER BY qb_id"
    ).fetchall()
    return [r[0] for r in rows]


def _is_correct(sid: str, qb: int, target_acc: float) -> bool:
    """确定性正确判定: hash(sid,qb) ∈ [0,1) < 目标正确率 → 对."""
    h = hashlib.md5(f"{sid}:{qb}".encode()).hexdigest()[:8]
    return (int(h, 16) / 0xFFFFFFFF) < target_acc


def _seed_demo_answers(con: duckdb.DuckDBPyConnection,
                       student_ids: list[str], now: str) -> int:
    qbs = _answerable_qbs(con)
    if not qbs:
        return 0
    aid = (con.execute("SELECT COALESCE(MAX(answer_id), 0) FROM student_answers").fetchone()[0]) + 1
    total = 0
    for idx, sid in enumerate(student_ids):
        acc = STUDENT_BASE_ACC[idx % len(STUDENT_BASE_ACC)]
        for qb in qbs:
            ok = _is_correct(sid, qb, acc)
            con.execute(
                "INSERT INTO student_answers "
                "(answer_id, student_id, question_id, paper_id, student_choice, is_correct, answered_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [aid, sid, str(qb), None, ("A" if ok else "X"), ok, now, "demo"],
            )
            aid += 1
            total += 1
    return total
