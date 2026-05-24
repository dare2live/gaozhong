"""课标词汇表 (附录 2, p129-182) 抽取 — 从 extract_curriculum.py 拆出 (4.5).

减 extract_cefr_vocab CC 20 → ≤ 10.
"""
from __future__ import annotations

import re

from pypdf import PdfReader

MAIN_RE = re.compile(r"^([A-Za-z][A-Za-z\-'.]*)(\*{1,2})?$")
ALT_WORD_RE = re.compile(r"([A-Za-z][A-Za-z\-']{1,})")
ALT_SKIP_TOKENS = {"pl", "sing", "eg", "etc", "ie"}


def _level_of(suffix: str) -> str:
    if suffix.startswith("***"): return "选修"
    if suffix.startswith("**"): return "选必"
    if suffix.startswith("*"): return "必修"
    return "义教"


def _skip_line(line: str) -> bool:
    if not line: return True
    if line.startswith("│") or line.isdigit(): return True
    if len(line) == 1 and line.isalpha(): return True
    # 跳过中文说明
    if any("一" <= ch <= "鿿" for ch in line): return True
    return False


def _parse_main_token(tok: str) -> tuple[str, str] | None:
    m = MAIN_RE.match(tok)
    if not m: return None
    w = m.group(1).lower().rstrip(".")
    suffix = m.group(2) or ""
    return (w, suffix)


def _extract_alt_words(paren_groups: list[str]) -> list[str]:
    """Extract alt forms from '(an)' / '(pl. mice)' etc."""
    out = []
    for p in paren_groups:
        for a in ALT_WORD_RE.findall(p):
            aw = a.lower()
            if aw not in ALT_SKIP_TOKENS:
                out.append(aw)
    return out


def _process_line(line: str, seen: set[str], source_tag: str) -> list[dict]:
    rows = []
    paren = re.findall(r"\(([^)]*)\)", line)
    main_part = re.sub(r"\([^)]*\)", "", line).strip()
    for tok in main_part.split():
        parsed = _parse_main_token(tok)
        if not parsed: continue
        word, suffix = parsed
        if word and word not in seen:
            seen.add(word)
            rows.append({
                "word": word, "cefr_level": _level_of(suffix),
                "raw_suffix": suffix, "source": source_tag,
            })
        for alt_word in _extract_alt_words(paren):
            if alt_word not in seen:
                seen.add(alt_word)
                rows.append({
                    "word": alt_word, "cefr_level": _level_of(suffix),
                    "raw_suffix": suffix + " (alt)", "source": source_tag,
                })
        paren = []   # 只用第一个 token 的括号
    return rows


def extract_cefr_vocab(reader: PdfReader, source_tag: str,
                         start_page: int = 129, end_page: int = 182) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for pi in range(start_page - 1, end_page):
        if pi >= len(reader.pages): break
        text = reader.pages[pi].extract_text() or ""
        for raw in text.split("\n"):
            line = raw.strip()
            if _skip_line(line): continue
            rows.extend(_process_line(line, seen, source_tag))
    return rows
