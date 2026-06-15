"""Build review backlog reports for EOL structured exam drafts."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.contracts.eol_review_decisions import (
    apply_review_decision,
    decisions_by_key,
    decision_key,
    default_decision_path,
    load_eol_review_decision_contract,
    read_decisions,
    validate_decisions,
)
from backend.services.contracts.eol_review import load_eol_review_rules

ROOT = Path(__file__).resolve().parents[3]


def default_draft_path(year: int) -> Path:
    return ROOT / "data" / "external" / "exam_sources" / "eol" / f"{year}_xgkii_english_eol_structured_draft.jsonl"


def load_review_rules(path: Path | None = None) -> dict[str, Any]:
    return load_eol_review_rules(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line_number"] = line_number
        rows.append(row)
    return rows


def _as_tokens(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text.lower()] if text else []


def _text(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    return "" if value is None else str(value).strip()


def _empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return not value
    return False


def _contains_any(text: str, tokens: list[str]) -> bool:
    normalized = text.lower()
    return any(token and token in normalized for token in tokens)


def _row_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "line_number": row.get("_line_number"),
        "year": row.get("year"),
        "paper_type": row.get("paper_type"),
        "question_number": row.get("question_number"),
        "observed_question_number": row.get("observed_question_number"),
        "question_type": row.get("question_type"),
        "source_id": row.get("source_id"),
        "review_status": row.get("review_status"),
    }


def _row_issues(row: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required_fields = [str(field) for field in rules.get("required_fields") or []]
    blocking_status_tokens = _as_tokens(rules.get("blocking_review_status_tokens") or [])
    answer_required_tokens = _as_tokens(rules.get("answer_required_question_type_tokens") or [])
    allowed_empty_answer_tokens = _as_tokens(rules.get("allowed_empty_answer_question_type_tokens") or [])

    qtype = _text(row, "question_type").lower()
    answer = row.get("answer")
    review_status = _text(row, "review_status").lower()

    for field in required_fields:
        if _empty(row.get(field)):
            issues.append({"code": "required_field_missing", "detail": field})

    if _contains_any(review_status, blocking_status_tokens):
        issues.append({"code": "review_status_blocked", "detail": review_status})

    if _empty(row.get("source_span")):
        issues.append({"code": "source_span_missing", "detail": "source_span"})

    answer_required = _contains_any(qtype, answer_required_tokens)
    answer_allowed_empty = _contains_any(qtype, allowed_empty_answer_tokens)
    if answer_required and _empty(answer):
        if "listening" in qtype:
            issues.append({"code": "listening_answer_missing", "detail": qtype})
        elif not answer_allowed_empty:
            issues.append({"code": "answer_required_but_missing", "detail": qtype})

    return issues


def build_eol_review_backlog(
    year: int,
    draft_path: Path | None = None,
    decision_path: Path | None = None,
) -> dict[str, Any]:
    path = draft_path or default_draft_path(year)
    rules = load_review_rules()
    decision_contract = load_eol_review_decision_contract()
    decisions_path = decision_path or default_decision_path(year, decision_contract)
    rows = read_jsonl(path)
    decisions = read_decisions(decisions_path)
    decision_findings = validate_decisions(decisions, contract=decision_contract)
    decision_map = decisions_by_key(decisions, decision_contract)
    applied_decision_count = 0
    matched_decision_keys: set[tuple[str, ...]] = set()
    backlog = []
    issue_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    priority = list(rules.get("priority_issue_codes") or [])

    if not path.exists():
        issue_counts["draft_missing"] += 1
        backlog.append(
            {
                "identity": {"year": year, "draft_path": str(path)},
                "issues": [{"code": "draft_missing", "detail": str(path)}],
            }
        )

    for row in rows:
        row_key = decision_key(row, decision_contract)
        decision = decision_map.get(row_key)
        effective_row = apply_review_decision(row, decision, contract=decision_contract) if decision else row
        if decision:
            applied_decision_count += 1
            matched_decision_keys.add(row_key)
        issues = _row_issues(effective_row, rules)
        if not issues:
            continue
        for issue in issues:
            issue_counts[issue["code"]] += 1
        type_counts[str(effective_row.get("question_type") or "unknown")] += 1
        backlog.append({"identity": _row_identity(effective_row), "issues": issues})

    for key, decision in decision_map.items():
        if key in matched_decision_keys:
            continue
        issue_counts["unmatched_review_decision_key"] += 1
        backlog.append({
            "identity": {
                "year": year,
                "decision_path": str(decisions_path),
                "line_number": decision.get("_decision_line_number"),
                "decision_key": list(key),
            },
            "issues": [{
                "code": "unmatched_review_decision_key",
                "detail": "review decision key does not match any current draft row",
            }],
        })

    for finding in decision_findings:
        issue_counts[finding["code"]] += 1
        backlog.append({
            "identity": {
                "year": year,
                "decision_path": str(decisions_path),
                "line_number": finding.get("line"),
            },
            "issues": [{"code": finding["code"], "detail": finding["detail"]}],
        })

    by_priority: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in backlog:
        item_codes = {issue["code"] for issue in item["issues"]}
        matched = next((code for code in priority if code in item_codes), "other")
        by_priority[matched].append(item)

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tool": "backend.services.audit.eol_review_backlog",
        "year": year,
        "draft_path": str(path),
        "decision_path": str(decisions_path),
        "status": "fail" if backlog else "pass",
        "summary": {
            "rows": len(rows),
            "review_decisions": len(decisions),
            "applied_review_decisions": applied_decision_count,
            "decision_findings": len(decision_findings),
            "backlog_items": len(backlog),
            "issue_counts": dict(sorted(issue_counts.items())),
            "question_type_counts": dict(sorted(type_counts.items())),
            "priority_buckets": {key: len(value) for key, value in by_priority.items()},
        },
        "backlog": backlog,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
