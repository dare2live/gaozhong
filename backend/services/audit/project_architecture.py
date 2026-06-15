"""Read-only audit for module/data/config architecture ownership.

Public entry points (stable, imported by scripts/tools/audit/project_architecture_audit.py):
  - audit_project_architecture(config_path) -> dict
  - write_report(path, report) -> None

The per-section validators live in project_architecture_checks; shared primitives
(finding dataclass, path/contract helpers, ROOT) live in _pa_common. They are
re-exported here so prior import paths (e.g. ProjectArchitectureFinding,
_resolve_path) keep working. Splitting keeps every module < 400 lines (Rule 8).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.audit._pa_common import (  # noqa: F401  re-exported façade
    ROOT,
    ProjectArchitectureFinding,
    _add_path_finding,
    _audit_owner_module,
    _module_exists,
    _module_path,
    _now_iso,
    _read_text,
    _require_list,
    _require_mapping,
    _resolve_path,
)
from backend.services.audit.project_architecture_checks import (
    _audit_architecture_rules,
    _audit_config_contracts,
    _audit_data_zones,
    _audit_documentation_authority,
    _audit_gate_contracts,
    _audit_instruction_sources,
    _audit_legacy_policy_lints,
    _audit_module_contracts,
    _audit_sibling_projects,
    _audit_truth_sources,
)
from backend.services.contracts.project_architecture import (
    DEFAULT_CONFIG,
    REQUIRED_LIST_SECTIONS,
    REQUIRED_MAPPING_SECTIONS,
    load_project_architecture,
)


# Section name -> (audit fn, require fn). Drives both presence checks and dispatch
# so the entry point stays low-complexity (Rule 8 / CC<10).
_MAPPING_SECTIONS: tuple[tuple[str, Any], ...] = (
    ("instruction_sources", _audit_instruction_sources),
    ("truth_sources", _audit_truth_sources),
    ("sibling_projects", _audit_sibling_projects),
    ("module_contracts", _audit_module_contracts),
    ("data_zones", _audit_data_zones),
    ("config_contracts", _audit_config_contracts),
    ("documentation_authority", _audit_documentation_authority),
    ("gate_contracts", _audit_gate_contracts),
    ("legacy_policy_lints", _audit_legacy_policy_lints),
)

# Sections counted in the report summary; True => list-shaped, else mapping-shaped.
_SUMMARY_SECTIONS: tuple[tuple[str, bool], ...] = (
    ("instruction_sources", False),
    ("truth_sources", False),
    ("sibling_projects", False),
    ("module_contracts", False),
    ("data_zones", False),
    ("config_contracts", False),
    ("gate_contracts", False),
    ("legacy_policy_lints", False),
    ("architecture_rules", True),
)


def _load_contract(config: Path, findings: list[ProjectArchitectureFinding]) -> dict[str, Any]:
    if not config.exists():
        findings.append(
            ProjectArchitectureFinding(
                "architecture_config_missing",
                "BLOCK",
                str(config),
                "backend/config/project_architecture.yaml",
            )
        )
        return {}
    return load_project_architecture(config)


def _check_required_sections(contract: dict[str, Any], findings: list[ProjectArchitectureFinding]) -> None:
    for section in (*REQUIRED_MAPPING_SECTIONS, *REQUIRED_LIST_SECTIONS):
        if section not in contract:
            findings.append(ProjectArchitectureFinding("architecture_section_missing", "BLOCK", section, section))


def _run_section_audits(contract: dict[str, Any], findings: list[ProjectArchitectureFinding]) -> None:
    for section, audit_fn in _MAPPING_SECTIONS:
        audit_fn(findings, _require_mapping(findings, contract, section))
    _audit_architecture_rules(findings, _require_list(findings, contract, "architecture_rules"))


def _build_summary(
    contract: dict[str, Any],
    blocked: list[ProjectArchitectureFinding],
    warns: list[ProjectArchitectureFinding],
) -> dict[str, int]:
    summary = {name: len(contract.get(name) or ([] if is_list else {})) for name, is_list in _SUMMARY_SECTIONS}
    summary["block_findings"] = len(blocked)
    summary["warn_findings"] = len(warns)
    return summary


def audit_project_architecture(config_path: Path | None = None) -> dict[str, Any]:
    config = config_path or DEFAULT_CONFIG
    findings: list[ProjectArchitectureFinding] = []

    contract = _load_contract(config, findings)
    _check_required_sections(contract, findings)
    _run_section_audits(contract, findings)

    blocked = [finding for finding in findings if finding.severity == "BLOCK"]
    warns = [finding for finding in findings if finding.severity == "WARN"]
    return {
        "generated_at": _now_iso(),
        "tool": "backend.services.audit.project_architecture",
        "config_path": str(config),
        "status": "fail" if blocked else "warn" if warns else "pass",
        "summary": _build_summary(contract, blocked, warns),
        "findings": [finding.__dict__ for finding in findings],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
