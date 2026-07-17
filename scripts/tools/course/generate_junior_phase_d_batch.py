#!/usr/bin/env python3
"""Generate junior Phase D recitable bodies for all hujiao syllabus lessons.

Banks: backend/config/junior_phase_d_banks.json (module title → [(en, zh), ...]).
Lexicon: cumulative hujiao ∪ 义教 (ban G_FINAL). Must pass junior review gate.

    python3 -m scripts.tools.course.generate_junior_phase_d_batch [--force]
    python3 scripts/tools/audit/junior_course_content_review_gate.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.course.junior_content import CONTENT_DIR, reload
from backend.services.course.junior_knowledge import junior_syllabus
from backend.services.course.junior_lexicon import allowed_hujiao_through_expanded
from backend.services.course.scenarios import _tokens, has_political_word, has_textbook_copy

BANKS_PATH = ROOT / "backend/config/junior_phase_d_banks.json"


def _load_banks() -> dict[str, list[tuple[str, str]]]:
    raw = json.loads(BANKS_PATH.read_text(encoding="utf-8"))
    out: dict[str, list[tuple[str, str]]] = {}
    for title, pairs in raw.items():
        out[title] = [(p[0], p[1]) for p in pairs]
    return out


def _ok(con: duckdb.DuckDBPyConnection, body: str, vol: str, unit: int) -> list[str]:
    fails: list[str] = []
    allowed = allowed_hujiao_through_expanded(con, vol, unit)
    oov = sorted({t for t in _tokens(body) if t not in allowed and len(t) > 1})
    if oov:
        fails.append(f"OOV {oov[:20]}")
    hit = has_textbook_copy(con, body)
    if hit:
        fails.append(f"ngram {hit!r}")
    pol = has_political_word(body)
    if pol:
        fails.append(f"political {pol!r}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing jr-seg-*.json")
    args = ap.parse_args()

    banks = _load_banks()
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    today = date.today().isoformat()
    try:
        lessons = junior_syllabus(con)["lessons"]
        theme_i: dict[str, int] = {}
        written = 0
        skipped = 0
        errors: list[str] = []
        for les in lessons:
            seq = int(les["seq"])
            vol = les["volume_key"]
            unit = int(les["unit_number"])
            title = (les.get("title_en") or "").strip()
            path = CONTENT_DIR / f"jr-seg-{seq:02d}.json"
            if path.exists() and not args.force:
                skipped += 1
                theme_i[title] = theme_i.get(title, 0) + 1
                continue
            bank = banks.get(title) or []
            idx = theme_i.get(title, 0)
            theme_i[title] = idx + 1
            if idx >= len(bank):
                errors.append(f"seq={seq} title={title!r} bank exhausted idx={idx}")
                continue
            body_en, body_zh = bank[idx]
            bad = _ok(con, body_en, vol, unit)
            if bad:
                errors.append(f"seq={seq} {vol}/U{unit} {bad}")
                continue
            # political gate also checks Chinese
            pol_zh = has_political_word(body_zh)
            if pol_zh:
                errors.append(f"seq={seq} political_zh {pol_zh!r}")
                continue
            payload = {
                "seq": seq,
                "segment_id": f"jr-seg-{seq:02d}",
                "volume_key": vol,
                "unit_number": unit,
                "unit_concept_id": f"unit:hujiao/{vol}/U{unit}",
                "layer": "hujiao_cumulative",
                "title_zh": f"{title} — 第{seq}节可背诵讲义",
                "body_en": body_en,
                "body_zh": body_zh,
                "covers": [f"unit:hujiao/{vol}/U{unit}"],
                "exam_grounded": {
                    "axis": "textbook_unit",
                    "label": title,
                    "note": (
                        "组织轴=沪教教材单元; 非 theme_l2; 非押题。"
                        "词量门=累计 hujiao∪义教基底, 禁 G_FINAL"
                    ),
                },
                "review": {
                    "status": "pass",
                    "reviewed_at": today,
                    "checks": [
                        "lexicon_hujiao_cumulative",
                        "no_10gram_textbook",
                        "unit_grounded",
                        "no_political",
                    ],
                    "note": "junior Phase D batch via generate_junior_phase_d_batch + review_gate",
                },
            }
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            written += 1
        reload()
        print(f"written={written} skipped={skipped} errors={len(errors)}")
        for e in errors:
            print(" ERR", e)
        return 1 if errors else 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
