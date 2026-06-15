"""Audit how official EOL review decisions cover the current draft/backlog."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.audit.eol_review_backlog import (
    build_eol_review_backlog,
    default_draft_path,
    read_jsonl,
)
from backend.services.contracts.eol_review_decisions import (
    decision_key,
    default_decision_path,
    load_eol_review_decision_contract,
    read_decisions,
    validate_decisions,
)


def _key_set(rows: list[dict[str, Any]], contract: dict[str, Any]) -> set[tuple[str, ...]]:
    return {decision_key(row, contract) for row in rows}


def build_eol_review_decision_coverage(
    year: int,
    draft_path: Path | None = None,
    decision_path: Path | None = None,
) -> dict[str, Any]:
    contract = load_eol_review_decision_contract()
    draft = draft_path or default_draft_path(year)
    decisions_file = decision_path or default_decision_path(year, contract)
    decision_path_exists = decisions_file.exists()
    draft_rows = read_jsonl(draft)
    decisions = read_decisions(decisions_file)
    decision_findings = validate_decisions(decisions, contract=contract)

    draft_keys = _key_set(draft_rows, contract)
    decision_keys = _key_set(decisions, contract)
    matched_keys = sorted(draft_keys & decision_keys)
    unmatched_decision_keys = sorted(decision_keys - draft_keys)
    undecided_draft_keys = sorted(draft_keys - decision_keys)
    backlog_report = build_eol_review_backlog(year, draft, decisions_file)

    findings: list[dict[str, Any]] = []
    if not decision_path_exists:
        findings.append({
            "code": "review_decision_file_missing",
            "detail": str(decisions_file),
        })
    for finding in decision_findings:
        findings.append({"code": finding["code"], "detail": finding.get("detail"), "line": finding.get("line")})
    for key in unmatched_decision_keys:
        findings.append({
            "code": "unmatched_review_decision_key",
            "detail": list(key),
        })

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tool": "backend.services.audit.eol_review_decision_coverage",
        "year": year,
        "draft_path": str(draft),
        "decision_path": str(decisions_file),
        "status": "fail" if findings or backlog_report["status"] != "pass" else "pass",
        "summary": {
            "draft_rows": len(draft_rows),
            "decision_path_exists": decision_path_exists,
            "decision_rows": len(decisions),
            "matched_decisions": len(matched_keys),
            "unmatched_decisions": len(unmatched_decision_keys),
            "undecided_draft_rows": len(undecided_draft_keys),
            "decision_findings": len(decision_findings),
            "remaining_backlog_items": backlog_report["summary"]["backlog_items"],
        },
        "findings": findings,
        "matched_decision_keys": [list(key) for key in matched_keys],
        "unmatched_decision_keys": [list(key) for key in unmatched_decision_keys],
        "undecided_draft_keys": [list(key) for key in undecided_draft_keys],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
