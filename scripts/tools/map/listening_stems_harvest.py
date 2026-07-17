#!/usr/bin/env python3
"""Harvest 2022–2025 XGKII listening stems (parse only; no DB writes)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/external/exam_sources/listening_stems"

from scripts.tools.map.listening_stems_parse import (
    docx_text,
    expand_key,
    parse_qs,
    require_full_abc,
)


def harvest_2022() -> list[dict]:
    """Load curated zxxk stems+key from committed jsonl (source of truth)."""
    path = OUT / "2022_xgkii_listening_stems.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(rows) != 20:
        raise RuntimeError(f"2022 jsonl expected 20, got {len(rows)}")
    require_full_abc(2022, rows)
    key = "".join(r["answer"] for r in sorted(rows, key=lambda x: x["n"]))
    if key != "CBBCAABBCCBAACCABABC":
        raise RuntimeError(f"2022 key drift {key}")
    return sorted(rows, key=lambda x: x["n"])


def harvest_2023() -> list[dict]:
    docx = ROOT / "data/external/exam_sources/third_party_pdfs/2023_xgkii_english_gzenxx.docx"
    t = docx_text(docx)
    i = t.find("What will Jack probably do this weekend?")
    i = t.rfind("1.", 0, i)
    j = t.find("第二部分", i)
    qs = parse_qs(t[i:j])
    key = {
        1: "C", 2: "A", 3: "B", 4: "B", 5: "C",
        6: "C", 7: "B", 8: "A", 9: "B",
        10: "C", 11: "A", 12: "C", 13: "A",
        14: "B", 15: "A", 16: "C", 17: "C",
        18: "A", 19: "B", 20: "A",
    }
    if len(qs) != 20:
        raise RuntimeError(f"2023 expected 20 stems, got {sorted(qs)}")
    rows = [
        {
            "year": 2023,
            "n": n,
            "stem": qs[n]["stem"],
            "options": qs[n]["options"],
            "answer": key[n],
            "source": "gzenxx_docx;scribd_analysis_key",
        }
        for n in range(1, 21)
    ]
    require_full_abc(2023, rows)
    return rows


def harvest_2024() -> list[dict]:
    pdf_txt = Path("/tmp/2024_xgkii.txt")
    if not pdf_txt.exists():
        subprocess.run(
            [
                "pdftotext",
                "-layout",
                str(ROOT / "data/external/exam_sources/local_pdfs/2024_xgkii_english.pdf"),
                str(pdf_txt),
            ],
            check=True,
        )
    t = pdf_txt.read_text(encoding="utf-8", errors="replace")
    i = t.find("1. What did the woman do yesterday evening?")
    if i < 0:
        raise RuntimeError("2024 listening Q1 not found in PDF text")
    j = t.find("参考答案", i)
    if j < 0:
        j = t.find("第二部分", i)
    qs = parse_qs(t[i:j])
    export: dict[int, dict] = {}
    for line in (ROOT / "data/gaokao_export_2021_2025.jsonl").open(encoding="utf-8"):
        o = json.loads(line)
        if o.get("year") == 2024 and "听" in str(o.get("question_type")):
            export[int(o["question_number"])] = o
    rows = []
    for n in range(1, 21):
        if n not in qs or set(qs[n]["options"]) != {"A", "B", "C"}:
            raise RuntimeError(f"2024 Q{n} incomplete parse: {qs.get(n)}")
        ans = (export[n].get("answer") or "").strip()
        if ans not in "ABC":
            raise RuntimeError(f"2024 Q{n} bad answer {ans!r}")
        rows.append(
            {
                "year": 2024,
                "n": n,
                "stem": qs[n]["stem"],
                "options": qs[n]["options"],
                "answer": ans,
                "source": "local_pdf+gaokao_export",
            }
        )
    require_full_abc(2024, rows)
    return rows


def harvest_2025() -> list[dict]:
    analysis = (
        ROOT
        / "data/external/exam_sources/listening_transcripts/2025_xgkii_newdu_listening_analysis.txt"
    )
    stem_path = (
        ROOT
        / "data/external/exam_sources/listening_transcripts/2025_xgkii_newdu_listening_stem.txt"
    )
    t = stem_path.read_text(encoding="utf-8")
    m = re.search(r"1\.How will the woman.*?(?=1—5\s+[A-C]{5})", t, re.S)
    if not m:
        raise RuntimeError("2025 stem block not found")
    block = re.sub(r"(?m)^(\d{1,2})\.(?=\S)", r"\1. ", m.group(0))
    qs = parse_qs(block)
    if 4 in qs and "B" not in qs[4]["options"] and analysis.exists():
        am = re.search(
            r"4\.What is the man's major\?\s*"
            r"A\.Psychology\.\s*B\.Biology\.\s*C\.English\.",
            analysis.read_text(encoding="utf-8"),
            re.S,
        )
        if not am:
            raise RuntimeError("2025 Q4 ABC not found in analysis for B-patch")
        qs[4]["options"] = {
            "A": "Psychology.",
            "B": "Biology.",
            "C": "English.",
        }
    key_m = re.search(
        r"1—5\s+([A-C]{5})\s+6—10\s+([A-C]{5})\s+11—15\s+([A-C]{5})\s+16—20\s+([A-C]{5})",
        t,
    )
    if not key_m:
        raise RuntimeError("2025 answer key line not found")
    key = expand_key(list(key_m.groups()))
    if len(qs) != 20:
        raise RuntimeError(f"2025 expected 20, got {sorted(qs)}")
    rows = [
        {
            "year": 2025,
            "n": n,
            "stem": qs[n]["stem"],
            "options": qs[n]["options"],
            "answer": key[n],
            "source": "newdu_listening_stem+analysis_Q4B",
        }
        for n in range(1, 21)
    ]
    require_full_abc(2025, rows)
    return rows


def write_jsonl(year: int, rows: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{year}_xgkii_listening_stems.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path
