"""人教版词表抽 — 双模式 (anchor / parenthesized Unit#).

实测排版差异:
  - bixiu_1, bixiu_3: 有 'Words and Expressions in Each Unit' header + ' Unit N' anchor
  - bixiu_2:          只有页码 (e.g. '101'), 末括号 (N) 标 Unit
  - xuanze_1..4:      'Appendices' header, 词条行末 '(N)' 标 Unit (N = 1..5)

统一策略:
  1. 扫整个 PDF 找"词条密集页" (≥ 8 个词条匹配/页) — 自动定位 vocab section
  2. 优先用行末 `(N)` 抽 Unit#; 退到 ' Unit N' anchor; 都没有视为 unit_number=None (skip)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "structured" / "textbook"

# Entry: word /ipa/ pos. zh_def [(N)]
ENTRY_RE = re.compile(
    r"^\s*([a-zA-Z][a-zA-Z'\- ]*?)"
    r"\s+/[^/]+/\s*"
    r"([a-z]+\.(?:\s*&\s*[a-z]+\.)?)"
    r"\s*(.*?)"
    r"(?:\s*\((\d+|w)\))?"
    r"\s*$"
)
UNIT_ANCHOR_RE = re.compile(r"^\s+Unit\s+(\d+)\s*$")
ENTRY_MIN_PER_PAGE = 8


def _page_text(reader: PdfReader, pi: int) -> str:
    try:
        return reader.pages[pi].extract_text() or ""
    except Exception:
        return ""


def _entry_count(text: str) -> int:
    return sum(1 for ln in text.split("\n") if ENTRY_RE.match(ln))


def _find_vocab_pages(reader: PdfReader) -> list[int]:
    """Return 0-indexed pages with ≥ N entries — i.e. vocab section pages."""
    return [pi for pi in range(len(reader.pages))
            if _entry_count(_page_text(reader, pi)) >= ENTRY_MIN_PER_PAGE]


def _parse_entry(line: str) -> tuple[str, str, str, int | None] | None:
    """(word, pos, zh_def, unit_n_if_known) or None."""
    if "Words and Expressions" in line or line.startswith("Appendices"):
        return None
    m = ENTRY_RE.match(line)
    if not m:
        return None
    word_raw, pos, zh, unit_str = m.groups()
    word = word_raw.strip().lower()
    if not word or len(word) > 30:
        return None
    unit_n: int | None = None
    if unit_str and unit_str.isdigit():
        unit_n = int(unit_str)
    return (word, pos.rstrip("."), zh.strip(), unit_n)


def extract_renjiao_vocab(pdf_path: Path, volume_key: str) -> list[dict]:
    reader = PdfReader(pdf_path)
    pages = _find_vocab_pages(reader)
    if not pages:
        return []
    out: list[dict] = []
    seen: set[tuple[str, int]] = set()
    current_unit: int | None = None
    for pi in pages:
        for raw in _page_text(reader, pi).split("\n"):
            line = raw.rstrip()
            # anchor 行 ' Unit N'
            am = UNIT_ANCHOR_RE.match(line)
            if am:
                try:
                    current_unit = int(am.group(1))
                except ValueError:
                    pass
                continue
            parsed = _parse_entry(line)
            if not parsed:
                continue
            word, pos, zh, unit_from_paren = parsed
            unit_n = unit_from_paren if unit_from_paren is not None else current_unit
            if unit_n is None:
                continue
            key = (word, unit_n)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "version_key": "renjiao", "volume_key": volume_key,
                "unit_number": unit_n, "word": word,
                "pos": pos, "zh_def": zh, "raw_marker": "",
            })
    return out


def run_all() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"volumes": 0, "rows": 0, "per_volume": {}}
    all_rows: list[dict] = []
    for pdf in sorted((TEXTBOOK_DIR / "renjiao").glob("*.pdf")):
        rows = extract_renjiao_vocab(pdf, pdf.stem)
        all_rows.extend(rows)
        summary["volumes"] += 1
        summary["rows"] += len(rows)
        summary["per_volume"][pdf.stem] = len(rows)
    out_jsonl = OUT_DIR / "vocab_intro_renjiao.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary["jsonl"] = str(out_jsonl.relative_to(ROOT))
    return summary


if __name__ == "__main__":
    s = run_all()
    print(json.dumps(s, ensure_ascii=False, indent=2))
