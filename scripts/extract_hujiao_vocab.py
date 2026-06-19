"""沪教牛津(广深沈) 初中英语 6册 词表抽取 — 沈阳主用版, stage=初中 真相源.

源: data/junior_high/textbooks/hujiao/{7a,7b,8a,8b,9a,9b}.pdf (卷末 Words and expressions 附录)。
文本层主抽 (PaddleOCR 交叉验证已证 171/171=100% 可信); 双栏 crop + PUA IPA 跳过。
emit: data/junior_high/structured/hujiao_vocab.jsonl  (word, pos, zh_def, grade, stage=初中, source)
cross-check: 与义务课标三级 + 高中cefr 对账 (stdout)。CC<10/函数 (Rule 8)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
TB = ROOT / "data" / "junior_high" / "textbooks" / "hujiao"
OUT = ROOT / "data" / "junior_high" / "structured"
COL_SPLIT_RATIO = 0.5
# 词条: word /ipa/ pos. 释义 [p. N]  (IPA 含 PUA, 用 /[^/]+/ 跨过)
_ENTRY = re.compile(r"^([a-zA-Z][a-zA-Z\-' ]*?)\s*/[^/]+/\s*([a-z]+)\.\s*(.+?)(?:\s*p\.\s*\d+)?\s*$")
_GRADE = {"7a": "七上", "7b": "七下", "8a": "八上", "8b": "八下", "9a": "九上", "9b": "九下"}


def _col_lines(page) -> list[str]:
    mid = page.width * COL_SPLIT_RATIO
    out = []
    for box in ((0, 0, mid, page.height), (mid, 0, page.width, page.height)):
        out.extend((page.crop(box).extract_text() or "").split("\n"))
    return out


def _parse(line: str) -> tuple[str, str, str] | None:
    """word + pos 来自可读文本层; 释义含中文则取, CID 乱码则标 '待OCR'.

    CID 只污染中文释义, 英文 word 本身可读 → stage 词表不靠 OCR; 释义后置 OCR 补。
    """
    line = line.replace("上海教育出版社", "").strip()
    m = _ENTRY.match(line)
    if not m:
        return None
    word = m.group(1).strip().lower()
    if not (2 <= len(word) <= 25) or not re.match(r"^[a-z]", word):
        return None
    zh = m.group(3).strip()
    # F4 修: 任何 (cid: 出现即标待OCR (含 cid+中文混合 cheerful→(cid:2682)(cid:2754)的,
    # 旧版 any(中文) 为真就保留泄漏 cid); 纯中文才取释义; 既无中文又无 cid = 噪声滤。
    if "(cid:" in zh or "ud:" in zh:
        zh_clean = "待OCR"
    elif any("一" <= ch <= "鿿" for ch in zh):
        zh_clean = zh[:60]
        # 强验证 H1: 释义以分隔符(；，、（)结尾 = 源文本层CID吃后半(人人；所有人→人人；); 诚实标不完整。
        if zh_clean.rstrip().endswith(("；", "，", "、", "（", "(", ";", ",")):
            zh_clean = zh_clean.rstrip() + "…(文本层截断待补全)"
    else:
        return None
    return (word, m.group(2), zh_clean)


def _vocab_pages(pdf) -> list[int]:
    """词表附录页 = 每页 ≥8 条匹配 (双栏 reflow 后)."""
    out = []
    for i, pg in enumerate(pdf.pages):
        if sum(1 for ln in _col_lines(pg) if _parse(ln)) >= 8:
            out.append(i)
    return out


def extract_volume(vol: str) -> list[dict]:
    rows, seen = [], set()
    with pdfplumber.open(str(TB / f"{vol}.pdf")) as pdf:
        page_lines = {i: _col_lines(pdf.pages[i]) for i in _vocab_pages(pdf)}
    for lines in page_lines.values():
        for ln in lines:
            p = _parse(ln)
            if p and p[0] not in seen:
                seen.add(p[0])
                rows.append({"word": p[0], "pos": p[1], "zh_def": p[2], "grade": _GRADE[vol],
                             "stage": "初中", "version": "沪教牛津(广深沈)", "source": f"hujiao_{vol}"})
    return rows


def _dedup_first(per_raw: dict) -> dict[str, dict]:
    """6册按年级序首现去重: 首现卷=grade; 后卷干净释义回填 CID 待OCR 词."""
    seen: dict[str, dict] = {}
    for vol in _GRADE:                        # 7a→9b 保序
        rows = extract_volume(vol)
        per_raw[vol] = len(rows)
        for row in rows:
            w = row["word"]
            if w not in seen:
                seen[w] = row
            elif seen[w]["zh_def"] == "待OCR" and row["zh_def"] != "待OCR":
                seen[w]["zh_def"] = row["zh_def"]
    return seen


def build() -> dict:
    """6册抽取 + 首现去重 (per-grade=首引年级; 9b累积总表只补新词)."""
    OUT.mkdir(parents=True, exist_ok=True)
    per_raw: dict = {}
    rows = list(_dedup_first(per_raw).values())
    with (OUT / "hujiao_vocab.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    per_first = {g: sum(1 for r in rows if r["grade"] == g) for g in set(_GRADE.values())}
    need_ocr = sum(1 for r in rows if r["zh_def"] == "待OCR")
    return {"distinct_word": len(rows), "释义待OCR": need_ocr,
            "per_grade首现": {k: per_first.get(k, 0) for k in ["七上","七下","八上","八下","九上","九下"]},
            "per_vol_raw": per_raw}


def cross_check() -> None:
    import duckdb
    hj = {json.loads(l)["word"] for l in (OUT / "hujiao_vocab.jsonl").open(encoding="utf-8")}
    yiwu = {json.loads(l)["word"] for l in (OUT / "curriculum_vocab.jsonl").open(encoding="utf-8")}
    c = duckdb.connect(str(ROOT / "data" / "db" / "gaozhong.duckdb"), read_only=True)
    cefr = {r[0] for r in c.execute("SELECT word FROM cefr_vocab").fetchall()}
    c.close()
    print("\n=== 沪教词表 跨源对账 ===")
    print(f"沪教6册 distinct: {len(hj)}")
    print(f"∩ 义务课标三级({len(yiwu)}): {len(hj & yiwu)} ({len(hj&yiwu)/max(1,len(hj)):.0%} 教材词在课标内)")
    print(f"∩ 高中cefr({len(cefr)}): {len(hj & cefr)}")
    print(f"沪教有但义务课标无(教材超课标/抽取噪声): {len(hj - yiwu)} 例 {sorted(hj-yiwu)[:12]}")


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    cross_check()
