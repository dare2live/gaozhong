"""Read-only consistency audit for source registry and paper contracts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.services.contracts import known_source_state_tokens, match_source_state
from backend.services.contracts.eol_review_decisions import validate_decision_contract
from backend.services.contracts.eol_review import validate_eol_review_rules
from backend.services.contracts.source_crosscheck import (
    html_identity_required_groups,
    validate_html_identity_rules,
)
from backend.services.data_sources import SourceSpec, load_registry

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCES = ROOT / "backend" / "config" / "sources.yaml"
DEFAULT_CONTRACTS = ROOT / "backend" / "config" / "exam_paper_contracts.yaml"


@dataclass(frozen=True)
class SourceContractFinding:
    code: str
    severity: str
    target: str
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_contracts(path: Path = DEFAULT_CONTRACTS) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw.get("contracts") or {}


def _load_quarantined_source_ids(path: Path = DEFAULT_SOURCES) -> set[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(source_id) for source_id in (raw.get("quarantined_exam_sources") or {})}


def _source_status(source: SourceSpec) -> str:
    return str(source.status or "unknown")


def _is_risky_source(source: SourceSpec) -> bool:
    status = _source_status(source)
    family = str(source.family or "")
    return any(token in status or token in family for token in ("candidate", "suspicious"))


def _audit_source_shape(source: SourceSpec, state_tokens: set[str]) -> list[SourceContractFinding]:
    findings: list[SourceContractFinding] = []
    if not match_source_state(_source_status(source)):
        findings.append(
            SourceContractFinding(
                "source_status_has_no_known_state_token",
                "WARN",
                source.source_id,
                _source_status(source),
            )
        )
    if not source.attachments:
        findings.append(
            SourceContractFinding(
                "source_has_no_attachments",
                "BLOCK",
                source.source_id,
                "source registry entry cannot be verified without at least one attachment",
                )
            )
    if source.family == "exam_truth_source_landing_page" and not html_identity_required_groups(source.source_id):
        findings.append(
            SourceContractFinding(
                "landing_page_identity_rule_missing",
                "BLOCK",
                source.source_id,
                "landing-page source must define html identity rules in backend/config/source_crosscheck_rules.yaml",
            )
        )
    for attachment in source.attachments:
        if attachment.min_bytes <= 0:
            findings.append(
                SourceContractFinding(
                    "attachment_has_no_min_bytes",
                    "BLOCK",
                    source.source_id,
                    str(attachment.local_path),
                )
            )
        if attachment.transform == "docx_to_txt" and not attachment.text_path:
            findings.append(
                SourceContractFinding(
                    "docx_transform_missing_text_path",
                    "BLOCK",
                    source.source_id,
                    str(attachment.local_path),
                )
            )
    return findings


def _contract_source_ids(contract: dict[str, Any]) -> set[str]:
    ids: set[str] = set(contract.get("current_known_sources") or [])
    for year_contract in (contract.get("years") or {}).values():
        ids.update(year_contract.get("current_known_sources") or [])
    return ids


def audit_source_contracts() -> dict[str, Any]:
    registry = load_registry()
    contracts = _load_contracts()
    state_tokens = known_source_state_tokens()
    source_ids = set(registry.list_ids())
    quarantined_source_ids = _load_quarantined_source_ids()
    referenced_ids: set[str] = set()
    findings: list[SourceContractFinding] = []
    source_states = [
        {
            "source_id": source.source_id,
            "status": _source_status(source),
            "matched_state": match_source_state(_source_status(source)),
            "risky": _is_risky_source(source),
        }
        for source in registry.list_sources()
    ]

    for source in registry.list_sources():
        findings.extend(_audit_source_shape(source, state_tokens))

    for source_id in sorted(source_ids & quarantined_source_ids):
        findings.append(
            SourceContractFinding(
                "source_id_active_and_quarantined",
                "BLOCK",
                source_id,
                "source id cannot be present in both active exam_sources and quarantined_exam_sources",
            )
        )

    for finding in validate_html_identity_rules(known_source_ids=source_ids):
        findings.append(
            SourceContractFinding(
                finding["code"],
                "BLOCK",
                finding["target"],
                finding["detail"],
            )
        )

    for finding in validate_eol_review_rules():
        findings.append(
            SourceContractFinding(
                finding["code"],
                "BLOCK",
                finding["target"],
                finding["detail"],
            )
        )

    for finding in validate_decision_contract():
        findings.append(
            SourceContractFinding(
                finding["code"],
                "BLOCK",
                finding["target"],
                finding["detail"],
            )
        )

    for contract_name, contract in contracts.items():
        contract_ids = _contract_source_ids(contract)
        referenced_ids.update(contract_ids)
        for source_id in sorted(contract_ids):
            if source_id in quarantined_source_ids:
                findings.append(
                    SourceContractFinding(
                        "contract_references_quarantined_source",
                        "BLOCK",
                        contract_name,
                        source_id,
                    )
                )
                continue
            if source_id not in source_ids:
                findings.append(
                    SourceContractFinding(
                        "contract_references_unknown_source",
                        "BLOCK",
                        contract_name,
                        source_id,
                    )
                )
                continue
            source = registry.get(source_id)
            if _is_risky_source(source):
                findings.append(
                    SourceContractFinding(
                        "contract_references_risky_source",
                        "WARN",
                        contract_name,
                        f"{source_id}:{_source_status(source)}",
                    )
                )

    unreferenced_exam_sources = [
        source_id
        for source_id in sorted(source_ids - referenced_ids)
        if "exam" in registry.get(source_id).family or "listening" in registry.get(source_id).family
    ]
    for source_id in unreferenced_exam_sources:
        findings.append(
            SourceContractFinding(
                "exam_source_not_referenced_by_contract",
                "WARN",
                source_id,
                registry.get(source_id).family,
            )
        )

    blocked = [finding for finding in findings if finding.severity == "BLOCK"]
    warns = [finding for finding in findings if finding.severity == "WARN"]
    return {
        "generated_at": _now_iso(),
        "tool": "backend.services.audit.source_contracts",
        "status": "fail" if blocked else "warn" if warns else "pass",
        "summary": {
            "sources": len(source_ids),
            "quarantined_sources": len(quarantined_source_ids),
            "contracts": len(contracts),
            "referenced_sources": len(referenced_ids),
            "source_state_tokens": len(state_tokens),
            "block_findings": len(blocked),
            "warn_findings": len(warns),
        },
        "source_states": source_states,
        "findings": [finding.__dict__ for finding in findings],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
