"""Phase D 课节正文 — 模块化单目录加载 (坑8: 可整体增删, 不散落).

真相源: data/structured/course_content/*.json
入库前必过 review_gate (scripts/tools/audit/course_content_review_gate.py).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTENT_DIR = ROOT / "data" / "structured" / "course_content"


@lru_cache(maxsize=1)
def _index() -> dict[int, dict]:
    """seq → content payload (仅 review_status=pass 可挂 syllabus)."""
    out: dict[int, dict] = {}
    if not CONTENT_DIR.is_dir():
        return out
    for path in sorted(CONTENT_DIR.glob("seg-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        seq = int(raw["seq"])
        out[seq] = {
            "seq": seq,
            "segment_id": raw.get("segment_id") or f"seg-{seq:02d}",
            "layer": raw.get("layer", "G_FINAL"),
            "title_zh": raw.get("title_zh", ""),
            "body_en": raw.get("body_en", ""),
            "body_zh": raw.get("body_zh", ""),
            "covers_exam_points": list(raw.get("covers_exam_points") or []),
            "exam_grounded": raw.get("exam_grounded") or {},
            "review": raw.get("review") or {},
            "source_file": str(path.relative_to(ROOT)),
            "phase": "D_pilot",
        }
    return out


def reload() -> None:
    _index.cache_clear()


def content_for_seq(seq: int) -> dict | None:
    """挂到 syllabus lesson: 仅 review.status==pass; 否则 None (前端显示「本节暂无正文」)."""
    item = _index().get(int(seq))
    if not item:
        return None
    st = (item.get("review") or {}).get("status")
    if st != "pass":
        return None
    return item


def all_pending_or_pass() -> list[dict]:
    """review gate 扫全量 artifact (含未 pass)."""
    reload()
    if not CONTENT_DIR.is_dir():
        return []
    items = []
    for path in sorted(CONTENT_DIR.glob("seg-*.json")):
        items.append(json.loads(path.read_text(encoding="utf-8")))
    return items
