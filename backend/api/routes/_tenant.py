"""域B 多租户作用域 helper (审计 BLOCK 修, 2026-06-20).

用户硬约束 + 设计§1.5 隔离铁律: 所有 per-student 端点必按 teacher_id 隔离 —
老师只见自己班级链(teachers ← classes ← students)下的学生。单一 helper 全端点共用,
不让任何端点各自实现 (避免漏一个=越权, 审计实证 inc6 只做了 1/7)。

注: 当前系统无 auth/session, teacher_id 由客户端传 (demo 阶段); 真上线需服务端鉴权派生 teacher_id,
此 helper 是隔离的**单一执行点**, 接入鉴权后只改 get_teacher 一处。

══ 多租户收口决策 (用户 2026-06-26): 多校/多教研员轨**止步于此** ══
- 当前定位 = **单教研员内网工具** (无需鉴权/枚举防护; 用户明确"不用管枚举的问题, 先有一个教研员就行")。
- 隔离骨架**保留不删** (owns_student/owns_class + 全 per-student 端点已走本 helper), 作未来多租户的**扩展接口**:
  接入登录/JWT 时唯一改动点 = get_teacher 改为从 server-side session 派生 (不再信 query 参数);
  owns_* 归属判定无需改 (已是 server 端 SQL 校验), 其余端点零改动 (单一执行点红利)。
- 未做 (刻意非遗漏): 登录/JWT/bcrypt · 跨租户枚举防护(IDOR) · Docker/HTTPS/nginx · 多租户压测。
  恢复多校轨从这几项起步; 见 docs/RESUME.md 交付裁决 ②③轨。
"""
from __future__ import annotations

MISSING = {"error": "missing ?teacher_id — 域B 多租户必须带作用域 (老师只见自己学生)"}
DENIED = {"error": "forbidden — 该资源不属于此 teacher_id (跨租户隔离)"}


def get_teacher(qs: dict) -> str | None:
    return (qs.get("teacher_id", [None]) or [None])[0]


def owns_student(con, teacher_id: str, student_id: str) -> bool:
    """学生是否在该老师的班级链下."""
    return con.execute(
        "SELECT 1 FROM students s JOIN classes c ON c.class_id = s.class_id "
        "WHERE s.student_id = ? AND c.teacher_id = ? LIMIT 1", [student_id, teacher_id]
    ).fetchone() is not None


def owns_class(con, teacher_id: str, class_id: str) -> bool:
    return con.execute(
        "SELECT 1 FROM classes WHERE class_id = ? AND teacher_id = ? LIMIT 1",
        [class_id, teacher_id]).fetchone() is not None
