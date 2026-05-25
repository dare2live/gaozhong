"""听力练习加载 — 短对话/长对话/独白入 question_bank (Phase 7.2).

从 backend/config/listening_exercises.yaml 读取, init_db 调用.
长对话/独白 每段多题 → 展开为多行 question_bank (共享 transcript).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "listening_exercises.yaml"

QTYPE_MAP = {
    "short": "听力短对话",
    "dialog": "听力长对话",
    "passage": "听力独白",
}


def load_listening_exercises() -> list[dict]:
    """读 yaml → list[dict] for question_bank insertion."""
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    rows: list[dict] = []
    for ex in data.get("short_dialogs", []):
        rows.append(_short_to_qb(ex))
    for ex in data.get("extra_short_dialogs", []):
        rows.append(_short_to_qb(ex))
    for ex in data.get("long_dialogs", []):
        rows.extend(_multi_to_qb(ex, "dialog"))
    for ex in data.get("extra_long_dialogs", []):
        rows.extend(_multi_to_qb(ex, "dialog"))
    for ex in data.get("monologues", []):
        rows.extend(_multi_to_qb(ex, "passage"))
    return rows


def _short_to_qb(ex: dict) -> dict:
    return {
        "question_type": QTYPE_MAP["short"],
        "stem": (ex.get("stem") or "").strip(),
        "options_json": None,
        "answer": (ex.get("answer") or "").strip(),
        "difficulty": ex.get("difficulty", "mid"),
        "origin": "listening_exercise",
        "origin_ref": ex.get("id", ""),
        "analysis": (ex.get("analysis") or "").strip(),
        "has_audio": True,
        "audio_id": ex.get("audio_id", ""),
        "transcript": (ex.get("transcript") or "").strip(),
        "audio_speakers": json.dumps(ex.get("speakers", []), ensure_ascii=False),
        "audio_duration": ex.get("audio_duration"),
    }


def _multi_to_qb(ex: dict, kind: str) -> list[dict]:
    """长对话/独白: 1 段 transcript → N 道题, 共享 transcript + audio_id."""
    transcript = (ex.get("transcript") or "").strip()
    audio_id = ex.get("audio_id", "")
    speakers = json.dumps(ex.get("speakers", []), ensure_ascii=False)
    duration = ex.get("audio_duration")
    difficulty = ex.get("difficulty", "mid")
    base_id = ex.get("id", "")
    rows = []
    for i, q in enumerate(ex.get("questions", []), 1):
        rows.append({
            "question_type": QTYPE_MAP[kind],
            "stem": (q.get("stem") or "").strip(),
            "options_json": None,
            "answer": (q.get("answer") or "").strip(),
            "difficulty": difficulty,
            "origin": "listening_exercise",
            "origin_ref": f"{base_id}/q{i}",
            "analysis": (q.get("analysis") or "").strip(),
            "has_audio": True,
            "audio_id": audio_id,
            "transcript": transcript,
            "audio_speakers": speakers,
            "audio_duration": duration,
        })
    return rows
