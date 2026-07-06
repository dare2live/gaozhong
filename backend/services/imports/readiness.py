"""Read-only import readiness assessment.

This module does not write DuckDB. It checks whether structured rows satisfy the
configured import policy before a controller-owned import window exists.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.contracts import load_import_policy, match_source_state, source_state_satisfies


@dataclass(frozen=True)
class RowFinding:
    row_id: str
    code: str
    severity: str
    detail: str


@dataclass(frozen=True)
class ImportReadinessReport:
    policy_name: str
    status: str
    row_count: int
    blocked_count: int
    warn_count: int
    findings: list[RowFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "status": self.status,
            "row_count": self.row_count,
            "blocked_count": self.blocked_count,
            "warn_count": self.warn_count,
            "finding_code_counts": dict(Counter(finding.code for finding in self.findings)),
            "finding_severity_counts": dict(Counter(finding.severity for finding in self.findings)),
            "findings": [finding.__dict__ for finding in self.findings],
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _row_id(row: dict[str, Any], index: int) -> str:
    return str(row.get("id") or row.get("question_id") or row.get("origin_ref") or f"row:{index}")


def _text(row: dict[str, Any], *keys: str) -> str:
    return " ".join(str(row.get(key) or "") for key in keys)


def _missing_required_fields(row: dict[str, Any], required: list[str], nullable: list[str]) -> list[str]:
    missing: list[str] = []
    nullable_set = set(nullable)
    for field in required:
        if field not in row:
            missing.append(field)
            continue
        value = row.get(field)
        if field not in nullable_set and (value is None or value == ""):
            missing.append(field)
    return missing


def _check_required_fields(row_id: str, row: dict[str, Any], policy: dict[str, Any]) -> list[RowFinding]:
    missing = _missing_required_fields(
        row,
        list(policy.get("require_source_fields") or []),
        list(policy.get("nullable_source_fields") or []),
    )
    if missing:
        return [RowFinding(row_id, "missing_required_fields", "BLOCK", ",".join(missing))]
    return []


def _check_stem(row_id: str, row: dict[str, Any]) -> list[RowFinding]:
    findings: list[RowFinding] = []
    stem = _text(row, "stem", "stem_preview", "source_span", "raw_question")
    if not stem.strip():
        findings.append(RowFinding(row_id, "missing_stem_preview", "BLOCK", "stem/stem_preview/raw_question is empty"))
    if "参考答案" in stem:
        findings.append(RowFinding(row_id, "answer_section_contamination", "BLOCK", "stem contains reference-answer marker"))
    return findings


def _check_review_status(row_id: str, review_status: str) -> list[RowFinding]:
    if "not_import_ready" in review_status or review_status.startswith("draft_"):
        return [RowFinding(row_id, "review_status_not_import_ready", "BLOCK", review_status)]
    return []


def _check_source_state(
    row_id: str, source_state: str, review_status: str, policy: dict[str, Any]
) -> list[RowFinding]:
    findings: list[RowFinding] = []
    required_state = str(policy.get("required_source_state") or "")
    if required_state and not source_state_satisfies(source_state, required_state):
        actual_state = match_source_state(source_state)
        findings.append(
            RowFinding(
                row_id,
                "source_state_below_import_policy",
                "BLOCK",
                f"required={required_state}, actual={source_state or 'missing'}, actual_state={actual_state or 'unrecognized'}",
            )
        )
    if "candidate" in source_state or "candidate" in review_status:
        findings.append(RowFinding(row_id, "candidate_only_source", "BLOCK", source_state or review_status))
    return findings


def _check_numbering_shift(row_id: str, row: dict[str, Any], review_status: str) -> list[RowFinding]:
    observed = row.get("observed_question_number")
    reference = row.get("reference_answer_number")
    if observed is not None and reference is not None and observed != reference:
        explanation = str(row.get("numbering_explanation") or review_status)
        if "number_shift" not in explanation and "shift" not in explanation:
            return [
                RowFinding(
                    row_id,
                    "shifted_numbering_unexplained",
                    "BLOCK",
                    f"observed={observed}, reference={reference}",
                )
            ]
    return []


def _check_paper_type(row_id: str, row: dict[str, Any]) -> list[RowFinding]:
    paper_type = str(row.get("paper_type") or "")
    if not paper_type or paper_type == "未知":
        return [RowFinding(row_id, "unknown_paper_type", "BLOCK", paper_type or "missing")]
    return []


def _assess_row(row: dict[str, Any], index: int, policy: dict[str, Any]) -> list[RowFinding]:
    row_id = _row_id(row, index)
    review_status = str(row.get("review_status") or row.get("status") or "")
    source_state = str(row.get("source_state") or row.get("source_status") or "")

    findings: list[RowFinding] = []
    findings.extend(_check_required_fields(row_id, row, policy))
    findings.extend(_check_stem(row_id, row))
    findings.extend(_check_review_status(row_id, review_status))
    findings.extend(_check_source_state(row_id, source_state, review_status, policy))
    findings.extend(_check_numbering_shift(row_id, row, review_status))
    findings.extend(_check_paper_type(row_id, row))
    return findings


def assess_rows(
    rows: list[dict[str, Any]],
    *,
    policy_name: str = "exam_truth_source_import",
    policy_path: Path | None = None,
) -> ImportReadinessReport:
    policy = load_import_policy(policy_name, policy_path)
    findings: list[RowFinding] = []
    if not rows:
        findings.append(RowFinding("dataset", "empty_or_zero_rows", "BLOCK", "input has zero rows"))

    for index, row in enumerate(rows):
        findings.extend(_assess_row(row, index, policy))

    blocked = [finding for finding in findings if finding.severity == "BLOCK"]
    warns = [finding for finding in findings if finding.severity == "WARN"]
    status = "blocked" if blocked else "warn" if warns else "ready"
    return ImportReadinessReport(
        policy_name=policy_name,
        status=status,
        row_count=len(rows),
        blocked_count=len(blocked),
        warn_count=len(warns),
        findings=findings,
    )


def assess_jsonl(
    path: Path,
    *,
    policy_name: str = "exam_truth_source_import",
    policy_path: Path | None = None,
) -> ImportReadinessReport:
    return assess_rows(
        _read_jsonl(path),
        policy_name=policy_name,
        policy_path=policy_path,
    )
