#!/usr/bin/env python3
"""Write an EOL structured-draft review backlog report."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.audit.eol_review_backlog import build_eol_review_backlog, write_report


def default_output(year: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"eol_review_backlog_{year}_{stamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when backlog items exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or default_output(args.year)
    report = build_eol_review_backlog(args.year, args.draft, args.decisions)
    write_report(output, report)

    issue_counts = report["summary"]["issue_counts"]
    top_issues = ",".join(f"{key}:{value}" for key, value in list(issue_counts.items())[:8])
    print(
        "eol_review_backlog "
        f"year={args.year} status={report['status']} "
        f"rows={report['summary']['rows']} "
        f"review_decisions={report['summary']['review_decisions']} "
        f"applied_review_decisions={report['summary']['applied_review_decisions']} "
        f"backlog_items={report['summary']['backlog_items']} "
        f"top_issues={top_issues or 'none'} "
        f"output={output}"
    )
    if args.strict and report["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
