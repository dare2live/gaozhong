"""EOL review-decision **contract shape** validation (拆自 eol_review_decisions.py 防 god-module,
2026-07-06 复杂度债务修复批次: 该文件重构后涨到420行破 Rule8 >400 门槛, 按"校验对象"切开——
本文件只管 backend/config/eol_review_decisions.yaml 本身的配置形状对不对; 逐条 decision row
数据本身的校验留在 eol_review_decisions.py::validate_decisions)。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.services.contracts.eol_review_decisions import (
    KNOWN_MATERIALIZER_ISSUE_CODES, load_eol_review_decision_contract)


def _check_required_contract_lists(rules: dict[str, Any]) -> list[dict[str, str]]:
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
    findings: list[dict[str, str]] = []
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
    return findings


def _check_decision_path_config(rules: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
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
    return findings


def _check_key_field_fallback_entries(
    field_name: str, question_type_map: dict[str, Any]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for question_type, fallback_value in question_type_map.items():
        if not str(question_type).strip() or not str(fallback_value).strip():
            findings.append({
                "code": "eol_review_decision_key_fallback_empty",
                "target": f"{field_name}.{question_type}",
                "detail": "fallback question_type and value must be non-empty",
            })
    return findings


def _check_key_field_fallback_field(
    field_name: str, question_type_map: Any, key_fields: set[str]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
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
        return findings
    findings.extend(_check_key_field_fallback_entries(field_name, question_type_map))
    return findings


def _check_key_field_fallbacks(rules: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    key_fields = {str(field) for field in rules.get("key_fields") or []}
    fallback_rules = rules.get("key_field_fallbacks") or {}
    if not isinstance(fallback_rules, dict):
        findings.append({
            "code": "eol_review_decision_key_fallbacks_invalid",
            "target": "key_field_fallbacks",
            "detail": "key_field_fallbacks must be a mapping",
        })
        return findings
    for field, question_type_map in fallback_rules.items():
        field_name = str(field).strip()
        findings.extend(
            _check_key_field_fallback_field(field_name, question_type_map, key_fields)
        )
    return findings


def _check_materializer_issue_codes(rules: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for code in rules.get("materializer_priority_issue_codes") or []:
        issue_code = str(code).strip()
        if issue_code and issue_code not in KNOWN_MATERIALIZER_ISSUE_CODES:
            findings.append({
                "code": "eol_review_decision_materializer_issue_unknown",
                "target": issue_code,
                "detail": "materializer priority issue code is not emitted by decision materialization",
            })
    return findings


def validate_decision_contract(path: Path | None = None) -> list[dict[str, str]]:
    rules = load_eol_review_decision_contract(path)
    if not rules:
        return [{
            "code": "eol_review_decision_contract_missing",
            "target": "eol_review_decisions",
            "detail": "backend/config/eol_review_decisions.yaml must define eol_review_decisions",
        }]
    findings: list[dict[str, str]] = []
    findings.extend(_check_required_contract_lists(rules))
    findings.extend(_check_decision_path_config(rules))
    findings.extend(_check_key_field_fallbacks(rules))
    findings.extend(_check_materializer_issue_codes(rules))
    return findings
