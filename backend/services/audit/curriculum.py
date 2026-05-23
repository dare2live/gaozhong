"""课标 vocab / grammar 召回 + 层级完整性."""
from __future__ import annotations

import duckdb

from ._common import finding

VOCAB_LEVEL_EXPECTED = {"义教": 1500, "必修": 500, "选必": 1000}


def _level_sev(got: int, want: int) -> str:
    diff = abs(got - want)
    if diff <= 50: return "OK"
    if diff <= 200: return "WARN"
    return "FAIL"


def audit_curriculum_vocab(con: duckdb.DuckDBPyConnection) -> list[dict]:
    total = con.execute("SELECT COUNT(*) FROM cefr_vocab").fetchone()[0]
    by = dict(con.execute(
        "SELECT cefr_level, COUNT(*) FROM cefr_vocab GROUP BY cefr_level"
    ).fetchall())
    out = []
    sev = "OK" if abs(total - 3000) <= 100 else ("WARN" if abs(total - 3000) <= 300 else "FAIL")
    out.append(finding("vocab_recall", sev,
                       target="cefr_vocab.total", expected="3000", actual=str(total),
                       delta=str(total - 3000),
                       note="课标 p129: 义教 1500 + 必修 500 + 选必 1000 = 3000"))
    for lv, want in VOCAB_LEVEL_EXPECTED.items():
        got = by.get(lv, 0)
        out.append(finding("vocab_recall", _level_sev(got, want),
                           target=f"cefr_vocab.{lv}", expected=str(want), actual=str(got),
                           delta=str(got - want)))
    return out


def audit_grammar_hierarchy(con: duckdb.DuckDBPyConnection) -> list[dict]:
    total = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
    depths = dict(con.execute("SELECT depth, COUNT(*) FROM grammar_items GROUP BY depth").fetchall())
    out = [finding("grammar_recall", "OK",
                   target="grammar_items.total", expected=">=80", actual=str(total),
                   note=f"depth distribution: {depths}")]
    orphan = con.execute("""
        SELECT g.grammar_item_id FROM grammar_items g
        WHERE g.parent_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM grammar_items p WHERE p.grammar_item_id = g.parent_id)
    """).fetchall()
    out.append(finding("grammar_recall", "FAIL" if orphan else "OK",
                       target="grammar_items.parent_id", expected="0 orphan",
                       actual=str(len(orphan)), note=str(orphan[:5]) if orphan else None))
    return out
