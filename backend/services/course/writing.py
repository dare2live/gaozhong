"""写作练习加载 — 续写 + 应用文入 question_bank (Phase 7.3).

从 backend/config/writing_exercises.yaml 读取, init_db 调用.
"""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "writing_exercises.yaml"


def load_writing_exercises() -> list[dict]:
    """读 yaml → list[dict] for question_bank insertion."""
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    rows = []
    for ex in data.get("narrative_continuation", []):
        rows.append(_to_qb_row(ex, "续写"))
    for ex in data.get("applied_writing", []):
        rows.append(_to_qb_row(ex, "应用文"))
    return rows


def _to_qb_row(ex: dict, qtype: str) -> dict:
    return {
        "question_type": qtype,
        "stem": (ex.get("stem") or "").strip(),
        "options_json": None,
        "answer": (ex.get("answer") or "").strip(),
        "difficulty": ex.get("difficulty", "mid"),
        "origin": "writing_exercise",
        "origin_ref": ex.get("id", ""),
        "analysis": (ex.get("analysis") or "").strip(),
    }
