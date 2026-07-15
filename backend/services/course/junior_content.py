"""初中 Phase D 可背诵正文 — 独立目录, 不与高中 course_content 混载.

真相源: data/structured/junior_course_content/jr-seg-*.json
入库前必过 junior_course_content_review_gate.py (累计 hujiao 词量门, 禁 G_FINAL).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTENT_DIR = ROOT / "data" / "structured" / "junior_course_content"


@lru_cache(maxsize=1)
def _index() -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not CONTENT_DIR.is_dir():
        return out
    for path in sorted(CONTENT_DIR.glob("jr-seg-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        seq = int(raw["seq"])
        out[seq] = {
            "seq": seq,
            "segment_id": raw.get("segment_id") or f"jr-seg-{seq:02d}",
            "volume_key": raw.get("volume_key"),
            "unit_number": raw.get("unit_number"),
            "unit_concept_id": raw.get("unit_concept_id"),
            "layer": raw.get("layer", "hujiao_cumulative"),
            "title_zh": raw.get("title_zh", ""),
            "body_en": raw.get("body_en", ""),
            "body_zh": raw.get("body_zh", ""),
            "covers": list(raw.get("covers") or []),
            "exam_grounded": raw.get("exam_grounded") or {},
            "review": raw.get("review") or {},
            "source_file": str(path.relative_to(ROOT)),
            "phase": "junior_D_pilot",
        }
    return out


def reload() -> None:
    _index.cache_clear()


def content_for_jr_seq(seq: int) -> dict | None:
    """挂到 junior_syllabus lesson: 仅 review.status==pass."""
    item = _index().get(int(seq))
    if not item:
        return None
    if (item.get("review") or {}).get("status") != "pass":
        return None
    return item


def all_pending_or_pass() -> list[dict]:
    reload()
    if not CONTENT_DIR.is_dir():
        return []
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(CONTENT_DIR.glob("jr-seg-*.json"))
    ]
