"""听力文字稿讲解辅助 — 单一计算点 (Rule 1).

真相源 = data/structured/exam_point/listening_transcript_teaching.jsonl
(每条须能对 question_bank.stem/answer/transcript 核验; provenance=agent_transcript_grounded)。
API / 前端只读本模块, 禁止重写同款启发式。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
JSONL = ROOT / "data" / "structured" / "exam_point" / "listening_transcript_teaching.jsonl"

REQUIRED_KEYS = (
    "origin_ref",
    "year",
    "q",
    "section",
    "skill",
    "answer",
    "answer_text",
    "answer_support",
    "distractors",
    "easy_to_miss",
    "technique",
    "how_to",
    "provenance",
)


def jsonl_path() -> Path:
    return JSONL


@lru_cache(maxsize=1)
def _load_all() -> dict[str, dict[str, Any]]:
    if not JSONL.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ref = row.get("origin_ref")
            if ref:
                out[str(ref)] = row
    return out


def clear_cache() -> None:
    _load_all.cache_clear()


def all_aids() -> list[dict[str, Any]]:
    rows = list(_load_all().values())
    rows.sort(key=lambda r: (int(r.get("year") or 0), int(r.get("q") or 0)))
    return rows


def get_aid(origin_ref: str | None) -> dict[str, Any] | None:
    if not origin_ref:
        return None
    return _load_all().get(origin_ref)


def summary() -> dict[str, Any]:
    rows = all_aids()
    by_year: dict[int, int] = {}
    by_skill: dict[str, int] = {}
    by_section: dict[str, int] = {}
    for r in rows:
        y = int(r.get("year") or 0)
        by_year[y] = by_year.get(y, 0) + 1
        sk = str(r.get("skill") or "?")
        by_skill[sk] = by_skill.get(sk, 0) + 1
        sec = str(r.get("section") or "?")
        by_section[sec] = by_section.get(sec, 0) + 1
    return {
        "n": len(rows),
        "by_year": dict(sorted(by_year.items())),
        "by_skill": dict(sorted(by_skill.items(), key=lambda kv: -kv[1])),
        "by_section": by_section,
        "provenance": "agent_transcript_grounded",
        "honesty": (
            "讲解锚定题干选项+文字稿; 音频为第三方核验档非 NEEA 官方原声; "
            "干扰项归类为可核验启发式, 非官方评分细则。"
        ),
    }
