"""教材末 "Words and expressions" section → unit_vocab_intro 表.

排版样本 (外研版必修一 p112-120):
    senior /ˈsiːniə/ adj.  （地位、水平或级别）高的，... 1
    * homesick /ˈhəʊmˌsɪk/ adj.  想家的 14
    ▫ opposing /əˈpəʊzɪŋ/ adj.  ... 15

每行行末数字 = 该词首次引入的 Unit 编号 (外研 1-6).
前缀符号: `*` = 选学; `▫` = 复用词.

人教版词表在 APPENDICES "Words and Expressions in Each Unit" (p108 起), 按 Unit
分段而不是行尾数字 — 待 STEP 2 第三刀.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "structured" / "textbook"

# Word and expressions section 实际排版 (实测样本):
#   "UNIT 1" / "UNIT N TITLE" 段头独立一行 → current_unit = N
#   词条行: word /ipa/ pos.  zh_def [trailing num=lesson# 忽略]
# 行末数字曾被误抽为 Unit#, 见 docs/lessons_learned.md L-A.
ENTRY_RE = re.compile(
    r"^\s*([*▫])?\s*"            # marker
    r"([a-zA-Z][a-zA-Z'\- ]*?)"   # word
    r"\s+/[^/]+/\s+"              # ipa /.../
    r"([a-z]+\.)?\s*"             # pos
    r"(.+?)"                      # zh_def
    r"(?:\s+\d{1,3})?\s*$",       # optional trailing lesson# (discarded)
)
UNIT_HEADER_RE = re.compile(r"^\s*UNIT\s+(\d+)\s*(.*)$", re.IGNORECASE)


def _find_section_pages(reader: PdfReader, heading: str = "Words and expressions") -> list[int]:
    """Return 0-indexed page numbers where the section appears."""
    pages = _section_pages_from_outline(reader, heading)
    return pages or _section_pages_from_text(reader, heading)


def _section_pages_from_outline(reader: PdfReader, heading: str) -> list[int]:
    try:
        outline = reader.outline
    except Exception:
        return []
    if not outline:
        return []
    needle = heading.lower()
    out: list[int] = []
    for o in _walk_outline(outline):
        title = (getattr(o, "title", "") or "")
        if needle not in title.lower():
            continue
        try:
            out.append(reader.get_destination_page_number(o))
        except Exception:
            continue
    return out


def _section_pages_from_text(reader: PdfReader, heading: str) -> list[int]:
    needle = heading.lower()
    out: list[int] = []
    for pi in range(len(reader.pages)):
        try:
            t = reader.pages[pi].extract_text() or ""
        except Exception:
            continue
        head = "\n".join(t.split("\n", 3)[:3]).lower()
        if needle in head:
            out.append(pi)
    return out


def _walk_outline(o) -> Iterable:
    if isinstance(o, list):
        for x in o:
            yield from _walk_outline(x)
    else:
        yield o


def _next_section_page(reader: PdfReader, start: int, exclude_heading: str) -> int:
    """Find next page whose first line starts a *different* section (not exclude_heading)."""
    for pi in range(start + 1, len(reader.pages)):
        try:
            t = reader.pages[pi].extract_text() or ""
        except Exception:
            continue
        first = (t.split("\n", 1)[0] if t else "").strip()
        # heuristics: "Vocabulary" / "Names and places" / "Junior high"
        if first and exclude_heading.lower() not in first.lower():
            for marker in ("Vocabulary", "Names and places", "Junior high", "后  记"):
                if first.startswith(marker):
                    return pi
    return len(reader.pages)


def _parse_unit_header(line: str) -> int | None:
    """If line is a 'UNIT N' section header, return N; else None."""
    if not line:
        return None
    s = line.strip()
    # too long → probably not header
    if len(s) > 40:
        return None
    m = UNIT_HEADER_RE.match(s)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _parse_entry_line(line: str) -> tuple[str, str, str, str] | None:
    """Parse one entry. Return (marker, word, pos, zh_def) or None.
    NOTE: 不返回 unit#; 由扫描循环里 current_unit 跟踪."""
    if not line or "Words and expressions" in line or "Vocabulary" in line:
        return None
    m = ENTRY_RE.match(line.rstrip())
    if not m:
        return None
    marker, word, pos, zh = m.groups()
    word = word.strip().lower()
    if not word or len(word) > 30:
        return None
    return (marker or "", word, (pos or "").rstrip("."), (zh or "").strip())


def _page_text(reader: PdfReader, pi: int) -> str:
    try:
        return reader.pages[pi].extract_text() or ""
    except Exception:
        return ""


def extract_vocab_intro(pdf_path: Path, version_key: str, volume_key: str) -> list[dict]:
    reader = PdfReader(pdf_path)
    starts = _find_section_pages(reader, "Words and expressions")
    if not starts:
        return []
    s = starts[0]
    e = _next_section_page(reader, s, "Words and expressions")
    out: list[dict] = []
    seen: set[tuple[str, int]] = set()
    current_unit: int | None = None
    for pi in range(s, e):
        for raw in _page_text(reader, pi).split("\n"):
            line = raw.rstrip()
            # check UNIT N header first
            header_n = _parse_unit_header(line)
            if header_n is not None:
                current_unit = header_n
                continue
            if current_unit is None:
                continue
            parsed = _parse_entry_line(line)
            if not parsed:
                continue
            marker, word, pos, zh = parsed
            key = (word, current_unit)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "version_key": version_key, "volume_key": volume_key,
                "unit_number": current_unit, "word": word, "pos": pos,
                "zh_def": zh, "raw_marker": marker,
            })
    return out


def run_all() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"volumes": 0, "rows": 0, "by_version": {}}
    all_rows: list[dict] = []
    for ver_dir in sorted(TEXTBOOK_DIR.iterdir()):
        if not ver_dir.is_dir(): continue
        # 仅外研版 STEP 2 第二刀, 人教版词表排版不同, 留下一刀
        if ver_dir.name != "waiyan":
            continue
        for pdf in sorted(ver_dir.glob("*.pdf")):
            rows = extract_vocab_intro(pdf, ver_dir.name, pdf.stem)
            summary["volumes"] += 1
            summary["rows"] += len(rows)
            summary["by_version"][ver_dir.name] = summary["by_version"].get(ver_dir.name, 0) + len(rows)
            all_rows.extend(rows)
    out_jsonl = OUT_DIR / "vocab_intro_all.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary["jsonl"] = str(out_jsonl.relative_to(ROOT))
    return summary


if __name__ == "__main__":
    s = run_all()
    print(json.dumps(s, ensure_ascii=False, indent=2))
