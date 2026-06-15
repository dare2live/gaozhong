#!/usr/bin/env python3
"""Read-only dry-run gate for structured exam-source rows."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.imports import assess_jsonl


def _default_output(input_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stem = input_path.stem.replace("_structured_draft", "")
    return ROOT / "data" / "reports" / f"import_readiness_{stem}_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Structured JSONL rows to assess")
    parser.add_argument("--policy", default="exam_truth_source_import")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Return non-zero when readiness is blocked")
    args = parser.parse_args()

    report = assess_jsonl(args.input, policy_name=args.policy)
    output = args.output or _default_output(args.input)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"status={report.status}")
    print(f"rows={report.row_count} blocked={report.blocked_count} warn={report.warn_count}")
    print(f"report={output}")
    return 1 if args.strict and report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
