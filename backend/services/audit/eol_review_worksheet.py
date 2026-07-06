"""Generate reviewer worksheets for EOL structured-draft backlog items."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.audit.eol_review_backlog import build_eol_review_backlog, default_draft_path, read_jsonl
from backend.services.contracts.eol_review_decisions import load_eol_review_decision_contract


def _draft_rows_by_key(rows: list[dict[str, Any]], key_fields: list[str]) -> dict[tuple[str, ...], dict[str, Any]]:
    result: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(str(row.get(field) or "").strip() for field in key_fields)
        result[key] = row
    return result


def _identity_key(identity: dict[str, Any], key_fields: list[str]) -> tuple[str, ...]:
    return tuple(str(identity.get(field) or "").strip() for field in key_fields)


def _decision_contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "allowed_decision_statuses": list(contract.get("allowed_decision_statuses") or []),
        "required_fields": list(contract.get("required_fields") or []),
        "import_ready_required_fields": list(contract.get("import_ready_required_fields") or []),
        "non_import_ready_required_fields": list(contract.get("non_import_ready_required_fields") or []),
        "status_guidance": {
            "import_ready": "Use only after answer, source_id, and source_span have been checked against the source artifact.",
            "needs_followup": "Use when the item still needs evidence or human review; review_note is required.",
            "rejected": "Use when this draft row should not be imported; review_note is required.",
            "rescope": "Use when the row belongs outside the current import scope; review_note is required.",
        },
    }


def _build_worksheet_row(
    item: dict[str, Any],
    draft_rows: dict[tuple[str, ...], dict[str, Any]],
    key_fields: list[str],
    contract_summary: dict[str, Any],
) -> dict[str, Any] | None:
    identity = item.get("identity") or {}
    if "decision_path" in identity:
        return None
    source_row = draft_rows.get(_identity_key(identity, key_fields), {})
    issue_codes = [issue["code"] for issue in item.get("issues") or []]
    return {
        "worksheet_kind": "eol_review_decision_template",
        "year": identity.get("year"),
        "paper_type": source_row.get("paper_type") or identity.get("paper_type"),
        "observed_question_number": identity.get("observed_question_number"),
        "question_type": identity.get("question_type"),
        "backlog_issue_codes": issue_codes,
        "backlog_issue_details": item.get("issues") or [],
        "current_review_status": identity.get("review_status"),
        "current_answer": source_row.get("answer"),
        "current_source_id": source_row.get("source_id"),
        "current_source_span": source_row.get("source_span"),
        "stem_preview": source_row.get("stem_preview"),
        "source_file": source_row.get("source_file"),
        "decision_contract": contract_summary,
        "decision_status": "",
        "reviewer": "",
        "reviewed_at": "",
        "answer": source_row.get("answer") or "",
        "source_id": source_row.get("source_id") or "",
        "source_span": source_row.get("source_span") or "",
        "review_status": "",
        "review_note": "",
    }


def build_eol_review_worksheet(
    year: int,
    draft_path: Path | None = None,
    decision_path: Path | None = None,
) -> dict[str, Any]:
    """Build a worksheet JSONL payload for unresolved EOL review backlog items."""
    path = draft_path or default_draft_path(year)
    decision_contract = load_eol_review_decision_contract()
    key_fields = [str(field) for field in decision_contract.get("key_fields") or []]
    contract_summary = _decision_contract_summary(decision_contract)
    draft_rows = _draft_rows_by_key(read_jsonl(path), key_fields)
    backlog_report = build_eol_review_backlog(year, path, decision_path)

    worksheet_rows: list[dict[str, Any]] = []
    for item in backlog_report["backlog"]:
        row = _build_worksheet_row(item, draft_rows, key_fields, contract_summary)
        if row is not None:
            worksheet_rows.append(row)

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tool": "backend.services.audit.eol_review_worksheet",
        "year": year,
        "draft_path": str(path),
        "decision_path": backlog_report.get("decision_path"),
        "decision_contract": contract_summary,
        "backlog_status": backlog_report.get("status"),
        "summary": {
            "backlog_items": backlog_report["summary"]["backlog_items"],
            "worksheet_rows": len(worksheet_rows),
            "skipped_decision_file_issues": backlog_report["summary"].get("decision_findings", 0),
        },
        "rows": worksheet_rows,
    }


def write_worksheet_jsonl(path: Path, worksheet: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in worksheet["rows"]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_worksheet_manifest(path: Path, worksheet: dict[str, Any], worksheet_jsonl_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(worksheet)
    payload["worksheet_jsonl_path"] = str(worksheet_jsonl_path)
    payload.pop("rows", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
