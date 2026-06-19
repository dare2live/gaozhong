"""D0 local_pdf 真题全文完整性校验 (从 data_accuracy_check 抽出, 避 god-module Rule 8).

修复缺陷: 2025/2024 阅读理解 raw_question 硬截 2000 丢后段小题 + answer 空。
锁三维度防回归: 无硬截断 / 客观题答案已填 / 题干无卷尾附录污染。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import duckdb

# 有客观答案键的题型 (写作 应用文/续写 无单一答案, 不强求 answer)
_OBJECTIVE_QTYPES = ("阅读理解", "完形填空", "完形填空(七选五/语篇)", "语法填空")


def check_local_pdf_integrity(con: duckdb.DuckDBPyConnection, check) -> None:
    """local_pdf 题干完整性 3 项 D0 校验 (新数据落地必入强校验, 坑17)."""
    print("\n=== (21e) local_pdf 真题全文完整性 (2025/2024 截断+空答案缺陷防回归) ===")
    trunc = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE source_repo='local_pdf' "
        "AND LENGTH(raw_question)=2000"
    ).fetchone()[0]
    qmarks = ",".join("?" * len(_OBJECTIVE_QTYPES))
    noans = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE source_repo='local_pdf' "
        f"AND question_type IN ({qmarks}) AND COALESCE(TRIM(answer),'')=''",
        list(_OBJECTIVE_QTYPES),
    ).fetchone()[0]
    polluted = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE source_repo='local_pdf' AND ("
        "raw_question LIKE '%英语听力%' OR raw_question LIKE '%参考答案%' "
        "OR raw_question LIKE '%绝密★启用前%' OR raw_question LIKE '%普通高等学校招生%')"
    ).fetchone()[0]
    check("local_pdf 题干无硬截断(len=2000)", trunc == 0, f"{trunc} 行")
    check("local_pdf 阅读/完形/语法 answer 已填", noans == 0, f"{noans} 行空答案")
    check("local_pdf 题干无卷尾附录污染", polluted == 0, f"{polluted} 行")
    # B1 (强验证 wf_9d0ef21a): 2024/2025 辽宁卷 local_pdf 权威, GAOKAO-Bench 同卷重复已 supersede。
    dup = con.execute(
        "SELECT year, COUNT(*) FROM exam_questions WHERE year IN (2024, 2025) "
        "AND province LIKE '辽宁%' AND source_repo <> 'local_pdf' GROUP BY year"
    ).fetchall()
    check("2024/2025 辽宁卷无 GAOKAO-Bench 重复(local_pdf 单一权威)", not dup,
          f"{dup} (gbu 同卷未 supersede)" if dup else "0 重复")
