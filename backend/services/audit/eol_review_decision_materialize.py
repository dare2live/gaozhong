"""Materialize completed EOL review worksheet rows into decision JSONL."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.contracts.eol_review_decisions import (
    default_decision_path,
    load_eol_review_decision_contract,
    validate_decisions,
    validate_worksheet_rows,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_worksheet_line_number"] = line_number
        rows.append(row)
    return rows


def _empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return not value
    return False


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _field_changed(row: dict[str, Any], field: str, current_field: str) -> bool:
    if field not in row:
        return False
    return _text(row.get(field)) != _text(row.get(current_field))


def _partial_decision_without_status(row: dict[str, Any]) -> bool:
    if not _empty(row.get("decision_status")):
        return False
    reviewer_fields = ["reviewer", "reviewed_at", "review_note", "review_status"]
    if any(not _empty(row.get(field)) for field in reviewer_fields):
        return True
    comparable_fields = [
        ("answer", "current_answer"),
        ("source_id", "current_source_id"),
        ("source_span", "current_source_span"),
    ]
    return any(_field_changed(row, field, current_field) for field, current_field in comparable_fields)


def _priority_buckets(findings: list[dict[str, Any]], priority: list[str]) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for finding in findings:
        code = str(finding.get("code") or "")
        bucket = code if code in priority else "other"
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return buckets


def _decision_from_worksheet_row(row: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    fields = []
    fields.extend(str(field) for field in contract.get("required_fields") or [])
    fields.extend(str(field) for field in contract.get("overlay_fields") or [])
    fields.extend(["review_note"])

    decision: dict[str, Any] = {}
    for field in dict.fromkeys(fields):
        if field in row and not _empty(row.get(field)):
            decision[field] = row[field]
    return decision


def materialize_review_decisions(
    *,
    year: int,
    worksheet_path: Path,
    output_path: Path | None = None,
    allow_empty: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    contract = load_eol_review_decision_contract()
    output = output_path or default_decision_path(year, contract)
    output_path_exists = output.exists()
    worksheet_path_exists = worksheet_path.exists()
    worksheet_rows = read_jsonl(worksheet_path)
    worksheet_findings = validate_worksheet_rows(worksheet_rows, contract=contract, expected_year=year)
    missing_worksheet_findings = []
    if not worksheet_path_exists:
        missing_worksheet_findings.append({
            "code": "review_worksheet_file_missing",
            "detail": str(worksheet_path),
        })
    partial_rows = [
        row for row in worksheet_rows
        if _partial_decision_without_status(row)
    ]
    partial_findings = [
        {
            "code": "review_worksheet_partial_decision_missing_status",
            "line": row.get("_worksheet_line_number") or index,
            "detail": "decision_status is required when reviewer fields are filled or answer/source fields changed",
        }
        for index, row in enumerate(partial_rows, start=1)
    ]
    completed_rows = [
        row for row in worksheet_rows
        if not _empty(row.get("decision_status"))
    ]
    decisions = [_decision_from_worksheet_row(row, contract) for row in completed_rows]
    findings = missing_worksheet_findings + worksheet_findings + partial_findings + validate_decisions(decisions, contract=contract)

    if not decisions and not allow_empty:
        findings.append({
            "code": "no_completed_review_decisions",
            "detail": "worksheet has no rows with decision_status",
        })
    if output_path_exists and not overwrite:
        findings.append({
            "code": "decision_output_exists",
            "detail": str(output),
        })
    priority = [str(code) for code in contract.get("materializer_priority_issue_codes") or []]
    priority_buckets = _priority_buckets(findings, priority)

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tool": "backend.services.audit.eol_review_decision_materialize",
        "year": year,
        "worksheet_path": str(worksheet_path),
        "output_path": str(output),
        "status": "fail" if findings else "pass",
        "summary": {
            "worksheet_path_exists": worksheet_path_exists,
            "output_path_exists": output_path_exists,
            "worksheet_rows": len(worksheet_rows),
            "worksheet_findings": len(worksheet_findings),
            "partial_rows": len(partial_rows),
            "completed_rows": len(completed_rows),
            "decision_rows": len(decisions),
            "findings": len(findings),
            "priority_buckets": priority_buckets,
        },
        "findings": findings,
        "decisions": decisions,
    }


def write_decisions(path: Path, decisions: list[dict[str, Any]], *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"decision output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in decisions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_manifest(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(report)
    payload.pop("decisions", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
