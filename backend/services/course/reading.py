"""阅读理解练习加载 — 基于趋势引擎推荐的考点分布生成 (Phase 7.4).

从 backend/config/reading_exercises.yaml 读取, init_db 调用.
"""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "reading_exercises.yaml"


def load_reading_exercises() -> list[dict]:
    """读 yaml → list[dict] for question_bank insertion."""
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return [_to_qb_row(ex) for ex in data.get("reading_comprehension", [])]


def _to_qb_row(ex: dict) -> dict:
    return {
        "question_type": "阅读理解",
        "stem": (ex.get("stem") or "").strip(),
        "options_json": None,
        "answer": (ex.get("answer") or "").strip(),
        "difficulty": ex.get("difficulty", "hard"),
        "origin": "reading_exercise",
        "origin_ref": ex.get("id", ""),
        "analysis": (ex.get("analysis") or "").strip(),
    }
