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

# 多租户 demo (inc6): 2 老师各拥自己班级 — 演示 teacher_id 隔离 (老师A不可见老师B学生)。
DEMO_TEACHERS = [
    ("t-li",   "李老师", "沈阳市第二中学", "沈阳"),
    ("t-wang", "王老师", "沈阳市第二中学", "沈阳"),
]
DEMO_CLASS_A = "sy-no2-2024-g3-1"   # → 李老师
DEMO_CLASS_B = "sy-no2-2024-g3-2"   # → 王老师
DEMO_CLASSES = [
    (DEMO_CLASS_A, "t-li",   "沈阳市第二中学", "高三", "高三 1 班 (demo)"),
    (DEMO_CLASS_B, "t-wang", "沈阳市第二中学", "高三", "高三 2 班 (demo)"),
]
DEMO_STUDENTS = [
    ("sy-2024-001", "张明",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_A),
    ("sy-2024-002", "李华",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_A),
    ("sy-2024-003", "王芳",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_A),
    ("sy-2024-004", "刘洋",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_B),
    ("sy-2024-005", "陈静",  "沈阳市第二中学", "沈阳", "高三", DEMO_CLASS_B),
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
    con.execute("DELETE FROM teachers")
    for tid, name, school, city in DEMO_TEACHERS:        # inc6: 多租户老师
        con.execute("INSERT INTO teachers VALUES (?, ?, ?, ?, ?)", [tid, name, school, city, now])
    for cid, tid, school, grade, cname in DEMO_CLASSES:   # 班级归属老师 (teacher_id)
        con.execute("INSERT INTO classes VALUES (?, ?, ?, ?, ?, ?)", [cid, tid, school, grade, cname, now])
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
        "teachers": len(DEMO_TEACHERS), "classes": len(DEMO_CLASSES), "students": len(DEMO_STUDENTS),
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


# ====== 学生端最小闭环 (2026-07-06 数据关联设计审查批次6, 用户选定"最小闭环"方案) ======
# real学生走独立student_id(前端生成'real-'前缀), 不复用上面5个demo学生 — demo数据的
# determinism(哈希确定性正确率)不能被真实答题污染, source字段全程物理隔离(D0已锁'demo'/'real'二值)。

def _linked_qb_id(con: duckdb.DuckDBPyConnection, word: str) -> int | None:
    """给 /api/exercise/l1 词汇小测的某个词找一个weakness计算兼容的真题qb_id.

    坑: /api/exercise/l1 出的是合成词汇配对题(非question_bank真题, 没有qb_id), 但
    weakness._compute_one_student() 要求 student_answers.question_id 能直接 CAST 成 BIGINT
    并 JOIN question_bank.qb_id — 若存"word:xxx"这类concept_id字符串, CAST 会报错(非静默
    过滤, 会打断该学生全部弱点计算)。这里尽量找一道同时命中该词 tag 且有真考点边
    (tests_exam_point, 弱点计算真正依赖的边)的真题 qb_id 作为归属; 找不到就存 None(诚实,
    不硬凑归属), 那条答题不产生弱点信号 — 比伪造一个不相关的qb_id更符合"宁缺毋滥"。
    """
    row = con.execute(
        "SELECT qt.qb_id FROM question_tags qt "
        "JOIN question_bank qb ON qb.qb_id = qt.qb_id "
        "JOIN edges e ON e.src_id = 'question:' || qb.origin_ref AND e.relation = 'tests_exam_point' "
        "WHERE qt.tag_id = ? LIMIT 1",
        [f"word:{word}"],
    ).fetchone()
    return row[0] if row else None


def submit_real_answers(con: duckdb.DuckDBPyConnection, student_id: str, name: str,
                         city: str, answers: list[dict]) -> dict:
    """记录一次真实答题(source='real') + 触发该生弱点重算(recompute_one, 不动其他学生).

    answers: [{"word_concept": "word:xxx", "choice": "A", "is_correct": bool}, ...]
    (来自 /api/exercise/l1 每题的 evidence.word_concept 字段)。
    """
    from backend.services import weakness

    now = datetime.now(timezone.utc).isoformat()
    if not con.execute("SELECT 1 FROM students WHERE student_id = ?", [student_id]).fetchone():
        con.execute(
            "INSERT INTO students (student_id, name, school, city, grade, class_id, enroll_year, created_at, source) "
            "VALUES (?, ?, NULL, ?, NULL, NULL, NULL, ?, 'real')",
            [student_id, name or student_id, city, now],
        )
    aid = (con.execute("SELECT COALESCE(MAX(answer_id), 0) FROM student_answers").fetchone()[0]) + 1
    n_written = 0
    for a in answers:
        word = (a.get("word_concept") or "").removeprefix("word:")
        qb_id = _linked_qb_id(con, word) if word else None
        con.execute(
            "INSERT INTO student_answers "
            "(answer_id, student_id, question_id, paper_id, student_choice, is_correct, answered_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [aid, student_id, str(qb_id) if qb_id is not None else None, None,
             a.get("choice"), bool(a.get("is_correct")), now, "real"],
        )
        aid += 1
        n_written += 1
    wk = weakness.recompute_one(con, student_id)
    return {"student_id": student_id, "answers_recorded": n_written,
            "weakness_rows": wk.get("weakness_rows", 0)}
