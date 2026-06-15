#!/usr/bin/env python3
"""Audit the machine-readable module/data/config architecture contract."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.audit.project_architecture import audit_project_architecture, write_report


def _default_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"project_architecture_audit_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "backend" / "config" / "project_architecture.yaml",
        help="Architecture contract YAML path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output_path(),
        help="Report output path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when BLOCK findings exist.",
    )
    args = parser.parse_args()

    report = audit_project_architecture(args.config)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_report(output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "summary": report["summary"],
                "report": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.strict and report["status"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
