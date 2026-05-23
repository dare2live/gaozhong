"""课标 vs 外部 word list (mahavivo Highschool) cross-check."""
from __future__ import annotations

import duckdb

from ._common import ROOT, finding


def audit_cross_source_vocab(con: duckdb.DuckDBPyConnection) -> list[dict]:
    cefr = {row[0] for row in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    mh_path = ROOT / "data/structured/english-wordlists/Highschool_edited.txt"
    if not mh_path.exists():
        return [finding("cross_source", "WARN", target="mahavivo.Highschool_edited",
                        actual="MISSING", note="mahavivo 词表未入仓")]
    mh = {ln.strip().lower() for ln in mh_path.read_text(encoding="utf-8").splitlines()
          if ln.strip() and ln.strip()[0].isalpha()}
    inter = cefr & mh
    cov = len(inter) / max(1, min(len(cefr), len(mh)))
    sev = "OK" if cov >= 0.6 else ("WARN" if cov >= 0.4 else "FAIL")
    return [
        finding("cross_source", "OK", target="cefr ∩ mahavivo",
                expected="≥60% of min(|cefr|,|mh|)", actual=str(len(inter)),
                note=f"|cefr|={len(cefr)} |mh|={len(mh)} "
                     f"only_cefr={len(cefr - mh)} only_mh={len(mh - cefr)}"),
        finding("cross_source", sev, target="cefr_vs_mahavivo_coverage",
                expected=">=0.6", actual=f"{cov:.3f}"),
    ]
