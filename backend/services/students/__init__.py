"""学生档案 service — demo 数据灌库 (5.6, init_db 灌 1 班 5 学生)."""
from __future__ import annotations

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

# demo 弱点 (5 学生各 3 弱点, 关联到课程 materials 真实词)
DEMO_WEAKNESS = [
    ("sy-2024-001", "word:academic", 0.85, 12),
    ("sy-2024-001", "word:abandon",  0.72, 10),
    ("sy-2024-001", "word:access",   0.68, 11),
    ("sy-2024-002", "word:astonish", 0.78, 9),
    ("sy-2024-002", "word:civil",    0.65, 8),
    ("sy-2024-003", "grammar:三/10/(1)", 0.81, 14),
    ("sy-2024-003", "grammar:三/14",      0.74, 11),
    ("sy-2024-004", "word:debate",   0.79, 10),
    ("sy-2024-004", "word:creature", 0.66, 7),
    ("sy-2024-005", "word:advocate", 0.83, 13),
    ("sy-2024-005", "grammar:三/13", 0.71, 9),
]


def seed_demo(con: duckdb.DuckDBPyConnection) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    con.execute("DELETE FROM student_weakness")
    con.execute("DELETE FROM students")
    con.execute("DELETE FROM classes")
    # 班级
    con.execute(
        "INSERT INTO classes VALUES (?, ?, ?, ?, ?, ?)",
        [DEMO_CLASS_ID, None, "沈阳市第二中学", "高三", "高三 1 班 (demo)", now],
    )
    # 学生
    for sid, name, school, city, grade, cid in DEMO_STUDENTS:
        con.execute(
            "INSERT INTO students "
            "(student_id, name, school, city, grade, class_id, enroll_year, created_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [sid, name, school, city, grade, cid, 2022, now, "demo"],
        )
    # 弱点
    for sid, concept, score, n in DEMO_WEAKNESS:
        con.execute(
            "INSERT INTO student_weakness "
            "(student_id, concept_id, weakness_score, sample_n, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [sid, concept, score, n, now],
        )
    return {
        "classes": 1, "students": len(DEMO_STUDENTS),
        "weakness_rows": len(DEMO_WEAKNESS),
    }
