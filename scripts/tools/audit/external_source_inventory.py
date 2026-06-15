#!/usr/bin/env python3
"""Write a read-only inventory report for registered external source artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.audit.external_source_inventory import (
    build_external_source_inventory,
    inventory_to_markdown,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = ROOT / "data" / "reports" / "external_source_inventory.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when ERROR findings exist.",
    )
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="With --strict, also exit non-zero on WARN findings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_external_source_inventory()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "markdown":
        args.output.write_text(inventory_to_markdown(report), encoding="utf-8")
    else:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    errors = int(report["summary"]["finding_counts"].get("ERROR", 0))
    warnings = int(report["summary"]["finding_counts"].get("WARN", 0))
    print(
        "external_source_inventory "
        f"sources={report['summary']['source_count']} "
        f"attachments={report['summary']['attachment_counts']['total']} "
        f"errors={errors} warnings={warnings} "
        f"output={args.output}"
    )

    if args.strict and (errors or (args.fail_on_warn and warnings)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
