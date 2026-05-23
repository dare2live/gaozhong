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


def _build_anchor_re(anchors: list[str]) -> re.Pattern:
    # match anchor at line start, allow extra title text after
    return re.compile(r"^\s*(" + "|".join(re.escape(a) for a in anchors)
                      + r")\b", re.IGNORECASE)


def _page_head_lines(reader: PdfReader, pi: int, n: int = 3) -> list[str]:
    try:
        t = reader.pages[pi].extract_text() or ""
    except Exception:
        return []
    return [ln.strip() for ln in t.split("\n")[:n] if ln.strip()]


def _scan_unit(reader: PdfReader, page_start: int, page_end: int,
               anchor_re: re.Pattern) -> list[tuple[int, str, str]]:
    """Return [(page, anchor_match, head_line), ...] within [start, end] (1-indexed)."""
    out = []
    seen_anchor_at_page: dict[str, int] = {}  # anchor → first page
    for pi in range(page_start - 1, min(page_end, len(reader.pages))):
        for line in _page_head_lines(reader, pi, n=3):
            m = anchor_re.match(line)
            if not m:
                continue
            anchor = m.group(1)
            # 同 anchor 在 unit 内多次出现 (跨页 section) → 取第一次
            if anchor in seen_anchor_at_page:
                continue
            seen_anchor_at_page[anchor] = pi + 1
            out.append((pi + 1, anchor, line))
            break
    out.sort(key=lambda r: r[0])
    return out


def extract_sections_for_unit(reader: PdfReader, version_key: str, volume_key: str,
                              unit_number: int, page_start: int, page_end: int) -> list[dict]:
    anchors = ANCHORS.get(version_key, [])
    if not anchors:
        return []
    anchor_re = _build_anchor_re(anchors)
    hits = _scan_unit(reader, page_start, page_end, anchor_re)
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
