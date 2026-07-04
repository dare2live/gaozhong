"""D0 治理类零覆盖表补齐 (坑17: 全数据审计2026-07-04发现的零覆盖表, 非语义数据准确性,
而是"未审阅数据不能被当已验证消费"/"demo数据必须可与真实数据区分"这类治理契约).
"""
from __future__ import annotations

import duckdb


def check_ocr_fix_dictionary(con: duckdb.DuckDBPyConnection, check) -> None:
    """ocr_fix_dictionary(1627行候选纠错, reviewed_by全NULL): 此前D0/moth/audit_findings
    三处零覆盖。当前只读候选队列(无consumer写回exam_questions等), 锁"未审阅不能被消费"
    契约先于消费者出现存在, 防未来有人加lookup时忘记检查review状态导致真词被静默改错
    (表内含如'doing'→'dining' Levenshtein距离2的高风险候选)。"""
    print("\n=== (40) ocr_fix_dictionary 治理契约 (未审阅候选不得被消费) ===")
    n = con.execute("SELECT COUNT(*) FROM ocr_fix_dictionary").fetchone()[0]
    check("ocr_fix_dictionary 表存在且有候选 (只读候选队列)", n > 0, f"{n} 行")
    n_reviewed = con.execute(
        "SELECT COUNT(*) FROM ocr_fix_dictionary WHERE reviewed_by IS NOT NULL"
    ).fetchone()[0]
    check("reviewed_by 非NULL 的行(已人工审阅=可被消费) — 当前应=0, 表内容仍为纯候选未应用",
          n_reviewed == 0, f"{n_reviewed} 行已标审阅(若非0, 需确认新增consumer已检查审阅状态)")


def check_student_answers_demo_transparency(con: duckdb.DuckDBPyConnection, check) -> None:
    """student_answers(920行demo数据, 坑4修复后产物) source字段值域诚实性: 此前D0零覆盖
    (仅moth weakness-derived-no-orphan间接验证join支撑, 不校验本表自身)。当前100% demo
    诚实(已知坑4后状态), 锁 source∈{demo,real} 防未来混入真实作答但demo/real边界失守——
    这类回归当前任何断言都测不到(既有覆盖只测join关系, 不测source值域本身)。"""
    print("\n=== (41) student_answers source 字段诚实性 (demo/real 边界) ===")
    bad = con.execute(
        "SELECT COUNT(*) FROM student_answers WHERE source IS NULL OR source NOT IN ('demo', 'real')"
    ).fetchone()[0]
    check("student_answers.source ⊆ {demo,real} 且非NULL (demo/real边界透明, 防未来混淆)",
          bad == 0, f"{bad} 行 source 越界或缺失")
