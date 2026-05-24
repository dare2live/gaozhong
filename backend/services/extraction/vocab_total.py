"""抽 'Vocabulary' (字母 A-Z 全册总词表) 章节 — 补外研漏抓 (L-F).

外研版每册末有 2 个词表 section:
  'Words and expressions' (by-Unit, 已抽 by vocab.py)
  'Vocabulary' (字母 A-Z 全册总, 未抽 — 大量重复词跨 unit, 但也有不在 Words 里的)

策略: 抽 Vocabulary 章节所有 word, 归 unit_number=99 表示"全册总表 / 不归单元".
audit 把这些归到 cumulative_words_learned 算 + 5 年累计.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "structured" / "textbook"

# 简化 ENTRY_RE: 不要求 trailing 数字, 接受 multi-form (vt./vi.)
ENTRY_RE = re.compile(
    r"^\s*[*▫]?\s*"
    r"([a-zA-Z][a-zA-Z'\- ]*?)"
    r"\s+/[^/]+/\s*"
    r"([a-z]+\.(?:\s*&\s*[a-z]+\.)?)?"
    r"\s*(.+?)"
    r"(?:\s+\d{1,3})?\s*$"
)
VOLUME_SUMMARY_UNIT = 99


def _page_text(reader: PdfReader, pi: int) -> str:
    try: return reader.pages[pi].extract_text() or ""
    except Exception: return ""


def _find_vocabulary_pages(reader: PdfReader) -> tuple[int, int]:
    """Find Vocabulary section page range (after 'Words and expressions', before 'Names')."""
    start = -1; end = len(reader.pages)
    for pi in range(len(reader.pages)):
        t = _page_text(reader, pi)
        first = (t.split("\n", 1)[0] if t else "").strip()
        if start < 0 and first.startswith("Vocabulary"):
            start = pi
        elif start >= 0 and (first.startswith("Names") or first.startswith("Junior") or "后  记" in t):
            end = pi
            break
    return (start, end)


def _parse_line(line: str) -> tuple[str, str, str] | None:
    if not line or "Vocabulary" in line or len(line) <= 2: return None
    m = ENTRY_RE.match(line)
    if not m: return None
    word, pos, zh = m.groups()
    word = word.strip().lower()
    if not word or len(word) > 30: return None
    return word, (pos or "").rstrip("."), (zh or "").strip()


def extract_vocabulary_section(pdf_path: Path, version_key: str,
                                  volume_key: str) -> list[dict]:
    reader = PdfReader(pdf_path)
    s, e = _find_vocabulary_pages(reader)
    if s < 0:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for pi in range(s, e):
        for raw in _page_text(reader, pi).split("\n"):
            parsed = _parse_line(raw.rstrip())
            if not parsed: continue
            word, pos, zh = parsed
            if word in seen: continue
            seen.add(word)
            out.append({
                "version_key": version_key, "volume_key": volume_key,
                "unit_number": VOLUME_SUMMARY_UNIT, "word": word,
                "pos": pos, "zh_def": zh,
                "raw_marker": "from_Vocabulary_section",
            })
    return out


def run_all() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    per_vol: dict[str, int] = {}
    for ver in ("waiyan", "renjiao"):
        for pdf in sorted((TEXTBOOK_DIR / ver).glob("*.pdf")):
            rows = extract_vocabulary_section(pdf, ver, pdf.stem)
            all_rows.extend(rows)
            per_vol[f"{ver}/{pdf.stem}"] = len(rows)
    out_jsonl = OUT_DIR / "vocab_total_all.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"rows": len(all_rows), "per_vol": per_vol, "jsonl": str(out_jsonl.relative_to(ROOT))}


if __name__ == "__main__":
    print(json.dumps(run_all(), ensure_ascii=False, indent=2))
