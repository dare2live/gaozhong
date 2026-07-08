"""沪教牛津(广深沈) 初中英语 6册 词表 unit级归属抽取 (Phase E4 knowledge lineage 补全).

背景: hujiao_vocab.jsonl(extract_hujiao_vocab.py 已有产物)只有grade粒度(七上/七下等),
无unit_number — 因为该脚本抽的是卷末"Words and expressions in alphabetical order"
(字母序总表), 天然不带单元归属。

真相源: 同一份卷末附录里**还有一份"Words and expressions in each unit"**(按单元排列
的同一批词, 逐条查证过, 见 data/junior_high/textbooks/hujiao/7a.pdf 页123起), 每个单元
以独立"Unit N"标题行开头, 后续词条直到下一个"Unit N"标题前都属于该单元。**词条后的
"p. N"是单元内部页码(如Unit1第1页/第2页...), 不是全书绝对页码**, 本抽取器不使用它,
只用"Unit N"标题作单元边界(逐条核实过: 该行必为独立一行, 不与词条同行)。

区间定位: 从各册已知的Appendices起点(见 extract_hujiao_sections.py._backmatter_start
同一批已验证值)开始找第一个独立"Unit 1"行(防止匹配到正文里的Unit1主题页标题),
到"Words and expressions in alphabetical order"标题行(page级别检测, 不逐行检测防止
同页内提前误截断, 已实测踩过这个坑)结束。

emit: data/junior_high/structured/hujiao_vocab_unit.jsonl (version, volume_key,
unit_number, word) — 与 hujiao_vocab.jsonl 按word JOIN 取 pos/zh_def, 不重复抽取释义
(Rule1单一计算点)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.extract_hujiao_vocab import _ENTRY, _col_lines  # noqa: E402
TB = ROOT / "data" / "junior_high" / "textbooks" / "hujiao"
OUT = ROOT / "data" / "junior_high" / "structured"
VOLUMES = ("7a", "7b", "8a", "8b", "9a", "9b")
# 复用 extract_hujiao_sections.py._backmatter_start 已验证的Appendices起点(逐册实测值)。
_BACKMATTER_START = {"7a": 123, "7b": 127, "8a": 139, "8b": 139, "9a": 139, "9b": 107}
_ALPHA_TITLE_FRAGMENT = "aaalllppphhhaaabbbeeetttiiicccaaalll"  # 粗体加倍渲染的"alphabetical"


def _find_unit_list_bounds(pdf: pdfplumber.PDF, vol: str) -> tuple[int, int] | None:
    """[start, end) 页范围: 独立"Unit 1"行所在页 → "alphabetical order"标题所在页(不含)。

    坑(2026-07-08实测): 若逐行检测到标题就立即break, 2栏reflow顺序会让同页里标题**之前**
    的词条(仍属alphabetical表, 非unit表)被误收; 必须先按页扫定位end页, 再整页排除。
    """
    bm = _BACKMATTER_START[vol]
    start = end = None
    for i in range(bm, len(pdf.pages)):
        lines = _col_lines(pdf.pages[i])
        if start is None and any(ln.strip() == "Unit 1" for ln in lines):
            start = i
        if end is None and _ALPHA_TITLE_FRAGMENT in "".join(lines).replace(" ", ""):
            end = i
            break
    return (start, end) if start is not None and end is not None else None


def _unit_marker(line: str) -> int | None:
    stripped = line.strip()
    if stripped.startswith("Unit ") and stripped[5:].strip().isdigit():
        return int(stripped[5:].strip())
    return None


def _entry_word(line: str) -> str | None:
    clean = line.replace("上海教育出版社", "").strip()
    m = _ENTRY.match(clean)
    if not m:
        return None
    word = m.group(1).strip().lower()
    return word if 2 <= len(word) <= 25 and word[0].isalpha() else None


def extract_volume(vol: str) -> list[dict]:
    with pdfplumber.open(str(TB / f"{vol}.pdf")) as pdf:
        bounds = _find_unit_list_bounds(pdf, vol)
        if not bounds:
            return []
        start, end = bounds
        cur_unit: int | None = None
        rows: list[dict] = []
        for i in range(start, end):
            for ln in _col_lines(pdf.pages[i]):
                unit = _unit_marker(ln)
                if unit is not None:
                    cur_unit = unit
                    continue
                word = _entry_word(ln)
                if word and cur_unit is not None:
                    rows.append({"version": "hujiao", "volume_key": vol,
                                 "unit_number": cur_unit, "word": word})
    return rows


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    per_vol: dict[str, int] = {}
    for vol in VOLUMES:
        rows = extract_volume(vol)
        per_vol[vol] = len(rows)
        all_rows.extend(rows)
    with (OUT / "hujiao_vocab_unit.jsonl").open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"总行数": len(all_rows), "per_vol": per_vol}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
