#!/usr/bin/env python3
"""初中可背诵正文 review gate — 累计 hujiao 词量门 (禁 G_FINAL).

用法: python3 scripts/tools/audit/junior_course_content_review_gate.py
exit 0 = 全部 artifact 过词量/10-gram/单元锚定/政治词; 无 artifact 时诚实 OK(空集).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.course.junior_content import CONTENT_DIR, all_pending_or_pass
from backend.services.course.junior_lexicon import allowed_hujiao_through_expanded
from backend.services.course.scenarios import _tokens, has_political_word, has_textbook_copy
from scripts.lib.db_lock import connect_readonly_with_retry

DB = ROOT / "data" / "db" / "gaozhong.duckdb"


def _check_one(con: duckdb.DuckDBPyConnection, item: dict) -> list[str]:
    fails: list[str] = []
    seq = item.get("seq")
    body = (item.get("body_en") or "").strip()
    if not body:
        fails.append(f"seq={seq}: empty body_en")
        return fails
    layer = item.get("layer") or ""
    if layer in ("G1", "G2", "G3", "G_FINAL") or "G_FINAL" in str(layer):
        fails.append(f"seq={seq}: banned senior layer {layer!r}")
    vol = item.get("volume_key")
    unit = item.get("unit_number")
    if not vol or unit is None:
        fails.append(f"seq={seq}: missing volume_key/unit_number")
        return fails
    allowed = allowed_hujiao_through_expanded(con, str(vol), int(unit))
    oov = sorted({t for t in _tokens(body) if t not in allowed and len(t) > 1})
    if oov:
        fails.append(f"seq={seq}: OOV@hujiao_cumulative {oov[:12]}")
    hit = has_textbook_copy(con, body)
    if hit:
        fails.append(f"seq={seq}: 10-gram textbook overlap {hit!r}")
    pol = has_political_word(body) or has_political_word(item.get("body_zh") or "")
    if pol:
        fails.append(f"seq={seq}: political word {pol!r}")
    covers = item.get("covers") or []
    expect = f"unit:hujiao/{vol}/U{int(unit)}"
    if expect not in covers and not any(str(c).startswith("unit:hujiao/") for c in covers):
        fails.append(f"seq={seq}: missing unit cover (want {expect})")
    st = (item.get("review") or {}).get("status")
    if st not in ("pass", "pending", "fail"):
        fails.append(f"seq={seq}: review.status invalid {st!r}")
    return fails


def main() -> int:
    items = all_pending_or_pass()
    if not items:
        print("OK (no junior_course_content artifacts — empty set honest)")
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
            print("FAIL junior review gate:")
            for f in fails:
                print(" ", f)
            return 1
        print(f"OK {len(items)} artifact(s) under {CONTENT_DIR.relative_to(ROOT)}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
