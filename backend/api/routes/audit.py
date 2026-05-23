"""GET /api/audit/findings — 跨源审计结果."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_audit_findings(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT audit_kind, severity, target, expected, actual, delta, note "
            "FROM audit_findings ORDER BY audit_kind, severity DESC"
        ))
    finally:
        con.close()


ROUTES = {"/api/audit/findings": api_audit_findings}
