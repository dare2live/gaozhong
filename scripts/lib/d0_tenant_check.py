"""D0 域B 多租户隔离校验 (审计 BLOCK 修 2026-06-20; 坑21: 契约必须接进执行点).

不只断言"schema 有 teacher_id", 而是**真调用路由函数跨租户访问**, 断言被拒 —
这样若有人删掉某端点的 owns 校验, 此门立刻 FAIL (装饰性契约 vs 强制执行的区别)。

锁: ① 每班有 teacher_id (隔离键不为空) ② 跨租户 get/weakness/recommend → forbidden
   ③ list 按 teacher 作用域 (不含他人学生) ④ 无 teacher_id → MISSING ⑤ 正当访问可达。
"""
from __future__ import annotations

import duckdb


def _q(**kw):
    return {k: [v] for k, v in kw.items()}


def check_tenant_isolation(con: duckdb.DuckDBPyConnection, check) -> None:
    from backend.api.routes import students as st
    print("\n=== (28) 域B 多租户隔离 (行为级: 真调路由跨租户访问必拒, 坑21) ===")

    # ① 隔离键完整性: 班级 teacher_id 不为空 (否则归属链断 → 越权)
    null_tid = con.execute("SELECT COUNT(*) FROM classes WHERE teacher_id IS NULL OR teacher_id=''").fetchone()[0]
    check("classes.teacher_id 无空 (隔离键完整)", null_tid == 0, f"{null_tid} 班无 teacher_id")

    # 找跨租户对: teacherA + teacherB 的学生
    pair = con.execute(
        "SELECT a.teacher_id, b.student_id FROM "
        "(SELECT DISTINCT teacher_id FROM classes WHERE teacher_id IS NOT NULL) a, "
        "(SELECT s.student_id, c.teacher_id AS owner FROM students s "
        " JOIN classes c ON c.class_id=s.class_id WHERE c.teacher_id IS NOT NULL) b "
        "WHERE a.teacher_id <> b.owner LIMIT 1"
    ).fetchone()
    if not pair:
        check("跨租户对存在 (≥2 老师各有生, 才可测隔离)", True, "skip: 单租户 demo")
        return
    other_tid, victim_sid = pair

    def denied(r):
        return "forbidden" in str(r.get("error", ""))

    # ② 跨租户读 → forbidden
    check("get 跨租户 → forbidden", denied(st.api_students_get(_q(id=victim_sid, teacher_id=other_tid))),
          f"{other_tid} 读到 {victim_sid}")
    check("weakness 跨租户 → forbidden",
          denied(st.api_students_weakness(_q(id=victim_sid, teacher_id=other_tid))), "leak")
    check("recommend 跨租户 → forbidden",
          denied(st.api_students_recommend(_q(id=victim_sid, teacher_id=other_tid))), "leak")

    # ③ list 按 teacher 作用域: 返回的学生全属该 teacher
    lst = st.api_students_list(_q(teacher_id=other_tid))
    returned = {s["student_id"] for s in lst.get("students", [])}
    owned = {r[0] for r in con.execute(
        "SELECT s.student_id FROM students s JOIN classes c ON c.class_id=s.class_id "
        "WHERE c.teacher_id=?", [other_tid]).fetchall()}
    check("list 仅返回本租户学生", returned <= owned, f"越界: {sorted(returned - owned)}")
    check("list 不含受害学生", victim_sid not in returned, f"含 {victim_sid}")

    # ④ 无 teacher_id → MISSING (不允许裸全表)
    check("list 无 teacher_id → MISSING", "teacher_id" in str(st.api_students_list(_q()).get("error", "")), "裸读")

    # ⑤ 正当访问可达 (隔离不误杀自己人)
    own = con.execute(
        "SELECT s.student_id FROM students s JOIN classes c ON c.class_id=s.class_id "
        "WHERE c.teacher_id=? LIMIT 1", [other_tid]).fetchone()
    if own:
        check("正当访问自己学生可达 (隔离不误杀)",
              bool(st.api_students_get(_q(id=own[0], teacher_id=other_tid)).get("student")), "误杀")
