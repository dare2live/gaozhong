#!/usr/bin/env python3
"""Generate a reviewer worksheet for unresolved EOL structured-draft backlog rows."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.audit.eol_review_worksheet import (
    build_eol_review_worksheet,
    write_worksheet_jsonl,
    write_worksheet_manifest,
)

def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def default_output(year: int) -> Path:
    return ROOT / "data" / "reports" / f"eol_review_worksheet_{year}_{_stamp()}.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or default_output(args.year)
    manifest = args.manifest or output.with_suffix(".manifest.json")
    worksheet = build_eol_review_worksheet(args.year, args.draft, args.decisions)
    write_worksheet_jsonl(output, worksheet)
    write_worksheet_manifest(manifest, worksheet, output)
    print(
        "eol_review_worksheet "
        f"year={args.year} "
        f"backlog_status={worksheet['backlog_status']} "
        f"backlog_items={worksheet['summary']['backlog_items']} "
        f"worksheet_rows={worksheet['summary']['worksheet_rows']} "
        f"output={output} manifest={manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
