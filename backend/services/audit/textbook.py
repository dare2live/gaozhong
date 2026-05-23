"""教材 PDF page count + unit 切分召回 + 越纲词率."""
from __future__ import annotations

import duckdb

from ._common import finding


def audit_textbook_pages(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = con.execute(
        "SELECT version_key, volume_key, pdf_pages FROM textbooks"
    ).fetchall()
    bad = [(v, k, p) for v, k, p in rows if (p or 0) < 50]
    return [finding("textbook_pages", "FAIL" if bad else "OK",
                    target="textbooks.pdf_pages", expected="all > 50",
                    actual=f"{len(rows) - len(bad)}/{len(rows)} pass",
                    note=str(bad) if bad else None)]


def audit_textbook_units(con: duckdb.DuckDBPyConnection) -> list[dict]:
    per_vol = con.execute("""
        SELECT version_key, volume_key, COUNT(*) AS n_units
        FROM units GROUP BY version_key, volume_key
    """).fetchall()
    expected_total = 14 * 6
    actual_total = sum(n for _, _, n in per_vol)
    ratio = actual_total / expected_total
    sev = "OK" if ratio >= 0.75 else ("WARN" if ratio >= 0.5 else "FAIL")
    out = [finding("textbook_units", sev,
                   target="units.total",
                   expected=f"≈{expected_total} (14 × ~6)",
                   actual=str(actual_total), delta=str(actual_total - expected_total),
                   note=f"召回率 {ratio:.0%}")]
    short = [(v, k, n) for v, k, n in per_vol if n < 4]
    out.append(finding("textbook_units",
                       "FAIL" if any(n == 0 for _, _, n in short) else
                       ("WARN" if short else "OK"),
                       target="units.per_volume", expected="all >= 4",
                       actual=f"{len(per_vol) - len(short)}/{len(per_vol)} pass",
                       note=f"short_vols={short}" if short else None))
    total_vols = con.execute("SELECT COUNT(*) FROM textbooks").fetchone()[0]
    out.append(finding("textbook_units",
                       "WARN" if len(per_vol) < total_vols else "OK",
                       target="units.volume_coverage",
                       expected=str(total_vols), actual=str(len(per_vol)),
                       note=f"{total_vols - len(per_vol)} 册无任何 unit"))
    return out


def audit_vocab_curriculum_alignment(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """教材引入词 vs 课标 — 双指标: (1) extractor 召回 (validated rows),
    (2) 越纲率 (validated rows 内, 教材词 ∩ 课标)."""
    try:
        # 1) extractor 召回: validated/total (INNER JOIN units)
        raw_total = con.execute("SELECT COUNT(*) FROM unit_vocab_intro").fetchone()[0]
        valid_total = con.execute("""
            SELECT COUNT(*) FROM unit_vocab_intro v
            INNER JOIN units u
              ON u.version_key=v.version_key AND u.volume_key=v.volume_key AND u.unit_number=v.unit_number
        """).fetchone()[0]
        # 2) alignment 在 validated rows 上
        row = con.execute("""
            SELECT COUNT(DISTINCT v.word) AS total,
                   COUNT(DISTINCT CASE WHEN c.word IS NOT NULL THEN v.word END) AS in_cur,
                   COUNT(DISTINCT CASE WHEN c.word IS NULL THEN v.word END) AS out_cur
            FROM unit_vocab_intro v
            INNER JOIN units u
              ON u.version_key=v.version_key AND u.volume_key=v.volume_key AND u.unit_number=v.unit_number
            LEFT JOIN cefr_vocab c ON c.word = v.word
        """).fetchone()
    except duckdb.CatalogException:
        return []
    out = []
    if raw_total == 0:
        return [finding("vocab_alignment", "WARN",
                        target="unit_vocab_intro vs cefr_vocab",
                        expected="教材词总 > 0", actual="0",
                        note="STEP 2 第二刀未跑或 jsonl 空")]
    recall = valid_total / raw_total
    sev_r = "OK" if recall >= 0.7 else ("WARN" if recall >= 0.4 else "FAIL")
    out.append(finding("vocab_alignment", sev_r,
                       target="vocab extractor 召回 (validated/total)",
                       expected=">= 70%",
                       actual=f"{recall:.1%} ({valid_total}/{raw_total})",
                       note="extractor 误抽 lesson# 当 Unit#, 待 STEP 2 第三刀重写按 'UNIT N' 标头切"))
    total, in_cur, out_cur = row
    if total > 0:
        extra_ratio = out_cur / total
        sev_a = "OK" if extra_ratio <= 0.20 else ("WARN" if extra_ratio <= 0.40 else "FAIL")
        out.append(finding("vocab_alignment", sev_a,
                           target="教材引入词 ∩ 课标 (越纲率)",
                           expected="≤ 20% (课标 +200 词扩展), 容忍到 40%",
                           actual=f"{extra_ratio:.1%}",
                           note=f"total={total} in_cur={in_cur} extra={out_cur}"))
    return out
