"""Shared helpers for audit package."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def finding(kind: str, severity: str, **kw) -> dict:
    return {"audit_kind": kind, "severity": severity, **kw}
