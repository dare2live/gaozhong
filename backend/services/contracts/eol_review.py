"""Shared EOL review-rule loader and validator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RULES_PATH = ROOT / "backend" / "config" / "eol_review_rules.yaml"

KNOWN_REVIEW_BACKLOG_ISSUE_CODES = {
    "draft_missing",
    "duplicate_review_decision_key",
    "unmatched_review_decision_key",
    "required_field_missing",
    "review_decision_import_ready_field_missing",
    "review_decision_non_import_ready_field_missing",
    "review_decision_required_field_missing",
    "review_decision_status_unknown",
    "review_status_blocked",
    "source_span_missing",
    "listening_answer_missing",
    "answer_required_but_missing",
}


def load_eol_review_rules(path: Path | None = None) -> dict[str, Any]:
    source = path or DEFAULT_RULES_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    return raw.get("eol_review_backlog") or {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _validate_token_list(
    findings: list[dict[str, str]],
    rules: dict[str, Any],
    field: str,
    *,
    required: bool,
) -> None:
    values = _as_list(rules.get(field))
    if required and not values:
        findings.append({
            "code": "eol_review_rule_list_missing",
            "target": field,
            "detail": "required token list is missing or empty",
        })
        return
    for index, value in enumerate(values):
        if not str(value).strip():
            findings.append({
                "code": "eol_review_rule_empty_token",
                "target": f"{field}[{index}]",
                "detail": "tokens cannot be empty",
            })


def validate_eol_review_rules(path: Path | None = None) -> list[dict[str, str]]:
    rules = load_eol_review_rules(path)
    findings: list[dict[str, str]] = []

    if not rules:
        return [{
            "code": "eol_review_rules_missing",
            "target": "eol_review_backlog",
            "detail": "backend/config/eol_review_rules.yaml must define eol_review_backlog",
        }]

    _validate_token_list(findings, rules, "required_fields", required=True)
    _validate_token_list(findings, rules, "blocking_review_status_tokens", required=True)
    _validate_token_list(findings, rules, "allowed_empty_answer_question_type_tokens", required=False)
    _validate_token_list(findings, rules, "answer_required_question_type_tokens", required=True)
    _validate_token_list(findings, rules, "priority_issue_codes", required=False)

    for code in _as_list(rules.get("priority_issue_codes")):
        issue_code = str(code).strip()
        if issue_code and issue_code not in KNOWN_REVIEW_BACKLOG_ISSUE_CODES:
            findings.append({
                "code": "eol_review_priority_issue_unknown",
                "target": issue_code,
                "detail": "priority issue code is not emitted by eol_review_backlog",
            })

    return findings
