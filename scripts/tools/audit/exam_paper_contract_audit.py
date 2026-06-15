#!/usr/bin/env python3
"""Read-only audit for exam paper coverage contracts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.audit.exam_contracts import audit_contract, write_report


def _default_output(contract_name: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"exam_paper_contract_{contract_name}_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="xgkii_english_m0_2021_2025")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Return non-zero when contract audit fails")
    args = parser.parse_args()

    report = audit_contract(args.contract)
    output = args.output or _default_output(args.contract)
    write_report(output, report)
    print(f"status={report['status']}")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    print(f"report={output}")
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
