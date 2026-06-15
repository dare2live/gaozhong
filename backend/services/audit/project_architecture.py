"""Read-only audit for module/data/config architecture ownership."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.contracts.project_architecture import (
    DEFAULT_CONFIG,
    REQUIRED_LIST_SECTIONS,
    REQUIRED_MAPPING_SECTIONS,
    load_project_architecture,
)

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ProjectArchitectureFinding:
    code: str
    severity: str
    target: str
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _module_path(module_name: str) -> Path:
    return ROOT / Path(*module_name.split("."))


def _module_exists(module_name: str) -> bool:
    base = _module_path(module_name)
    return (base.with_suffix(".py")).exists() or (base / "__init__.py").exists()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _add_path_finding(
    findings: list[ProjectArchitectureFinding],
    *,
    code: str,
    target: str,
    path_text: str,
    expect_dir: bool | None = None,
) -> None:
    path = _resolve_path(path_text)
    if not path.exists():
        findings.append(ProjectArchitectureFinding(code, "BLOCK", target, path_text))
        return
    if expect_dir is True and not path.is_dir():
        findings.append(ProjectArchitectureFinding(f"{code}_not_directory", "BLOCK", target, path_text))
    if expect_dir is False and not path.is_file():
        findings.append(ProjectArchitectureFinding(f"{code}_not_file", "BLOCK", target, path_text))


def _require_mapping(
    findings: list[ProjectArchitectureFinding],
    contract: dict[str, Any],
    section: str,
) -> dict[str, Any]:
    value = contract.get(section)
    if not isinstance(value, dict) or not value:
        findings.append(
            ProjectArchitectureFinding(
                "architecture_section_missing_or_empty",
                "BLOCK",
                section,
                "section must be a non-empty mapping",
            )
        )
        return {}
    return value


def _require_list(
    findings: list[ProjectArchitectureFinding],
    contract: dict[str, Any],
    section: str,
) -> list[Any]:
    value = contract.get(section)
    if not isinstance(value, list) or not value:
        findings.append(
            ProjectArchitectureFinding(
                "architecture_section_missing_or_empty",
                "BLOCK",
                section,
                "section must be a non-empty list",
            )
        )
        return []
    return value


def _audit_owner_module(
    findings: list[ProjectArchitectureFinding],
    section: str,
    item_id: str,
    item: dict[str, Any],
) -> None:
    owner_module = item.get("owner_module")
    if owner_module and not _module_exists(str(owner_module)):
        findings.append(
            ProjectArchitectureFinding(
                "owner_module_missing",
                "BLOCK",
                f"{section}.{item_id}",
                str(owner_module),
            )
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


def _audit_legacy_policy_lints(
    findings: list[ProjectArchitectureFinding],
    legacy_policy_lints: dict[str, Any],
) -> None:
    for lint_id, raw in legacy_policy_lints.items():
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("legacy_policy_lint_invalid", "BLOCK", lint_id, "must be mapping"))
            continue
        path_text = raw.get("path")
        if not path_text:
            findings.append(ProjectArchitectureFinding("legacy_policy_lint_path_missing", "BLOCK", lint_id, "path"))
            continue
        path = _resolve_path(str(path_text))
        _add_path_finding(
            findings,
            code="legacy_policy_lint_path_missing",
            target=f"legacy_policy_lints.{lint_id}",
            path_text=str(path_text),
            expect_dir=False,
        )
        if not path.exists():
            continue
        text = _read_text(path)
        matched = [pattern for pattern in raw.get("forbidden_patterns") or [] if str(pattern) in text]
        if not matched:
            continue
        required_refs = [str(ref) for ref in raw.get("required_config_refs") or []]
        missing_refs = [ref for ref in required_refs if ref not in text and Path(ref).name not in text]
        if missing_refs:
            findings.append(
                ProjectArchitectureFinding(
                    "legacy_policy_lint_failed",
                    str(raw.get("severity") or "BLOCK"),
                    f"legacy_policy_lints.{lint_id}",
                    f"matched={matched}; missing_config_refs={missing_refs}; rationale={raw.get('rationale') or ''}",
                )
            )


def _audit_architecture_rules(
    findings: list[ProjectArchitectureFinding],
    architecture_rules: list[Any],
) -> None:
    known_codes: set[str] = set()
    for idx, raw in enumerate(architecture_rules):
        target = f"architecture_rules[{idx}]"
        if not isinstance(raw, dict):
            findings.append(ProjectArchitectureFinding("architecture_rule_invalid", "BLOCK", target, "must be mapping"))
            continue
        code = str(raw.get("code") or "")
        if not code:
            findings.append(ProjectArchitectureFinding("architecture_rule_code_missing", "BLOCK", target, "code"))
        elif code in known_codes:
            findings.append(ProjectArchitectureFinding("architecture_rule_code_duplicate", "BLOCK", target, code))
        else:
            known_codes.add(code)
        if str(raw.get("severity") or "") not in {"BLOCK", "WARN", "INFO"}:
            findings.append(ProjectArchitectureFinding("architecture_rule_severity_invalid", "BLOCK", code or target, str(raw.get("severity") or "")))
        if not raw.get("rule"):
            findings.append(ProjectArchitectureFinding("architecture_rule_body_missing", "WARN", code or target, "rule"))


def audit_project_architecture(config_path: Path | None = None) -> dict[str, Any]:
    config = config_path or DEFAULT_CONFIG
    findings: list[ProjectArchitectureFinding] = []

    if not config.exists():
        findings.append(
            ProjectArchitectureFinding(
                "architecture_config_missing",
                "BLOCK",
                str(config),
                "backend/config/project_architecture.yaml",
            )
        )
        contract: dict[str, Any] = {}
    else:
        contract = load_project_architecture(config)

    for section in REQUIRED_MAPPING_SECTIONS:
        if section not in contract:
            findings.append(ProjectArchitectureFinding("architecture_section_missing", "BLOCK", section, section))
    for section in REQUIRED_LIST_SECTIONS:
        if section not in contract:
            findings.append(ProjectArchitectureFinding("architecture_section_missing", "BLOCK", section, section))

    _audit_instruction_sources(findings, _require_mapping(findings, contract, "instruction_sources"))
    _audit_truth_sources(findings, _require_mapping(findings, contract, "truth_sources"))
    _audit_sibling_projects(findings, _require_mapping(findings, contract, "sibling_projects"))
    _audit_module_contracts(findings, _require_mapping(findings, contract, "module_contracts"))
    _audit_data_zones(findings, _require_mapping(findings, contract, "data_zones"))
    _audit_config_contracts(findings, _require_mapping(findings, contract, "config_contracts"))
    _audit_documentation_authority(findings, _require_mapping(findings, contract, "documentation_authority"))
    _audit_gate_contracts(findings, _require_mapping(findings, contract, "gate_contracts"))
    _audit_legacy_policy_lints(findings, _require_mapping(findings, contract, "legacy_policy_lints"))
    _audit_architecture_rules(findings, _require_list(findings, contract, "architecture_rules"))

    blocked = [finding for finding in findings if finding.severity == "BLOCK"]
    warns = [finding for finding in findings if finding.severity == "WARN"]
    return {
        "generated_at": _now_iso(),
        "tool": "backend.services.audit.project_architecture",
        "config_path": str(config),
        "status": "fail" if blocked else "warn" if warns else "pass",
        "summary": {
            "instruction_sources": len(contract.get("instruction_sources") or {}),
            "truth_sources": len(contract.get("truth_sources") or {}),
            "sibling_projects": len(contract.get("sibling_projects") or {}),
            "module_contracts": len(contract.get("module_contracts") or {}),
            "data_zones": len(contract.get("data_zones") or {}),
            "config_contracts": len(contract.get("config_contracts") or {}),
            "gate_contracts": len(contract.get("gate_contracts") or {}),
            "legacy_policy_lints": len(contract.get("legacy_policy_lints") or {}),
            "architecture_rules": len(contract.get("architecture_rules") or []),
            "block_findings": len(blocked),
            "warn_findings": len(warns),
        },
        "findings": [finding.__dict__ for finding in findings],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
