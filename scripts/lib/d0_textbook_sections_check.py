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


def check_textbook_unit_content(con: duckdb.DuckDBPyConnection, check) -> None:
    """D0: 高中单元内容直出 textbook_content.unit_content (基础库 textbook 页, 此前无D0覆盖).

    2026-07-09覆盖率审计后补: /api/unit/content 此前只有 endpoint_contract_check 兜底
    (不崩+required_keys存在), 无专门D0校验其output结构; 顺带补vocab_pos_distribution
    (backend/services/vocab_pos.py, Rule5高中/初中共享helper)的结构闭合校验。
    """
    print("\n=== (55) 高中单元内容直出 unit_content (基础库 textbook 页) ===")
    from backend.services.textbook_content import unit_content
    r = unit_content(con, "waiyan", "bixiu_1", 1)
    check("顶层结构闭合: version_key/volume_key/unit_number/knowledge/passages",
          all(k in r for k in ("version_key", "volume_key", "unit_number", "knowledge", "passages")),
          f"{sorted(r.keys())}")
    k = r["knowledge"]
    check("knowledge 五轴齐全: vocab/collocation/sentence_pattern/expression/grammar",
          all(a in k for a in ("vocab", "collocation", "sentence_pattern", "expression", "grammar")),
          f"{sorted(k.keys())}")
    check("vocab_n 与 vocab 列表长度一致 (无重算)", k["vocab_n"] == len(k["vocab"]), f"{k['vocab_n']} vs {len(k['vocab'])}")
    pd = k.get("vocab_pos_distribution")
    check("vocab_pos_distribution 结构闭合(by_pos/n_tagged/n_untagged/caveat)",
          isinstance(pd, dict) and all(kk in pd for kk in ("by_pos", "n_tagged", "n_untagged", "caveat")),
          f"{sorted(pd.keys()) if isinstance(pd, dict) else pd}")
    check("pos_distribution n_tagged+n_untagged == vocab_n (对账, 无漏词)",
          isinstance(pd, dict) and pd["n_tagged"] + pd["n_untagged"] == k["vocab_n"],
          f"{pd.get('n_tagged') if isinstance(pd, dict) else None}+{pd.get('n_untagged') if isinstance(pd, dict) else None} vs {k['vocab_n']}")
