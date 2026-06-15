#!/usr/bin/env python3
"""Acquire or verify external data sources declared in backend/config/sources.yaml."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.data_sources import acquire_source, load_registry
from backend.services.data_sources.fetcher import write_manifest


def _default_output() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return ROOT / "data" / "reports" / f"external_source_acquisition_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", dest="sources", help="Source id from backend/config/sources.yaml")
    parser.add_argument("--reuse-existing", action="store_true", help="Verify existing local files instead of downloading again")
    parser.add_argument("--output", type=Path, default=_default_output())
    parser.add_argument("--strict", action="store_true", help="Return non-zero when any acquired source fails verification")
    args = parser.parse_args()

    registry = load_registry()
    source_ids = args.sources or registry.list_ids()
    records = [
        acquire_source(registry.get(source_id), reuse_existing=args.reuse_existing)
        for source_id in source_ids
    ]
    write_manifest(args.output, records)
    for record in records:
        print(
            f"{record['source_id']}: {record['status']} "
            f"attachments={len(record['attachments'])} findings={len(record['findings'])}"
        )
    print(f"manifest={args.output}")
    if args.strict and any(record["status"] != "ok" for record in records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
