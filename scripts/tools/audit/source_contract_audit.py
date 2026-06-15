#!/usr/bin/env python3
"""Read-only consistency audit for source registry and paper contracts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.audit.source_contracts import audit_source_contracts, write_report


def _default_output() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"source_contract_audit_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=_default_output())
    parser.add_argument("--strict", action="store_true", help="Return non-zero on BLOCK findings")
    args = parser.parse_args()

    report = audit_source_contracts()
    write_report(args.output, report)
    print(f"status={report['status']}")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    print(f"report={args.output}")
    return 1 if args.strict and report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
