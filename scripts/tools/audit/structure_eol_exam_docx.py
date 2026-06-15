#!/usr/bin/env python3
"""Backward-compatible wrapper for EOL draft extraction.

Prefer scripts/tools/extraction/build_eol_exam_draft.py for new calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.tools.extraction.build_eol_exam_draft import main


if __name__ == "__main__":
    main()
