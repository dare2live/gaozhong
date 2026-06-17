"""D0 EOL 真题 raw_question 完整性校验 (#8 防回归).

锁: (a) 无 900 硬截断 (compact 去 900 限后, len==900 = smoking gun);
    (b) 阅读/完形 raw_question 非空 (完形子题 sentinel 除外)。

check 由调用方传入 (data_accuracy_check.check)。只读。抽出避 data_accuracy_check god-module (Rule 8)。
"""
from __future__ import annotations

import duckdb

_EOL = "source_repo LIKE 'eol_xgkii%'"


def check_eol_integrity(con: duckdb.DuckDBPyConnection, check) -> None:
    n_900 = con.execute(
        f"SELECT COUNT(*) FROM exam_questions WHERE {_EOL} AND LENGTH(raw_question)=900"
    ).fetchone()[0]
    check("EOL raw_question 无 900 硬截断 (#8)", n_900 == 0, f"{n_900} 行 len==900")
    n_empty = con.execute(
        f"SELECT COUNT(*) FROM exam_questions WHERE {_EOL} AND "
        "(raw_question IS NULL OR (LENGTH(TRIM(raw_question))<10 AND raw_question NOT LIKE '%子题%'))"
    ).fetchone()[0]
    check("EOL raw_question 非空 (子题sentinel除外, #8)", n_empty == 0, f"{n_empty} 空")
