"""Inventory registered external exam sources and their local artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.contracts.source_crosscheck import html_identity_required_groups
from backend.services.contracts.source_state import match_source_state
from backend.services.data_sources.registry import ROOT, AttachmentSpec, SourceSpec, load_registry

NON_IMPORTABLE_STATE_TOKENS = {"candidate_only", "suspicious"}


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _attachment_inventory(source: SourceSpec, attachment: AttachmentSpec) -> dict[str, Any]:
    local_path = attachment.local_path
    exists = local_path.exists()
    size_bytes = local_path.stat().st_size if exists else None
    in_project = _is_under(local_path, ROOT)
    size_ok = bool(exists and size_bytes is not None and size_bytes >= attachment.min_bytes)

    row: dict[str, Any] = {
        "source_id": source.source_id,
        "kind": attachment.kind,
        "path": str(local_path),
        "exists": exists,
        "size_bytes": size_bytes,
        "min_bytes": attachment.min_bytes,
        "size_ok": size_ok,
        "in_project": in_project,
        "has_url": bool(attachment.url),
        "expected_sha256": attachment.expected_sha256,
        "transform": attachment.transform,
    }

    if attachment.text_path:
        text_path = attachment.text_path
        text_exists = text_path.exists()
        text_chars = len(text_path.read_text(encoding="utf-8", errors="ignore")) if text_exists else None
        row.update(
            {
                "text_path": str(text_path),
                "text_exists": text_exists,
                "text_chars": text_chars,
                "min_text_chars": attachment.min_text_chars,
                "text_size_ok": bool(
                    text_exists
                    and text_chars is not None
                    and text_chars >= attachment.min_text_chars
                ),
            }
        )

    return row


def _add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    source_id: str,
    detail: str,
    path: str | None = None,
) -> None:
    findings.append(
        {
            "severity": severity,
            "code": code,
            "source_id": source_id,
            "path": path,
            "detail": detail,
        }
    )


def _source_findings(source: SourceSpec, matched_state: str | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    normalized_status = source.status.lower()

    if not matched_state:
        _add_finding(
            findings,
            severity="WARN",
            code="unknown_source_state",
            source_id=source.source_id,
            detail=f"source status is not matched by source_states.yaml: {source.status}",
        )

    if matched_state in NON_IMPORTABLE_STATE_TOKENS or "candidate" in normalized_status:
        _add_finding(
            findings,
            severity="WARN",
            code="non_importable_source_state",
            source_id=source.source_id,
            detail=f"source status is not importable for M0 truth closure: {source.status}",
        )

    if "suspicious" in normalized_status:
        _add_finding(
            findings,
            severity="WARN",
            code="suspicious_source_state",
            source_id=source.source_id,
            detail=f"source is explicitly suspicious: {source.status}",
        )

    if not source.attachments:
        _add_finding(
            findings,
            severity="ERROR",
            code="source_has_no_attachments",
            source_id=source.source_id,
            detail="registered source has no local artifact contract",
        )

    if source.family == "exam_truth_source_landing_page" and not html_identity_required_groups(source.source_id):
        _add_finding(
            findings,
            severity="ERROR",
            code="landing_page_identity_rule_missing",
            source_id=source.source_id,
            detail="landing-page source must define html identity rules in backend/config/source_crosscheck_rules.yaml",
        )

    return findings


def _attachment_findings(source: SourceSpec, row: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    path = str(row["path"])

    if not row["exists"]:
        _add_finding(
            findings,
            severity="ERROR",
            code="attachment_missing",
            source_id=source.source_id,
            path=path,
            detail="registered local artifact does not exist",
        )
    elif not row["size_ok"]:
        _add_finding(
            findings,
            severity="ERROR",
            code="attachment_below_min_bytes",
            source_id=source.source_id,
            path=path,
            detail=f"artifact has {row['size_bytes']} bytes; min_bytes={row['min_bytes']}",
        )

    if not row["in_project"]:
        _add_finding(
            findings,
            severity="WARN",
            code="attachment_outside_project",
            source_id=source.source_id,
            path=path,
            detail="artifact is registered through an absolute path outside this project",
        )

    if row.get("text_path") and not row.get("text_exists"):
        _add_finding(
            findings,
            severity="ERROR",
            code="derived_text_missing",
            source_id=source.source_id,
            path=str(row["text_path"]),
            detail="attachment requires derived text, but text_path is missing",
        )
    elif row.get("text_path") and not row.get("text_size_ok"):
        _add_finding(
            findings,
            severity="ERROR",
            code="derived_text_below_min_chars",
            source_id=source.source_id,
            path=str(row["text_path"]),
            detail=(
                f"derived text has {row.get('text_chars')} chars; "
                f"min_text_chars={row.get('min_text_chars')}"
            ),
        )

    return findings


def _source_summary_row(source: SourceSpec, matched_state: str | None) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "name": source.name,
        "family": source.family,
        "org": source.org,
        "year": source.year,
        "paper_type": source.paper_type,
        "status": source.status,
        "matched_state": matched_state,
        "publish_url": source.publish_url,
        "attachment_count": len(source.attachments),
    }


def _collect_source_inventory(
    source: SourceSpec,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    matched_state = match_source_state(source.status)
    source_rows = [_attachment_inventory(source, attachment) for attachment in source.attachments]

    findings = list(_source_findings(source, matched_state))
    for row in source_rows:
        findings.extend(_attachment_findings(source, row))

    return _source_summary_row(source, matched_state), source_rows, findings


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    severity_counts = {"ERROR": 0, "WARN": 0}
    for finding in findings:
        severity = str(finding["severity"])
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return severity_counts


def _attachment_summary_counts(attachments: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(attachments),
        "in_project": sum(1 for row in attachments if row["in_project"]),
        "outside_project": sum(1 for row in attachments if not row["in_project"]),
        "missing": sum(1 for row in attachments if not row["exists"]),
        "below_min_bytes": sum(1 for row in attachments if row["exists"] and not row["size_ok"]),
    }


def build_external_source_inventory() -> dict[str, Any]:
    registry = load_registry()
    sources = []
    findings: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []

    for source in registry.list_sources():
        source_row, source_rows, source_findings = _collect_source_inventory(source)
        attachments.extend(source_rows)
        findings.extend(source_findings)
        sources.append(source_row)

    severity_counts = _severity_counts(findings)
    attachment_counts = _attachment_summary_counts(attachments)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "summary": {
            "source_count": len(sources),
            "attachment_counts": attachment_counts,
            "finding_counts": severity_counts,
            "current_m0_inventory_status": (
                "blocked"
                if severity_counts.get("ERROR", 0) or severity_counts.get("WARN", 0)
                else "clean"
            ),
        },
        "sources": sources,
        "attachments": attachments,
        "findings": findings,
    }


def inventory_to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# External Source Inventory",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Project root: `{report['project_root']}`",
        f"- Sources: `{report['summary']['source_count']}`",
        f"- Attachments: `{report['summary']['attachment_counts']['total']}`",
        f"- Findings: ERROR=`{report['summary']['finding_counts'].get('ERROR', 0)}`, WARN=`{report['summary']['finding_counts'].get('WARN', 0)}`",
        f"- M0 inventory status: `{report['summary']['current_m0_inventory_status']}`",
        "",
        "## Findings",
        "",
        "| Severity | Code | Source | Path | Detail |",
        "|---|---|---|---|---|",
    ]

    if report["findings"]:
        for finding in report["findings"]:
            path = finding.get("path") or ""
            lines.append(
                f"| {finding['severity']} | `{finding['code']}` | `{finding['source_id']}` | `{path}` | {finding['detail']} |"
            )
    else:
        lines.append("| OK | `none` |  |  | no findings |")

    lines.extend(
        [
            "",
            "## Attachments",
            "",
            "| Source | Kind | In project | Exists | Size | Min bytes | Path |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["attachments"]:
        size = "" if row["size_bytes"] is None else str(row["size_bytes"])
        lines.append(
            f"| `{row['source_id']}` | `{row['kind']}` | {row['in_project']} | {row['exists']} | {size} | {row['min_bytes']} | `{row['path']}` |"
        )

    return "\n".join(lines) + "\n"
