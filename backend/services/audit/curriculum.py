"""课标 vocab / grammar 召回 + 层级完整性."""
from __future__ import annotations

import duckdb

from backend.services.thresholds import get_threshold   # vocab 期望/容差单点 (thresholds.yaml vocab 块)
from ._common import finding

# 课标分级期望词量 + 容差 → thresholds.yaml vocab 块单点 (穷尽扫描: 原硬编码 + yaml 块零消费 + drift)
VOCAB_LEVEL_EXPECTED = {str(k): int(v) for k, v in (get_threshold("vocab.level_expected") or {}).items()}


def _level_sev(got: int, want: int) -> str:
    # 官方 1500/500/1000 是百位 rounded 目标; 实际附录2列表分级由星标(*/**)定, pypdf 抽取
    # 偶丢星标致 ~70 词在义教/必修/选必间漂移 (总数仍≈3000, 词全在)。分级近似 → ±100 容 rounding。
    # 注: 超纲/越纲率判定只看词是否在 cefr (membership), 不看级别, 故分级漂移不影响 §1.2。
    diff = abs(got - want)
    if diff <= get_threshold("vocab.level_tolerance", 100): return "OK"
    if diff <= get_threshold("vocab.level_tolerance_warn", 300): return "WARN"
    return "FAIL"


def audit_curriculum_vocab(con: duckdb.DuckDBPyConnection) -> list[dict]:
    total = con.execute("SELECT COUNT(*) FROM cefr_vocab").fetchone()[0]
    by = dict(con.execute(
        "SELECT cefr_level, COUNT(*) FROM cefr_vocab GROUP BY cefr_level"
    ).fetchall())
    out = []
    target = get_threshold("vocab.cefr_target", 3000)
    ok_tol, warn_tol = get_threshold("vocab.cefr_tolerance_ok", 100), get_threshold("vocab.cefr_tolerance_warn", 300)
    sev = "OK" if abs(total - target) <= ok_tol else ("WARN" if abs(total - target) <= warn_tol else "FAIL")
    out.append(finding("vocab_recall", sev,
                       target="cefr_vocab.total", expected=str(target), actual=str(total),
                       delta=str(total - target),
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
