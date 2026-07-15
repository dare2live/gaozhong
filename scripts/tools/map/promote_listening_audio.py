"""Promote fingerprint-verified candidate MP3s into data/audio/{year}/listening/.

Usage:
  python3 -m scripts.tools.map.promote_listening_audio
  python3 -m scripts.tools.map.promote_listening_audio --copy
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.listening.audio_catalog import promote_all  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--copy",
        action="store_true",
        help="force byte copy instead of hardlink",
    )
    args = ap.parse_args()
    out = promote_all(link=not args.copy)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    missing = out["catalog"].get("missing_files") or []
    if missing:
        print("MISSING:", missing, file=sys.stderr)
        return 1
    if not out["catalog"].get("complete"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
