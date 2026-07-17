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
    # 坑18 续: 页中水印 bleed (锦宏/学科网 mock-PDF 每页页脚注入公众号/客服/页码, mid-passage 污染题干)
    watermark = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE source_repo='local_pdf' AND ("
        "raw_question LIKE '%锦宏教育%' OR raw_question LIKE '%学科 网（北 京）%' "
        "OR regexp_matches(raw_question, '第\\s*\\d+\\s*页\\s*/\\s*共\\s*\\d+\\s*页'))"
    ).fetchone()[0]
    check("local_pdf 题干无硬截断(len=2000)", trunc == 0, f"{trunc} 行")
    check("local_pdf 阅读/完形/语法 answer 已填", noans == 0, f"{noans} 行空答案")
    check("local_pdf 题干无卷尾附录污染", polluted == 0, f"{polluted} 行")
    check("local_pdf 题干无页中水印bleed(锦宏/学科网/页码, 坑18)", watermark == 0, f"{watermark} 行残留水印")
    # B1: 2024/2025 客观卷面以 local_pdf 为权威; GAOKAO-Bench/gbu 同卷不得残留。
    # listening_stems_xgkii = 听力题干补齐(另源), 非 Bench 重复, 豁免。
    _ok_extra = ("listening_stems_xgkii",)
    placeholders = ",".join("?" * len(_ok_extra))
    dup = con.execute(
        "SELECT year, COUNT(*) FROM exam_questions WHERE year IN (2024, 2025) "
        "AND province LIKE '辽宁%' AND source_repo <> 'local_pdf' "
        f"AND source_repo NOT IN ({placeholders}) GROUP BY year",
        list(_ok_extra),
    ).fetchall()
    check("2024/2025 辽宁卷无 GAOKAO-Bench 重复(local_pdf 单一权威)", not dup,
          f"{dup} (gbu 同卷未 supersede)" if dup else "0 重复")
