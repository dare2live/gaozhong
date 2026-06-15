#!/usr/bin/env python3
"""Read-only field coverage audit for EOL structured draft JSONL."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.extraction.exam_eol import audit_draft_field_coverage, draft_paths, read_jsonl


def _default_output(year: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"eol_draft_field_audit_{year}_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, choices=[2021, 2022])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--policy", default="exam_truth_source_import")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    path = args.input or draft_paths(args.year)["draft"]
    report = audit_draft_field_coverage(read_jsonl(path), policy_name=args.policy)
    output = args.output or _default_output(args.year)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"status={report['status']}")
    print(f"rows={report['row_count']} missing_rows={report['missing_row_count']}")
    top_missing = sorted(report["missing_by_field"].items(), key=lambda item: (-item[1], item[0]))[:10]
    if top_missing:
        print("top_missing=" + ",".join(f"{field}:{count}" for field, count in top_missing))
    print(f"report={output}")
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
