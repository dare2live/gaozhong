"""教材 PDF → units (Unit 边界切分).

策略 (架构 §0 Rule 1 单一计算点):
  1. 先 try PDF outline (外研版多数册可用)
  2. 失败 → 扫所有页第一行 regex "^(WELCOME UNIT|UNIT N|Unit N)"
  3. 同 Unit 多次出现 (主体+workbook 重复页眉) → 取最小页 = start_page
  4. end_page = 下一 Unit start_page - 1, 末册到 total_pages
  5. 输出 jsonl + 入 units 表 + 建 in_volume edge

明确不做 (留 STEP 2 第二刀):
  - section 二级切 (Reading/Listening/Writing/...)
  - 词表 vocabulary 抽
  - 跨 PDF embedding 嵌入

抽取置信度 (extraction_method):
  outline   完美 (PDF 书签源信息)
  regex_min 较好 (regex 命中, 取最小页防止 workbook 干扰)
  empty     失败 (放入 manifest 但 units=[] 留 STEP 2 重试)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "structured" / "textbook"

UNIT_RE = re.compile(r"^\s*(WELCOME UNIT|UNIT\s+(\d+)|Unit\s+(\d+))\s*(.*)$", re.IGNORECASE)
UNIT_TITLE_CLEAN = re.compile(r"\s+\d+\s*$")  # trailing page number e.g. "UNIT 1 ART 9"


def _from_outline(reader: PdfReader) -> list[dict]:
    """Return [{unit_number, title_en, start_page, method='outline'}, ...]"""
    items: list[tuple[int, str, int]] = []  # (unit_number, title, start_page)
    try:
        outline = reader.outline
    except Exception:
        return []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
            return
        title = (getattr(o, "title", None) or "").strip()
        if not title:
            return
        m = re.search(r"Unit\s*(\d+)", title, re.I)
        if not m:
            if re.search(r"Welcome", title, re.I):
                unit_num = 0
            else:
                return
        else:
            unit_num = int(m.group(1))
        try:
            page = reader.get_destination_page_number(o) + 1
        except Exception:
            return
        items.append((unit_num, title, page))

    walk(outline)
    # dedup keep first per unit
    seen, out = set(), []
    for un, title, pg in sorted(items, key=lambda r: r[2]):
        if un in seen: continue
        seen.add(un)
        out.append({"unit_number": un, "title_en": title, "start_page": pg, "method": "outline"})
    return out


def _classify_unit_header(head_block: str) -> tuple[int, str] | None:
    """Parse head_block (first ~3 lines concatenated). Return (unit_num, title) or None."""
    m = UNIT_RE.match(head_block)
    if not m:
        return None
    if m.group(1).upper().startswith("WELCOME"):
        return (0, "WELCOME UNIT")
    num_str = m.group(2) or m.group(3)
    try:
        unit_num = int(num_str)
    except (TypeError, ValueError):
        return None
    tail = UNIT_TITLE_CLEAN.sub("", (m.group(4) or "").strip())
    return (unit_num, f"UNIT {unit_num} {tail}".rstrip())


def _page_head_block(reader: PdfReader, pi: int) -> str:
    try:
        txt = reader.pages[pi].extract_text() or ""
    except Exception:
        return ""
    return " ".join(line.strip() for line in txt.split("\n")[:3] if line.strip())[:80]


def _from_regex(reader: PdfReader) -> list[dict]:
    """页眉式 'UNIT N TITLE' 扫描. 同 N 取最小页.
    某些 PDF (eg 外研 xuanze_3/4) 把 'UNIT' 和数字拆两行, 所以合并前 3 行再 match."""
    hits: dict[int, tuple[int, str]] = {}
    for pi in range(len(reader.pages)):
        result = _classify_unit_header(_page_head_block(reader, pi))
        if result is None:
            continue
        unit_num, title = result
        if unit_num not in hits or (pi + 1) < hits[unit_num][0]:
            hits[unit_num] = (pi + 1, title)
    return [
        {"unit_number": u, "title_en": t, "start_page": p, "method": "regex_min"}
        for u, (p, t) in sorted(hits.items(), key=lambda kv: kv[1][0])
    ]


def extract_units(pdf_path: Path, version_key: str, volume_key: str) -> dict:
    """Returns {volume meta + units[]}. 不抛, 失败 units=[]."""
    reader = PdfReader(pdf_path)
    n_pages = len(reader.pages)
    units = _from_outline(reader)
    if len(units) < 2:
        units = _from_regex(reader)
    units.sort(key=lambda u: u["start_page"])
    # fill end_page
    for i, u in enumerate(units):
        u["end_page"] = units[i + 1]["start_page"] - 1 if i + 1 < len(units) else n_pages
    return {
        "version_key": version_key,
        "volume_key": volume_key,
        "n_pages": n_pages,
        "n_units": len(units),
        "method": units[0]["method"] if units else "empty",
        "units": units,
    }


def run_all() -> dict:
    """扫 data/textbooks/{waiyan,renjiao}/*.pdf, 落 data/structured/textbook/<ver>/<vol>.json"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"volumes": 0, "units_total": 0, "by_method": {}}
    all_volumes: list[dict] = []
    for ver_dir in sorted(TEXTBOOK_DIR.iterdir()):
        if not ver_dir.is_dir(): continue
        for pdf in sorted(ver_dir.glob("*.pdf")):
            rec = extract_units(pdf, ver_dir.name, pdf.stem)
            all_volumes.append(rec)
            (OUT_DIR / f"{ver_dir.name}_{pdf.stem}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            summary["volumes"] += 1
            summary["units_total"] += rec["n_units"]
            summary["by_method"][rec["method"]] = summary["by_method"].get(rec["method"], 0) + 1
    # 汇总 jsonl (init_db load 用)
    units_jsonl = OUT_DIR / "units_all.jsonl"
    with units_jsonl.open("w", encoding="utf-8") as fh:
        for v in all_volumes:
            for u in v["units"]:
                fh.write(json.dumps({
                    "version_key": v["version_key"],
                    "volume_key": v["volume_key"],
                    "unit_number": u["unit_number"],
                    "title_en": u["title_en"],
                    "page_start": u["start_page"],
                    "page_end": u["end_page"],
                    "extract_method": u["method"],
                }, ensure_ascii=False) + "\n")
    summary["jsonl"] = str(units_jsonl.relative_to(ROOT))
    return summary


if __name__ == "__main__":
    s = run_all()
    print(json.dumps(s, ensure_ascii=False, indent=2))
