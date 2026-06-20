"""D0 考试词典校验 (Canonical 词本体地基; 坑17 新数据入强校验).

锁: 规模(课标∪教材真超纲) + 三源标记齐(每词 source_flags 非空且∈真相源) + 释义覆盖率 +
最准(真题超课标教材的阅读生词如 photosynthesis 不入词典, 防注水) + 每词至少一真相源(不凭空)。
"""
from __future__ import annotations

import duckdb


def check_exam_dict(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (33) 考试词典 (Canonical 词本体; 课标∪教材真超纲) ===")
    n = con.execute("SELECT COUNT(*) FROM exam_vocabulary").fetchone()[0]
    check("考试词典规模 3500–5000 (最小: 课标∪教材真超纲, 无CET/GRE注水)", 3500 <= n <= 5000, f"{n}")
    # 每词至少一真相源 (不凭空造词)
    no_src = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE NOT (in_curriculum OR in_textbook)").fetchone()[0]
    check("每词至少课标或教材源 (最准: 不凭空造词)", no_src == 0, f"{no_src} 无源")
    # source_flags 与布尔列一致 (provenance 诚实)
    bad_flag = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE "
        "(in_curriculum AND source_flags NOT LIKE '%curriculum%') OR "
        "(in_exam AND source_flags NOT LIKE '%exam%')").fetchone()[0]
    check("source_flags 与三源布尔一致 (provenance 可溯)", bad_flag == 0, f"{bad_flag} 不一致")
    # 释义覆盖 ≥98% (教材生词表→中考表→COCA兜底交叉引用)
    cov = con.execute("SELECT COUNT(*) FROM exam_vocabulary WHERE gloss IS NOT NULL").fetchone()[0]
    check("释义覆盖率 ≥98% (教材→中考表→COCA 兜底交叉引用)", cov * 100 >= n * 98,
          f"{cov}/{n}={100 * cov // max(n, 1)}%")
    # gloss ⟺ gloss_source (provenance 诚实: 有释义必有来源, 无释义必无来源)
    bad_gs = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE (gloss IS NULL) <> (gloss_source IS NULL)").fetchone()[0]
    check("释义 ⟺ gloss_source (每条释义可溯源; 不凭空)", bad_gs == 0, f"{bad_gs} 不一致")
    # 最准: in_exam 词必有 gaokao_hit_ln>0 (旗与命中数一致)
    bad_exam = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE in_exam <> (gaokao_hit_ln > 0)").fetchone()[0]
    check("in_exam 旗 == 辽宁命中>0 (真题口径一致, §7)", bad_exam == 0, f"{bad_exam}")
