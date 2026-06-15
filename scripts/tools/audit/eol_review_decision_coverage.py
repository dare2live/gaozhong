#!/usr/bin/env python3
"""Audit coverage of official EOL review decisions against the current draft."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.audit.eol_review_decision_coverage import (
    build_eol_review_decision_coverage,
    write_report,
)

def default_output(year: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"eol_review_decision_coverage_{year}_{stamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when coverage status is not pass.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or default_output(args.year)
    report = build_eol_review_decision_coverage(args.year, args.draft, args.decisions)
    write_report(output, report)
    print(
        "eol_review_decision_coverage "
        f"year={args.year} status={report['status']} "
        f"decision_path_exists={report['summary']['decision_path_exists']} "
        f"decision_rows={report['summary']['decision_rows']} "
        f"matched_decisions={report['summary']['matched_decisions']} "
        f"unmatched_decisions={report['summary']['unmatched_decisions']} "
        f"remaining_backlog_items={report['summary']['remaining_backlog_items']} "
        f"findings={len(report['findings'])} "
        f"output={output}"
    )
    if args.strict and report["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
