"""修复 units.title_en — 外研版 outline 给的是 PDF 文件名 (e.g. 'B1-2 Unit 1.pdf'),
应抓真实英文主题 (eg "TEENAGE LIFE").

策略: 进每个 Unit 的 page_start, 抓首段内 'UNIT N' / 大写英文标题, 更新 units.title_en.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"

# Common patterns for unit theme in first 3 lines of unit start page
THEME_RE = re.compile(r"^\s*([A-Z][A-Z\s&]{4,40})\s*$")


def _read_unit_first_lines(pdf_path: Path, page_start: int, n_lines: int = 8) -> list[str]:
    try:
        reader = PdfReader(pdf_path)
        if page_start - 1 >= len(reader.pages):
            return []
        text = reader.pages[page_start - 1].extract_text() or ""
    except Exception:
        return []
    return [ln.strip() for ln in text.split("\n")[:n_lines] if ln.strip()]


def _pick_theme(lines: list[str]) -> str | None:
    """Pick first ALL-CAPS line ≥ 5 chars as theme."""
    for ln in lines:
        m = THEME_RE.match(ln)
        if m:
            title = m.group(1).strip()
            # skip noise like "UNIT", "SCOPE"
            if title in {"UNIT", "SCOPE", "PRESENTING"}:
                continue
            return title
    return None


# 外研版 Scope and sequence (p5-6) 解析格式:
#   '  P1' → 下一行非空 = unit 1 主题
#   '  P13' → unit 2 主题
SCOPE_PAGES = [4, 5]  # 0-indexed
PAGE_TAG_RE = re.compile(r"^\s+P(\d+)\s*$")


def _scan_scope_page(lines: list[str]) -> list[tuple[int, str]]:
    """Walk lines, after each 'Pnn' tag take next non-empty as theme."""
    out: list[tuple[int, str]] = []
    i, n = 0, len(lines)
    while i < n:
        m = PAGE_TAG_RE.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j < n:
            out.append((int(m.group(1)), lines[j].strip()))
        i = j + 1
    return out


def _scope_themes(pdf_path: Path) -> dict[int, str]:
    """Return {page_in_book: theme_title} from Scope and sequence."""
    try:
        r = PdfReader(pdf_path)
    except Exception:
        return {}
    pairs: list[tuple[int, str]] = []
    for spi in SCOPE_PAGES:
        if spi >= len(r.pages):
            continue
        try:
            t = r.pages[spi].extract_text() or ""
        except Exception:
            continue
        pairs.extend(_scan_scope_page(t.split("\n")))
    return dict(pairs)


def _map_unit_to_theme(pdf_path: Path, units: list[tuple]) -> dict[int, str]:
    """units = [(unit_number, page_start), ...]. Return {unit_number: theme}."""
    scope = _scope_themes(pdf_path)
    if not scope:
        return {}
    scope_pages = sorted(scope)
    out = {}
    for un, pg in units:
        # match scope page closest BUT <= pg
        candidates = [sp for sp in scope_pages if sp <= pg]
        if candidates:
            best = candidates[-1]
            theme = scope[best]
            if theme and len(theme) <= 60:
                out[un] = theme
    return out


def fix_titles(con: duckdb.DuckDBPyConnection) -> dict:
    """Replace filename-like title_en with real theme (from Scope and sequence)."""
    fixed = 0
    untouched = 0
    total = 0
    by_vol = con.execute("""
        SELECT version_key, volume_key,
               LIST({unit_number: unit_number, page_start: page_start})
        FROM units GROUP BY version_key, volume_key
    """).fetchall()
    for ver, vol, ulist in by_vol:
        units = [(u["unit_number"], u["page_start"]) for u in ulist if u["page_start"]]
        pdf_path = TEXTBOOK_DIR / ver / f"{vol}.pdf"
        if not pdf_path.exists() or not units:
            untouched += len(units); total += len(units); continue
        theme_map = _map_unit_to_theme(pdf_path, units)
        for un, pg in units:
            total += 1
            theme = theme_map.get(un)
            if not theme:
                untouched += 1; continue
            new_title = f"UNIT {un} {theme}"
            con.execute("""
                UPDATE units SET title_en=?
                WHERE version_key=? AND volume_key=? AND unit_number=?
            """, [new_title, ver, vol, un])
            fixed += 1
    return {"fixed": fixed, "untouched": untouched, "total": total}
