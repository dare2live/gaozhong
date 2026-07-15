#!/usr/bin/env python3
"""Rebuild 2021/2022 cloze options sidecar from EOL docx.

Output: data/structured/exam_point/cloze_options_eol_xgkii.jsonl
Consumed by attribution.qualifying_cloze_rows (n_passages 10→12).
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/structured/exam_point/cloze_options_eol_xgkii.jsonl"
OPT_RE = re.compile(
    r"^(\d{2})\.\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)\s*$"
)


def _docx_paras(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras: list[str] = []
    for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        texts = [
            t.text or ""
            for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        ]
        line = "".join(texts).strip()
        if line:
            paras.append(line)
    return paras


def extract_year(year: int) -> dict:
    path = ROOT / f"data/external/exam_sources/eol/{year}_xgkii_english_eol.docx"
    blanks: dict[int, tuple[str, str, str, str]] = {}
    for p in _docx_paras(path):
        m = OPT_RE.match(p.replace("\u3000", " "))
        if not m:
            continue
        n = int(m.group(1))
        if 41 <= n <= 55:
            blanks[n] = tuple(x.strip() for x in m.groups()[1:])  # type: ignore[assignment]
    if set(blanks) != set(range(41, 56)):
        raise SystemExit(f"{year}: expected blanks 41-55, got {sorted(blanks)}")
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    ans_rows = con.execute(
        "SELECT question_id, answer FROM exam_questions "
        "WHERE question_type='完形填空' AND question_id LIKE ? ORDER BY question_id",
        [f"eol/{year}/xgkii/%"],
    ).fetchall()
    con.close()
    by_n: dict[int, str] = {}
    for qid, ans in ans_rows:
        n = int(qid.rsplit("/", 1)[-1])
        if 41 <= n <= 55:
            by_n[n] = (ans or "").strip()
    letters = [by_n[n] for n in range(41, 56)]
    if len(letters) != 15 or any(a not in "ABCD" for a in letters):
        raise SystemExit(f"{year}: bad answers {by_n}")
    opts = [blanks[n] for n in range(41, 56)]
    option_block = "\n".join(
        f"{n}. A. {a} B. {b} C. {c} D. {d}"
        for n, (a, b, c, d) in zip(range(41, 56), opts)
    )
    return {
        "year": year,
        "province": "辽宁",
        "paper_type": "新高考全国II卷",
        "question_id": f"eol/{year}/xgkii/41",
        "blank_ids": [f"eol/{year}/xgkii/{n}" for n in range(41, 56)],
        "answers": letters,
        "options": [{"A": a, "B": b, "C": c, "D": d} for a, b, c, d in opts],
        "option_block": option_block,
        "source_file": f"{year}_xgkii_english_eol.docx",
        "source_path": f"data/external/exam_sources/eol/{year}_xgkii_english_eol.docx",
        "provenance": "eol_docx_option_rebuild",
        "note": "2021/2022 cloze stored per-blank; options rebuilt from EOL docx",
    }


def main() -> None:
    rows = [extract_year(2021), extract_year(2022)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} years={[r['year'] for r in rows]}")


if __name__ == "__main__":
    main()
