#!/usr/bin/env python3
"""M0 真值基座核验：共享常量 + 文本/签名/清单底层工具.

被 truth_baseline_load / truth_baseline_report / truth_baseline_audit 复用,
本模块只依赖标准库, 不 import 任何 sibling 模块, 避免循环 import.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"
# 2026-06-17: 镜像进本项目, 不读姊妹项目 gaokao (互不干扰独立项目)。原 gaokao 真值基线 jsonl 已 cp 进 data/external/。
STRUCTURE_PATH = ROOT / "data" / "external" / "gaokao_xgkii_2021_2025_mirror.jsonl"
VERIFIED_JSONL = ROOT / "data" / "gaokao_verified_xgkii_2023_2024.jsonl"

TARGET_YEARS = [2021, 2022, 2023, 2024, 2025]
TARGET_MIN_COUNT = {2021: 55, 2022: 55}
QTYPE_MAP = {
    "reading_comprehension": "阅读理解",
    "grammar_fill": "语法填空",
    "cloze_fill_in_blanks": "完形填空",
    "seven_choose_five": "完形填空(七选五/语篇)",
    "error_correction": "短文改错",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip().lower())
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return text.strip()


def _textify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return " ".join(_textify(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def signature(year: int | None, qtype: str, text: str, answer: Any = "") -> str:
    norm = normalize_text(f"{qtype or ''}||{text or ''}||{_textify(answer)}")
    digest = hashlib.sha1((norm or str(year or "")).encode("utf-8")).hexdigest()
    return digest


def _token_set(text: Any) -> set[str]:
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, (dict, tuple)):
        text = json.dumps(text, ensure_ascii=False)
    return {w for w in re.findall(r"[a-z0-9]+", normalize_text(str(text))) if len(w) > 2}


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def manifest_hash() -> tuple[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    parts: list[str] = []
    for label, path in {
        "db": DB_PATH,
        "structured": STRUCTURE_PATH,
        "verified_jsonl": VERIFIED_JSONL,
    }.items():
        if not path.exists():
            entries[label] = {"path": str(path), "exists": False}
            continue
        st = path.stat()
        sig = f"{path}|{st.st_size}|{int(st.st_mtime_ns)}"
        entries[label] = {
            "path": str(path),
            "exists": True,
            "size": st.st_size,
            "mtime_ns": int(st.st_mtime_ns),
            "signature": hashlib.sha1(sig.encode("utf-8")).hexdigest(),
        }
        parts.append(entries[label]["signature"])
    run_id = hashlib.sha1(("|".join(parts) + "|" + now_iso()).encode("utf-8")).hexdigest()[:16]
    return run_id, entries


def _map_qtype(qtype: str) -> str:
    return QTYPE_MAP.get((qtype or "").strip(), qtype or "")


def _flatten_options(options: Any) -> str:
    if not isinstance(options, dict):
        return ""
    parts: list[str] = []
    for key in sorted(options.keys()):
        parts.append(f"{key}:{options[key]}")
    return " ".join(parts)
