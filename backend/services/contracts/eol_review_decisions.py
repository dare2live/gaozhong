"""Shared EOL review-decision overlay loader and validator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from backend.services.data_sources.registry import load_registry

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = ROOT / "backend" / "config" / "eol_review_decisions.yaml"

KNOWN_MATERIALIZER_ISSUE_CODES = {
    "review_worksheet_file_missing",
    "review_worksheet_required_field_missing",
    "review_worksheet_kind_unknown",
    "review_worksheet_year_mismatch",
    "review_worksheet_partial_decision_missing_status",
    "no_completed_review_decisions",
    "decision_output_exists",
    "duplicate_review_decision_key",
    "review_decision_status_unknown",
    "review_decision_required_field_missing",
    "review_decision_import_ready_field_missing",
    "review_decision_non_import_ready_field_missing",
    "review_decision_source_unknown",
    "review_decision_source_family_disallowed",
}


def load_eol_review_decision_contract(path: Path | None = None) -> dict[str, Any]:
    source = path or DEFAULT_CONFIG_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    return raw.get("eol_review_decisions") or {}


def default_decision_path(year: int, contract: dict[str, Any] | None = None) -> Path:
    rules = contract or load_eol_review_decision_contract()
    directory = ROOT / str(rules.get("decision_dir") or "data/external/exam_sources/eol/review_decisions")
    template = str(rules.get("decision_file_template") or "{year}_xgkii_english_eol_review_decisions.jsonl")
    return directory / template.format(year=year)


def read_decisions(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_decision_line_number"] = line_number
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


def _fallback_key_value(field: str, row: dict[str, Any], contract: dict[str, Any]) -> str:
    fallback_rules = contract.get("key_field_fallbacks") or {}
    field_rules = fallback_rules.get(field) or {}
    question_type = str(row.get("question_type") or "").strip()
    value = field_rules.get(question_type)
    return "" if value is None else str(value).strip()


def decision_key(row: dict[str, Any], contract: dict[str, Any] | None = None) -> tuple[str, ...]:
    rules = contract or load_eol_review_decision_contract()
    values = []
    for field in rules.get("key_fields") or []:
        field_name = str(field)
        value = str(row.get(field_name) or "").strip()
        if not value:
            value = _fallback_key_value(field_name, row, rules)
        values.append(value)
    return tuple(values)


def validate_decision_contract(path: Path | None = None) -> list[dict[str, str]]:
    rules = load_eol_review_decision_contract(path)
    findings: list[dict[str, str]] = []
    required_lists = [
        "key_fields",
        "required_fields",
        "worksheet_required_fields",
        "materializer_priority_issue_codes",
        "allowed_decision_source_families",
        "allowed_decision_statuses",
        "import_ready_required_fields",
        "non_import_ready_required_fields",
        "overlay_fields",
    ]
    if not rules:
        return [{
            "code": "eol_review_decision_contract_missing",
            "target": "eol_review_decisions",
            "detail": "backend/config/eol_review_decisions.yaml must define eol_review_decisions",
        }]
    for field in required_lists:
        values = rules.get(field) or []
        if not isinstance(values, list) or not values:
            findings.append({
                "code": "eol_review_decision_contract_list_missing",
                "target": field,
                "detail": "required decision contract list is missing or empty",
            })
            continue
        for index, value in enumerate(values):
            if not str(value).strip():
                findings.append({
                    "code": "eol_review_decision_contract_empty_token",
                    "target": f"{field}[{index}]",
                    "detail": "tokens cannot be empty",
                })
    if not str(rules.get("decision_dir") or "").strip():
        findings.append({
            "code": "eol_review_decision_dir_missing",
            "target": "decision_dir",
            "detail": "decision_dir must be configured",
        })
    if not str(rules.get("decision_file_template") or "").strip():
        findings.append({
            "code": "eol_review_decision_file_template_missing",
            "target": "decision_file_template",
            "detail": "decision_file_template must be configured",
        })
    key_fields = {str(field) for field in rules.get("key_fields") or []}
    fallback_rules = rules.get("key_field_fallbacks") or {}
    if not isinstance(fallback_rules, dict):
        findings.append({
            "code": "eol_review_decision_key_fallbacks_invalid",
            "target": "key_field_fallbacks",
            "detail": "key_field_fallbacks must be a mapping",
        })
    else:
        for field, question_type_map in fallback_rules.items():
            field_name = str(field).strip()
            if field_name not in key_fields:
                findings.append({
                    "code": "eol_review_decision_key_fallback_field_unknown",
                    "target": field_name,
                    "detail": "fallback field must be listed in key_fields",
                })
            if not isinstance(question_type_map, dict) or not question_type_map:
                findings.append({
                    "code": "eol_review_decision_key_fallback_map_missing",
                    "target": field_name,
                    "detail": "fallback field must define question_type -> fallback key values",
                })
                continue
            for question_type, fallback_value in question_type_map.items():
                if not str(question_type).strip() or not str(fallback_value).strip():
                    findings.append({
                        "code": "eol_review_decision_key_fallback_empty",
                        "target": f"{field_name}.{question_type}",
                        "detail": "fallback question_type and value must be non-empty",
                    })
    for code in rules.get("materializer_priority_issue_codes") or []:
        issue_code = str(code).strip()
        if issue_code and issue_code not in KNOWN_MATERIALIZER_ISSUE_CODES:
            findings.append({
                "code": "eol_review_decision_materializer_issue_unknown",
                "target": issue_code,
                "detail": "materializer priority issue code is not emitted by decision materialization",
            })
    return findings


def validate_worksheet_rows(
    worksheet_rows: list[dict[str, Any]],
    *,
    contract: dict[str, Any] | None = None,
    expected_year: int | None = None,
) -> list[dict[str, Any]]:
    rules = contract or load_eol_review_decision_contract()
    findings: list[dict[str, Any]] = []
    required_fields = [str(item) for item in rules.get("worksheet_required_fields") or []]

    for index, row in enumerate(worksheet_rows, start=1):
        line = row.get("_worksheet_line_number") or index
        for field in required_fields:
            if _empty(row.get(field)):
                findings.append({
                    "code": "review_worksheet_required_field_missing",
                    "line": line,
                    "detail": field,
                })
        kind = str(row.get("worksheet_kind") or "").strip()
        if kind and kind != "eol_review_decision_template":
            findings.append({
                "code": "review_worksheet_kind_unknown",
                "line": line,
                "detail": kind,
            })
        if expected_year is not None and str(row.get("year") or "").strip() != str(expected_year):
            findings.append({
                "code": "review_worksheet_year_mismatch",
                "line": line,
                "detail": f"expected {expected_year}, got {row.get('year')}",
            })
    return findings


def validate_decisions(
    decisions: list[dict[str, Any]],
    *,
    contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rules = contract or load_eol_review_decision_contract()
    findings: list[dict[str, Any]] = []
    allowed_statuses = {str(item) for item in rules.get("allowed_decision_statuses") or []}
    allowed_source_families = {str(item) for item in rules.get("allowed_decision_source_families") or []}
    required_fields = [str(item) for item in rules.get("required_fields") or []]
    import_ready_required = [str(item) for item in rules.get("import_ready_required_fields") or []]
    non_import_ready_required = [str(item) for item in rules.get("non_import_ready_required_fields") or []]
    source_registry = load_registry()
    seen: dict[tuple[str, ...], int] = {}

    for index, row in enumerate(decisions, start=1):
        line = row.get("_decision_line_number") or index
        key = decision_key(row, rules)
        if key in seen:
            findings.append({
                "code": "duplicate_review_decision_key",
                "line": line,
                "detail": f"duplicates line {seen[key]}",
            })
        else:
            seen[key] = int(line)

        for field in required_fields:
            if _empty(row.get(field)):
                findings.append({
                    "code": "review_decision_required_field_missing",
                    "line": line,
                    "detail": field,
                })

        status = str(row.get("decision_status") or "").strip()
        if status not in allowed_statuses:
            findings.append({
                "code": "review_decision_status_unknown",
                "line": line,
                "detail": status or "<empty>",
            })

        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            try:
                source = source_registry.get(source_id)
            except KeyError:
                findings.append({
                    "code": "review_decision_source_unknown",
                    "line": line,
                    "detail": source_id,
                })
            else:
                if source.family not in allowed_source_families:
                    findings.append({
                        "code": "review_decision_source_family_disallowed",
                        "line": line,
                        "detail": f"{source_id}:{source.family}",
                    })

        if status == "import_ready":
            for field in import_ready_required:
                if _empty(row.get(field)):
                    findings.append({
                        "code": "review_decision_import_ready_field_missing",
                        "line": line,
                        "detail": field,
                    })
        elif status in allowed_statuses:
            for field in non_import_ready_required:
                if _empty(row.get(field)):
                    findings.append({
                        "code": "review_decision_non_import_ready_field_missing",
                        "line": line,
                        "detail": field,
                    })

    return findings


def decisions_by_key(decisions: list[dict[str, Any]], contract: dict[str, Any] | None = None) -> dict[tuple[str, ...], dict[str, Any]]:
    rules = contract or load_eol_review_decision_contract()
    return {decision_key(row, rules): row for row in decisions}


def apply_review_decision(
    row: dict[str, Any],
    decision: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rules = contract or load_eol_review_decision_contract()
    merged = dict(row)
    for field in rules.get("overlay_fields") or []:
        if field in decision and not _empty(decision.get(field)):
            merged[str(field)] = decision[field]
    status = str(decision.get("decision_status") or "").strip()
    if status == "import_ready":
        merged["review_status"] = rules.get("import_ready_review_status") or "import_ready"
    else:
        merged["review_status"] = f"review_decision_{status or 'unknown'}"
    merged["review_decision_status"] = status
    merged["reviewer"] = decision.get("reviewer")
    merged["reviewed_at"] = decision.get("reviewed_at")
    merged["review_decision_line_number"] = decision.get("_decision_line_number")
    return merged
