"""File SHA-256 vs file_manifest table."""
from __future__ import annotations

import duckdb

from ._common import ROOT, finding, sha256


def audit_file_sha(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = con.execute("SELECT rel_path, sha256, size_bytes FROM file_manifest").fetchall()
    bad = []
    for rel, sha, _ in rows:
        p = ROOT / rel
        if not p.exists():
            bad.append(finding("file_sha", "FAIL", target=rel, expected=sha, actual="MISSING"))
        elif sha256(p) != sha:
            bad.append(finding("file_sha", "FAIL", target=rel, expected=sha, actual=sha256(p)))
    bad.append(finding("file_sha", "OK",
                       target="*", expected=str(len(rows)),
                       actual=str(len(rows) - len([b for b in bad if b["severity"] == "FAIL"])),
                       note=f"全核 {len(rows)} 个 manifest 行"))
    return bad
