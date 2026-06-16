"""教材 Unit 内 section 切分 (STEP 2 第三刀, M1 收尾).

策略 (按 PDF 实测):
  - 外研版 outline 只到 Unit, section 用 regex 扫 unit 页范围
  - 人教版无 outline, 同样 regex 扫
共用 anchor 词典 (页眉首行匹配):
  ANCHORS_WAIYAN = ["Starting out", "Understanding ideas", "Using language",
                    "Developing ideas", "Presenting ideas", "Reflection",
                    "Project", "Self-assessment"]
  ANCHORS_RENJIAO = ["Reading and Thinking", "Reading and Writing",
                     "Listening and Speaking", "Listening and Talking",
                     "Discovering Useful Structures", "Assessing Your Progress",
                     "Workbook", "Project"]
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "structured" / "textbook"

ANCHORS = {
    "waiyan": [
        "Starting out", "Understanding ideas", "Using language",
        "Developing ideas", "Presenting ideas", "Reflection",
        "Project", "Self-assessment", "Integrated skills",
        "Grammar", "Vocabulary", "Listening", "Speaking", "Reading", "Writing",
    ],
    "renjiao": [
        "Reading and Thinking", "Reading and Writing",
        "Listening and Speaking", "Listening and Talking",
        "Discovering Useful Structures", "Assessing Your Progress",
        "Workbook", "Project", "Reading for Writing",
        "Video Time", "Words in Use", "Listening", "Speaking",
        "Grammar", "Vocabulary", "Reading", "Writing",
    ],
}

# anchor → kind (统一分类)
KIND_MAP = {
    "Starting out": "Intro", "Understanding ideas": "Reading",
    "Using language": "Grammar", "Developing ideas": "Reading",
    "Presenting ideas": "Speaking", "Reflection": "Review",
    "Project": "Project", "Self-assessment": "Review",
    "Integrated skills": "Integrated",
    "Reading and Thinking": "Reading", "Reading and Writing": "Writing",
    "Reading for Writing": "Writing",
    "Listening and Speaking": "Listening",
    "Listening and Talking": "Listening",
    "Discovering Useful Structures": "Grammar",
    "Assessing Your Progress": "Review", "Workbook": "Workbook",
    "Video Time": "Listening", "Words in Use": "Vocabulary",
    "Grammar": "Grammar", "Vocabulary": "Vocabulary",
    "Listening": "Listening", "Speaking": "Speaking",
    "Reading": "Reading", "Writing": "Writing",
}


# 辨识度高的多词 section 标题: 整页扫安全 (不会在正文误命中); 单词锚点 (Project/Grammar/Reading/
# Writing/Listening/Speaking/Vocabulary/Workbook) 仅页首匹配, 防正文常用词误报。
# 修复 (2026-06-16): 10 个 waiyan 单元页首是练习正文、section 标题在页中, 仅扫前3行漏 → pass-2 整页扫这些。
_DISTINCTIVE = frozenset({
    "Starting out", "Understanding ideas", "Using language", "Developing ideas",
    "Presenting ideas", "Reflection", "Integrated skills", "Self-assessment",
    "Reading and Thinking", "Reading and Writing", "Reading for Writing",
    "Listening and Speaking", "Listening and Talking",
    "Discovering Useful Structures", "Assessing Your Progress",
    "Words in Use", "Video Time",
})


def _build_anchor_re(anchors: list[str]) -> re.Pattern:
    # match anchor at line start, allow extra title text after
    return re.compile(r"^\s*(" + "|".join(re.escape(a) for a in anchors)
                      + r")\b", re.IGNORECASE)


def _build_distinctive_re(anchors: list[str]) -> re.Pattern | None:
    """该版本 anchors ∩ _DISTINCTIVE 的整页匹配 regex (无锚定行首); 无则 None."""
    distinctive = [a for a in anchors if a in _DISTINCTIVE]
    if not distinctive:
        return None
    return re.compile(r"(" + "|".join(re.escape(a) for a in distinctive) + r")\b", re.IGNORECASE)


def _page_head_lines(reader: PdfReader, pi: int, n: int = 3) -> list[str]:
    try:
        t = reader.pages[pi].extract_text() or ""
    except Exception:
        return []
    return [ln.strip() for ln in t.split("\n")[:n] if ln.strip()]


def _page_full_text(reader: PdfReader, pi: int) -> str:
    try:
        return reader.pages[pi].extract_text() or ""
    except Exception:
        return ""


def _scan_head(reader: PdfReader, pages: list[int], anchor_re: re.Pattern,
               seen: dict[str, int], out: list) -> None:
    """pass-1: 页首前3行匹配任意锚点 (原行为, 每页首个, 同 anchor 取首次页)."""
    for pi in pages:
        for line in _page_head_lines(reader, pi, n=3):
            m = anchor_re.match(line)
            if m and m.group(1) not in seen:
                seen[m.group(1)] = pi + 1
                out.append((pi + 1, m.group(1), line))
                break


def _scan_distinctive(reader: PdfReader, pages: list[int], distinctive_re: re.Pattern,
                      seen: dict[str, int], out: list) -> None:
    """pass-2: 整页扫辨识度高的多词锚点 (兜底填 pass-1 漏的; 不在页首的 section 标题)."""
    for pi in pages:
        for line in _page_full_text(reader, pi).split("\n"):
            m = distinctive_re.search(line)
            if m and m.group(1) not in seen:
                seen[m.group(1)] = pi + 1
                out.append((pi + 1, m.group(1), line.strip()))


def _scan_unit(reader: PdfReader, page_start: int, page_end: int,
               anchor_re: re.Pattern, distinctive_re: re.Pattern | None = None
               ) -> list[tuple[int, str, str]]:
    """Return [(page, anchor, title), ...] within [start, end] (1-indexed).

    pass-1 (页首) 不动 working 单元; pass-2 仅当 pass-1 整单元零命中时兜底整页扫多词锚点
    (修 10 waiyan 单元页首是练习正文)。限"零命中"刻意收窄 blast-radius (narrow-enough-to-verify)。
    """
    out: list[tuple[int, str, str]] = []
    seen: dict[str, int] = {}
    pages = list(range(page_start - 1, min(page_end, len(reader.pages))))
    _scan_head(reader, pages, anchor_re, seen, out)
    if distinctive_re is not None and not out:
        _scan_distinctive(reader, pages, distinctive_re, seen, out)
    out.sort(key=lambda r: r[0])
    return out


def extract_sections_for_unit(reader: PdfReader, version_key: str, volume_key: str,
                              unit_number: int, page_start: int, page_end: int) -> list[dict]:
    anchors = ANCHORS.get(version_key, [])
    if not anchors:
        return []
    anchor_re = _build_anchor_re(anchors)
    hits = _scan_unit(reader, page_start, page_end, anchor_re, _build_distinctive_re(anchors))
    if not hits:
        return []
    rows = []
    for i, (pg, anchor, head) in enumerate(hits):
        nxt_pg = hits[i + 1][0] - 1 if i + 1 < len(hits) else page_end
        rows.append({
            "version_key": version_key, "volume_key": volume_key,
            "unit_number": unit_number, "seq": i + 1,
            "kind": KIND_MAP.get(anchor, "Other"),
            "title": head,
            "page_start": pg, "page_end": max(pg, nxt_pg),
        })
    return rows


def run_all(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    by_kind: dict[str, int] = {}
    # 用 DB 里的 units (前置: textbook unit extract 必须先跑)
    if con is None:
        import duckdb as _ddb
        con = _ddb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    units = con.execute("""
        SELECT version_key, volume_key, unit_number, page_start, page_end
        FROM units ORDER BY version_key, volume_key, unit_number
    """).fetchall()
    pdf_cache: dict[str, PdfReader] = {}
    for ver, vol, un, ps, pe in units:
        key = f"{ver}/{vol}"
        if key not in pdf_cache:
            pdf_path = TEXTBOOK_DIR / ver / f"{vol}.pdf"
            if not pdf_path.exists():
                continue
            pdf_cache[key] = PdfReader(pdf_path)
        sections = extract_sections_for_unit(
            pdf_cache[key], ver, vol, un, ps or 1, pe or 200)
        all_rows.extend(sections)
        for s in sections:
            by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1

    out_jsonl = OUT_DIR / "sections_all.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"sections_total": len(all_rows), "by_kind": by_kind,
            "units_scanned": len(units), "jsonl": str(out_jsonl.relative_to(ROOT))}


if __name__ == "__main__":
    s = run_all()
    print(json.dumps(s, ensure_ascii=False, indent=2))
