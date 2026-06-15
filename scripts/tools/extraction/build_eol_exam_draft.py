#!/usr/bin/env python3
"""Build review-only EOL New Curriculum Paper II structured drafts.

Extraction logic lives in backend.services.extraction.exam_eol. This CLI only
handles arguments and file output. It does not write DuckDB and does not produce
import-ready truth rows.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.extraction.exam_eol import build_draft, draft_paths, write_draft_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, choices=[2021, 2022])
    parser.add_argument("--text", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()

    defaults = draft_paths(args.year)
    text_path = args.text or defaults["text"]
    out_path = args.out or defaults["draft"]
    audit_path = args.audit or defaults["audit"]

    rows, audit = build_draft(args.year, text_path)
    write_draft_outputs(rows, audit, out_path, audit_path)
    print(f"draft={out_path}")
    print(f"audit={audit_path}")
    print(f"rows={audit['row_count']} keyed={audit['keyed_count']} missing_stem={audit['missing_stem_count']}")
    print(f"import_ready={audit['import_ready']}")


if __name__ == "__main__":
    main()
