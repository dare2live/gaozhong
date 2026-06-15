#!/usr/bin/env python3
"""Convert completed EOL review worksheet rows into official decision JSONL."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.audit.eol_review_decision_materialize import (
    materialize_review_decisions,
    write_decisions,
    write_manifest,
)

def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def default_manifest(year: int) -> Path:
    return ROOT / "data" / "reports" / f"eol_review_decision_materialize_{year}_{_stamp()}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--worksheet", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Decision JSONL output; defaults to official per-year decision path.")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing decision output file.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow writing an empty decision file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = args.manifest or default_manifest(args.year)
    report = materialize_review_decisions(
        year=args.year,
        worksheet_path=args.worksheet,
        output_path=args.output,
        allow_empty=args.allow_empty,
        overwrite=args.overwrite,
    )
    write_manifest(manifest, report)

    if report["status"] != "pass":
        print(
            "eol_review_decision_materialize "
            f"year={args.year} status={report['status']} "
            f"worksheet_path_exists={report['summary']['worksheet_path_exists']} "
            f"output_path_exists={report['summary']['output_path_exists']} "
            f"partial_rows={report['summary']['partial_rows']} "
            f"findings={report['summary']['findings']} "
            f"manifest={manifest}"
        )
        return 1

    try:
        write_decisions(Path(report["output_path"]), report["decisions"], overwrite=args.overwrite)
    except FileExistsError as exc:
        print(
            "eol_review_decision_materialize "
            f"year={args.year} status=fail findings=output_exists "
            f"detail={exc} manifest={manifest}"
        )
        return 1

    print(
        "eol_review_decision_materialize "
        f"year={args.year} status=pass "
        f"worksheet_path_exists={report['summary']['worksheet_path_exists']} "
        f"output_path_exists={report['summary']['output_path_exists']} "
        f"worksheet_rows={report['summary']['worksheet_rows']} "
        f"partial_rows={report['summary']['partial_rows']} "
        f"decision_rows={report['summary']['decision_rows']} "
        f"output={report['output_path']} manifest={manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
