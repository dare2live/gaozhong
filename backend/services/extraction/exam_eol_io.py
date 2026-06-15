"""EOL exam-draft IO + field-coverage audit helpers.

JSONL read/write and the draft field-coverage audit, extracted from exam_eol.py
to keep that module under the god-module line budget (Rule 8). Depends only on the
parse module (for now_iso / required_draft_fields) and the import policy; it does
not write DuckDB. exam_eol re-exports these symbols so the public API stays stable.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from backend.services.contracts import load_import_policy
from backend.services.extraction.exam_eol_parse import now_iso, required_draft_fields


def write_draft_outputs(rows: list[dict[str, Any]], audit: dict[str, Any], out_path: Path, audit_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _classify_row(
    row: dict[str, Any],
    required: tuple[str, ...],
    nullable: set[str],
) -> tuple[list[str], list[str], list[str]]:
    """Return (missing, absent, empty_non_nullable) field names for one row.

    absent = key not present at all; empty_non_nullable = present-but-empty and not
    declared nullable; missing = union of both (order-preserving over `required`).
    """
    absent: list[str] = []
    empty_non_nullable: list[str] = []
    missing: list[str] = []
    for field in required:
        if field not in row:
            absent.append(field)
            missing.append(field)
        elif field not in nullable and (row.get(field) is None or row.get(field) == ""):
            empty_non_nullable.append(field)
            missing.append(field)
    return missing, absent, empty_non_nullable


def audit_draft_field_coverage(
    rows: list[dict[str, Any]],
    *,
    policy_name: str = "exam_truth_source_import",
) -> dict[str, Any]:
    policy = load_import_policy(policy_name)
    required = required_draft_fields(policy_name)
    nullable = set(policy.get("nullable_source_fields") or ())
    missing_counts: Counter[str] = Counter()
    absent_counts: Counter[str] = Counter()
    empty_counts: Counter[str] = Counter()
    missing_by_row: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        missing, absent, empty_non_nullable = _classify_row(row, required, nullable)
        missing_counts.update(missing)
        absent_counts.update(absent)
        empty_counts.update(empty_non_nullable)
        if missing:
            missing_by_row.append({
                "row_id": row.get("id") or f"row:{idx}",
                "missing_fields": missing,
                "absent_fields": absent,
                "empty_non_nullable_fields": empty_non_nullable,
            })

    # Preserve `required` field ordering in output (Counter is insertion-ordered).
    missing_by_field = {f: missing_counts[f] for f in required if missing_counts[f]}
    absent_by_field = {f: absent_counts[f] for f in required if absent_counts[f]}
    empty_non_nullable_by_field = {f: empty_counts[f] for f in required if empty_counts[f]}
    return {
        "generated_at": now_iso(),
        "tool": "backend.services.extraction.exam_eol.audit_draft_field_coverage",
        "policy_name": policy_name,
        "status": "fail" if missing_by_field else "pass",
        "row_count": len(rows),
        "required_fields": list(required),
        "nullable_fields": sorted(nullable),
        "missing_by_field": missing_by_field,
        "absent_required_by_field": absent_by_field,
        "empty_required_by_field": empty_non_nullable_by_field,
        "missing_row_count": len(missing_by_row),
        "missing_by_row": missing_by_row[:100],
    }
