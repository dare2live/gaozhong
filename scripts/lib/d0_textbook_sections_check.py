"""D0 教材 section 边界 + section_text 完整性 (issue #9 单元边界过宽 / #7 raw_text 截断).

从 data_accuracy_check 抽出统一为 lib 委托 (避 god-module Rule8; check 由调用方传入)。
(a) 无 section span>25 (末单元不吞 back-matter); (b) n_chars==LENGTH(raw_text) 无截断;
(c) section_text 无书末锚点污染 (Communication bank/Appendices/参考答案/English glossary)。
"""
from __future__ import annotations

import duckdb


def check_textbook_sections(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (26) 教材 section 边界 + section_text 完整性 ===")
    wide = con.execute(
        "SELECT version_key, volume_key, unit_number, seq, (page_end-page_start) AS span "
        "FROM sections WHERE (page_end-page_start) > 25 ORDER BY span DESC"
    ).fetchall()
    check("无 section span>25 (单元边界收口)", not wide,
          "0" if not wide else f"{len(wide)} 过宽: {[(r[0], r[1], r[2], r[4]) for r in wide[:5]]}")
    n_trunc = con.execute(
        "SELECT COUNT(*) FROM section_text WHERE n_chars <> LENGTH(raw_text)").fetchone()[0]
    check("section_text n_chars==LENGTH(raw_text) 全表 (无截断)", n_trunc == 0, f"{n_trunc} 不一致")
    n_pollute = con.execute(
        "SELECT COUNT(*) FROM section_text "
        "WHERE raw_text ILIKE '%Communication bank%' OR raw_text ILIKE '%Appendices%' "
        "OR raw_text LIKE '%参考答案%' OR raw_text ILIKE '%English glossary%'"
    ).fetchone()[0]
    check("section_text 无 back-matter 污染", n_pollute == 0, f"{n_pollute} 含书末锚点")
