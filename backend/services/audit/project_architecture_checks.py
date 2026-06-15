"""Per-section validators for the project-architecture audit.

Split out of project_architecture.py to keep each module < 400 lines (Rule 8).
The public entry point audit_project_architecture (in project_architecture.py)
dispatches into the _audit_* functions defined here. Shared primitives live in
_pa_common to keep the import graph acyclic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.services.audit._pa_common import (
    ProjectArchitectureFinding,
    _add_path_finding,
    _audit_owner_module,
    _read_text,
    _resolve_path,
)


def _audit_instruction_sources(
    findings: list[ProjectArchitectureFinding],
    instruction_sources: dict[str, Any],
) -> None:
    for source_id, raw in instruction_sources.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("instruction_source_invalid", "BLOCK", source_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("instruction_source_path_missing", "BLOCK", source_id, "path"))
            continue
        _add_path_finding(
            findings,
            code="instruction_source_path_missing",
            target=f"instruction_sources.{source_id}",
            path_text=str(path_text),
            expect_dir=False,
        )
        required_tokens = raw.get("required_tokens") or []
        if required_tokens:
            path = _resolve_path(str(path_text))
            if path.exists():
                text = _read_text(path)
                for token in required_tokens:
                    if str(token) not in text:
                        findings.append(
                            ProjectArchitectureFinding(
                                "instruction_source_required_token_missing",
                                "BLOCK",
                                f"instruction_sources.{source_id}",
                                str(token),
                            )
                        )


def _audit_truth_sources(
    findings: list[ProjectArchitectureFinding],
    truth_sources: dict[str, Any],
) -> None:
    for source_id, raw in truth_sources.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("truth_source_invalid", "BLOCK", source_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("truth_source_path_missing", "BLOCK", source_id, "path"))
        else:
            _add_path_finding(
                findings,
                code="truth_source_path_missing",
                target=f"truth_sources.{source_id}",
                path_text=str(path_text),
                expect_dir=False,
            )
        _audit_owner_module(findings, "truth_sources", source_id, raw)


def _audit_sibling_projects(
    findings: list[ProjectArchitectureFinding],
    sibling_projects: dict[str, Any],
) -> None:
    for project_id, raw in sibling_projects.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("sibling_project_invalid", "BLOCK", project_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("sibling_project_path_missing", "BLOCK", project_id, "path"))
        else:
            _add_path_finding(
                findings,
                code="sibling_project_path_missing",
                target=f"sibling_projects.{project_id}",
                path_text=str(path_text),
                expect_dir=True,
            )
        if "reference" not in str(raw.get("relationship") or ""):
            findings.append(
                ProjectArchitectureFinding(
                    "sibling_project_relationship_not_reference",
                    "WARN",
                    f"sibling_projects.{project_id}",
                    str(raw.get("relationship") or ""),
                )
            )
        if not raw.get("forbidden_use"):
            findings.append(
                ProjectArchitectureFinding(
                    "sibling_project_forbidden_use_missing",
                    "BLOCK",
                    f"sibling_projects.{project_id}",
                    "must declare forbidden_use",
                )
            )


def _audit_module_contracts(
    findings: list[ProjectArchitectureFinding],
    module_contracts: dict[str, Any],
) -> None:
    for module_id, raw in module_contracts.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("module_contract_invalid", "BLOCK", module_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("module_path_missing", "BLOCK", module_id, "path"))
        else:
            _add_path_finding(
                findings,
                code="module_path_missing",
                target=f"module_contracts.{module_id}",
                path_text=str(path_text),
                expect_dir=True,
            )
        owner_config = raw.get("owner_config")
        if owner_config:
            _add_path_finding(
                findings,
                code="module_owner_config_missing",
                target=f"module_contracts.{module_id}",
                path_text=str(owner_config),
                expect_dir=False,
            )
        if not raw.get("role"):
            findings.append(ProjectArchitectureFinding("module_role_missing", "WARN", module_id, "role"))
        _audit_owner_module(findings, "module_contracts", module_id, raw)
        for required_file in raw.get("required_files") or []:
            _add_path_finding(
                findings,
                code="module_required_file_missing",
                target=f"module_contracts.{module_id}",
                path_text=str(required_file),
                expect_dir=False,
            )


def _audit_data_zones(
    findings: list[ProjectArchitectureFinding],
    data_zones: dict[str, Any],
) -> None:
    for zone_id, raw in data_zones.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("data_zone_invalid", "BLOCK", zone_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("data_zone_path_missing", "BLOCK", zone_id, "path"))
        else:
            _add_path_finding(
                findings,
                code="data_zone_path_missing",
                target=f"data_zones.{zone_id}",
                path_text=str(path_text),
                expect_dir=True,
            )
        _audit_owner_module(findings, "data_zones", zone_id, raw)
        if not raw.get("truth_policy"):
            findings.append(ProjectArchitectureFinding("data_zone_truth_policy_missing", "WARN", zone_id, "truth_policy"))
        if not raw.get("write_policy"):
            findings.append(ProjectArchitectureFinding("data_zone_write_policy_missing", "WARN", zone_id, "write_policy"))


def _audit_config_contracts(
    findings: list[ProjectArchitectureFinding],
    config_contracts: dict[str, Any],
) -> None:
    for config_id, raw in config_contracts.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("config_contract_invalid", "BLOCK", config_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("config_path_missing", "BLOCK", config_id, "path"))
        else:
            _add_path_finding(
                findings,
                code="config_path_missing",
                target=f"config_contracts.{config_id}",
                path_text=str(path_text),
                expect_dir=False,
            )
        _audit_owner_module(findings, "config_contracts", config_id, raw)
        if not raw.get("owns"):
            findings.append(ProjectArchitectureFinding("config_ownership_missing", "WARN", config_id, "owns"))


def _audit_documentation_authority(
    findings: list[ProjectArchitectureFinding],
    documentation_authority: dict[str, Any],
) -> None:
    index = documentation_authority.get("required_index") or {}
    if isinstance(index, dict) and index.get("path"):
        _add_path_finding(
            findings,
            code="documentation_index_missing",
            target="documentation_authority.required_index",
            path_text=str(index["path"]),
            expect_dir=False,
        )
    else:
        findings.append(ProjectArchitectureFinding("documentation_index_missing", "BLOCK", "documentation_authority", "required_index.path"))
    for key in ("current_docs", "evidence_ledgers"):
        for path_text in documentation_authority.get(key) or []:
            _add_path_finding(
                findings,
                code=f"documentation_{key}_missing",
                target=f"documentation_authority.{key}",
                path_text=str(path_text),
                expect_dir=False,
            )


def _audit_gate_contracts(
    findings: list[ProjectArchitectureFinding],
    gate_contracts: dict[str, Any],
) -> None:
    for gate_id, raw in gate_contracts.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("gate_contract_invalid", "BLOCK", gate_id, "must be mapping"))
            continue
        script = raw.get("script")
        if not script:
            findings.append(ProjectArchitectureFinding("gate_script_missing", "BLOCK", gate_id, "script"))
        else:
            _add_path_finding(
                findings,
                code="gate_script_missing",
                target=f"gate_contracts.{gate_id}",
                path_text=str(script),
                expect_dir=False,
            )
        if not raw.get("command"):
            findings.append(ProjectArchitectureFinding("gate_command_missing", "BLOCK", gate_id, "command"))
        if not raw.get("verifies"):
            findings.append(ProjectArchitectureFinding("gate_verification_scope_missing", "WARN", gate_id, "verifies"))


def _lint_matched_missing_refs(raw: dict[str, Any], text: str) -> tuple[list[Any], list[str]]:
    """Return (matched forbidden patterns, required config refs missing from text)."""
    matched = [pattern for pattern in raw.get("forbidden_patterns") or [] if str(pattern) in text]
    if not matched:
        return [], []
    required_refs = [str(ref) for ref in raw.get("required_config_refs") or []]
    missing_refs = [ref for ref in required_refs if ref not in text and Path(ref).name not in text]
    return matched, missing_refs


def _audit_one_legacy_policy_lint(
    findings: list[ProjectArchitectureFinding],
    lint_id: str,
    raw: Any,
) -> None:
    if not isinstance(raw, dict):
        findings.append(ProjectArchitectureFinding("legacy_policy_lint_invalid", "BLOCK", lint_id, "must be mapping"))
        return
    path_text = raw.get("path")
    if not path_text:
        findings.append(ProjectArchitectureFinding("legacy_policy_lint_path_missing", "BLOCK", lint_id, "path"))
        return
    path = _resolve_path(str(path_text))
    _add_path_finding(
        findings,
        code="legacy_policy_lint_path_missing",
        target=f"legacy_policy_lints.{lint_id}",
        path_text=str(path_text),
        expect_dir=False,
    )
    if not path.exists():
        return
    matched, missing_refs = _lint_matched_missing_refs(raw, _read_text(path))
    if matched and missing_refs:
        findings.append(
            ProjectArchitectureFinding(
                "legacy_policy_lint_failed",
                str(raw.get("severity") or "BLOCK"),
                f"legacy_policy_lints.{lint_id}",
                f"matched={matched}; missing_config_refs={missing_refs}; rationale={raw.get('rationale') or ''}",
            )
        )


def _audit_legacy_policy_lints(
    findings: list[ProjectArchitectureFinding],
    legacy_policy_lints: dict[str, Any],
) -> None:
    for lint_id, raw in legacy_policy_lints.items():
        _audit_one_legacy_policy_lint(findings, lint_id, raw)


def _audit_architecture_rule_code(
    findings: list[ProjectArchitectureFinding],
    target: str,
    code: str,
    known_codes: set[str],
) -> None:
    if not code:
        findings.append(ProjectArchitectureFinding("architecture_rule_code_missing", "BLOCK", target, "code"))
    elif code in known_codes:
        findings.append(ProjectArchitectureFinding("architecture_rule_code_duplicate", "BLOCK", target, code))
    else:
        known_codes.add(code)


def _audit_one_architecture_rule(
    findings: list[ProjectArchitectureFinding],
    target: str,
    raw: Any,
    known_codes: set[str],
) -> None:
    if not isinstance(raw, dict):
        findings.append(ProjectArchitectureFinding("architecture_rule_invalid", "BLOCK", target, "must be mapping"))
        return
    code = str(raw.get("code") or "")
    _audit_architecture_rule_code(findings, target, code, known_codes)
    if str(raw.get("severity") or "") not in {"BLOCK", "WARN", "INFO"}:
        findings.append(ProjectArchitectureFinding("architecture_rule_severity_invalid", "BLOCK", code or target, str(raw.get("severity") or "")))
    if not raw.get("rule"):
        findings.append(ProjectArchitectureFinding("architecture_rule_body_missing", "WARN", code or target, "rule"))


def _audit_architecture_rules(
    findings: list[ProjectArchitectureFinding],
    architecture_rules: list[Any],
) -> None:
    known_codes: set[str] = set()
    for idx, raw in enumerate(architecture_rules):
        _audit_one_architecture_rule(findings, f"architecture_rules[{idx}]", raw, known_codes)
