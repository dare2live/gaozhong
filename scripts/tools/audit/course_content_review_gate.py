#!/usr/bin/env python3
"""Phase D 课节正文 review gate — 北极星 §6 硬门.

用法: python3 scripts/tools/audit/course_content_review_gate.py [--strict]
exit 0 = 全部 artifact 过词量/10-gram/考点锚定/政治词; 无 artifact 时诚实 OK(空集).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.course.content import CONTENT_DIR, all_pending_or_pass
from backend.services.course.lexicon_filter import allowed_words_for, expand_morphology
from backend.services.course.scenarios import _tokens, has_political_word, has_textbook_copy
from scripts.lib.db_lock import connect_readonly_with_retry

DB = ROOT / "data" / "db" / "gaozhong.duckdb"
_TOK = re.compile(r"[A-Za-z]+")


def _check_one(con, item: dict) -> list[str]:
    fails: list[str] = []
    seq = item.get("seq")
    body = (item.get("body_en") or "").strip()
    if not body:
        fails.append(f"seq={seq}: empty body_en")
        return fails
    layer = item.get("layer") or "G_FINAL"
    allowed = expand_morphology(set(allowed_words_for(con, layer)))
    oov = sorted({t for t in _tokens(body) if t not in allowed and len(t) > 1})
    if oov:
        fails.append(f"seq={seq}: OOV@{layer} {oov[:12]}")
    hit = has_textbook_copy(con, body)
    if hit:
        fails.append(f"seq={seq}: 10-gram textbook overlap {hit!r}")
    pol = has_political_word(body) or has_political_word(item.get("body_zh") or "")
    if pol:
        fails.append(f"seq={seq}: political word {pol!r}")
    pts = item.get("covers_exam_points") or []
    if not pts or not any(str(p).startswith("exam_point:") for p in pts):
        fails.append(f"seq={seq}: missing exam_point covers")
    focus = item.get("focus")
    if focus and f"exam_point:theme_l2:{focus}" not in pts and f"exam_point:genre:{focus}" not in pts:
        # theme_l2 试点要求 focus ∈ covers
        if not any(focus in str(p) for p in pts):
            fails.append(f"seq={seq}: focus {focus!r} not in covers_exam_points")
    st = (item.get("review") or {}).get("status")
    if st not in ("pass", "pending", "fail"):
        fails.append(f"seq={seq}: review.status invalid {st!r}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    items = all_pending_or_pass()
    if not items:
        print("OK (no course_content artifacts — empty set honest)")
        return 0
    con = connect_readonly_with_retry(str(DB))
    try:
        fails: list[str] = []
        for it in items:
            bad = _check_one(con, it)
            if bad and (it.get("review") or {}).get("status") == "pass":
                fails.extend([f"PASS_BUT_FAIL {x}" for x in bad])
            else:
                fails.extend(bad)
        if fails:
            print("FAIL review gate:")
            for f in fails:
                print(" ", f)
            return 1
        print(f"OK {len(items)} artifact(s) under {CONTENT_DIR.relative_to(ROOT)}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
