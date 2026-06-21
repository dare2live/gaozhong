"""人教版词表抽 — 单一真相源「各单元生词 / Words and Expressions in Each Unit」(2026-06-17 重写 D0).

真相源 (第一性原理): 人教书末 Appendices 有 **唯一** 一段「各单元生词」, 结构:
  - 起页同时含 '各单元生词' + 'Words and Expressions in Each Unit', 内首个 'Unit 1' 头
  - 每单元 'Unit N' 单行头锚定; 词条 `word /ipa/ pos. 释义`, 释义/多词性可换行续行
  - 课标词(黑体)+非课标词(白体) 全要; 专有名词(Egypt/UNESCO/the Nile…)单列于每单元后 — 无 pos, 不取
  - 该段之后是字母序 'Vocabulary/词汇' 总表(行末 (N) 标单元) + 不规则动词表 + 国家表 — **全不读**

弃用 (原 D0 违反): 「读所有 entry≥8 页 + 线性 _page_to_unit_estimator」把字母序总表页也当词表页,
尾段页全砸进 U5 → 331 个 (vol,word) 跨单元重复; 且行级 ^锚 双栏漏抽 → 召回 ~82%。
本版: 只读「各单元生词」单段, 'Unit N' 头锚单元, 块解析续行, 字母序总表即停。

双栏 + PUA: pdfplumber 按页宽中线 crop 左/右半栏各自 reflow; IPA 斜杠 PUA U+F02F→'/' 归一 (保留)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "structured" / "textbook"

_PUA_SLASH = "\uf02f"  # 人教 PDF 部分页 IPA 斜杠的 PUA 字形 (U+F02F)

# 段起锚: 同页含中英两个 '各单元生词' 标题 (排除卷首 per-unit 词表页, 它无 '各单元生词')
_SECTION_START_CN = "各单元生词"
_SECTION_START_EN = "Words and Expressions in Each Unit"
# 段终锚: 字母序总表标题 / 行末 (N) 内联单元标记 (per-unit 段内为 0)
_TOTAL_LIST_TITLE_RE = re.compile(r"^\s*Vocabulary\s*$")
_INLINE_UNIT_RE = re.compile(r"\(\d+\)\s*$")
_TOTAL_LIST_MIN_INLINE = 10  # 一页 ≥10 行末 (N) = 字母序总表 (per-unit 段恒 0)

_UNIT_HEAD_RE = re.compile(r"^\s*Unit\s+(\d+)\s*$")
# 词条头: 小写起首词/短语 + /ipa/ + 行内余文 (pos/释义可能续行)
_ENTRY_HEAD_RE = re.compile(r"^\s*([a-z][a-z'\- ]*?)\s+/[^/]+/\s*(.*)$")
# 短语词条头: 小写英文≥2词 + 起首中文(无/ipa/, 无POS) — 如 'clean up 打扫'。
# 旧版无此识别→短语被当续行吸进前词(231条丢失 + zh_def污染)。护栏: 英文≥2词+起首中文,
# 区别于释义续行(起首中文)和例句(常含大写/过长); dry实证216候选0假阳性(无大写无过长)。
_PHRASE_HEAD_RE = re.compile(r"^\s*([a-z][a-z'’.\-]*(?:\s+[a-z][a-z'’.\-]+)+)\s+([一-鿿].*)$")
_POS_TOKEN_RE = re.compile(
    r"\b(?:n|vt|vi|adj|adv|prep|conj|pron|num|art|aux|modal|abbr|int)\.")
# 段内非词条噪声行 (running header / 注释 / 页码)
_NOISE_RE = re.compile(
    r"^\s*(?:Appendices?|Words and Expres|ssions in Each Unit"
    r"|各单元生词|注[:：]|\d{1,3}|[A-Z]\s*)\s*$")


def _page_lines(page) -> list[str]:
    """按页宽中线 crop 左/右半页各自 extract_text + PUA U+F02F→'/' → 文本行列表 (左半在前)."""
    mid = page.width / 2
    left = page.crop((0, 0, mid, page.height)).extract_text() or ""
    right = page.crop((mid, 0, page.width, page.height)).extract_text() or ""
    return [ln.replace(_PUA_SLASH, "/") for ln in (left + "\n" + right).split("\n")]


def _is_section_start(page) -> bool:
    """该页是否为「各单元生词」段起页 (中英标题同现, 排除卷首 per-unit 词表页)."""
    t = page.extract_text() or ""
    return _SECTION_START_CN in t and _SECTION_START_EN in t


def _is_total_list(page) -> bool:
    """该页是否进入字母序 'Vocabulary/词汇' 总表 (段终边界).

    用整页 extract_text (洁净) 判, 不用双栏 crop — 字母序总表页右栏常 PUA 字形化,
    crop 后 'Vocabulary'/'(N)' 被打散无法匹配; 整页文本里两者清晰可辨。
    """
    t = page.extract_text() or ""
    lines = t.split("\n")
    if any(_TOTAL_LIST_TITLE_RE.match(ln) for ln in lines):
        return True
    return sum(1 for ln in lines if _INLINE_UNIT_RE.search(ln)) >= _TOTAL_LIST_MIN_INLINE


def _section_pages(pdf) -> list[list[str]]:
    """返回「各单元生词」段(含起页, 到字母序总表前)的逐页(双栏 reflow)行列表; 无段起返回 []."""
    start = next((i for i, pg in enumerate(pdf.pages) if _is_section_start(pg)), None)
    if start is None:
        return []
    pages: list[list[str]] = []
    for pg in pdf.pages[start:]:
        if pages and _is_total_list(pg):  # 起页本身不当总表 (它含 per-unit 词条)
            break
        pages.append(_page_lines(pg))
    return pages


def _is_entry_continuation(line: str) -> bool:
    """续行 = 非空、非 Unit 头、非新词条头、非噪声 (pos 续行 / 释义续行 / 短语行)."""
    s = line.strip()
    if not s or _UNIT_HEAD_RE.match(line) or _NOISE_RE.match(line):
        return False
    return _ENTRY_HEAD_RE.match(line) is None


def _has_cjk(s: str) -> bool:
    return any("一" <= c <= "鿿" for c in s)


def _finalize(word: str, rest_lines: list[str], is_phrase: bool = False) -> dict | None:
    """块行 → 词条 dict; 无 pos (专有名词/纯中文转写) 返回 None (不当词表).
    短语词条(is_phrase): 无POS, zh_def=块内中文(有中文才保留, 防纯专名)。"""
    block = " ".join(s.strip() for s in rest_lines if s.strip())
    if is_phrase:
        zh = re.sub(r"\s*\(\d+\)\s*$", "", block).strip()
        return {"word": word, "pos": "", "zh_def": zh} if _has_cjk(zh) else None
    pos_m = _POS_TOKEN_RE.search(block)
    if not pos_m:
        return None
    pos = pos_m.group(0).rstrip(".")
    # zh_def = pos 之后首段中文 (取到行尾, 去内联 (N) 单元标记若有)
    tail = block[pos_m.end():].strip()
    zh = re.sub(r"\s*\(\d+\)\s*$", "", tail).strip()
    return {"word": word, "pos": pos, "zh_def": zh}


def _start_pending(line: str) -> tuple[str, list[str], bool] | None:
    """行是否词条头 → (word, [rest], is_phrase); 否则 None.
    词条头(有ipa) 与 短语头(无ipa, 英文≥2词+起首中文) 二选一; 短语在续行判定前优先识别。"""
    eh = _ENTRY_HEAD_RE.match(line)
    if eh:
        return eh.group(1).strip().lower(), [eh.group(2)], False
    ph = _PHRASE_HEAD_RE.match(line)
    if ph:
        return ph.group(1).strip().lower(), [ph.group(2)], True
    return None


def _backfill_first_unit(raw: list[tuple]) -> list[tuple[int, dict]]:
    """首个 unit 头前的 (None, entry) 回填到**首个真实 unit**(双栏reflow把首单元词排到头前)。
    派生首单元号(不硬编码 '1'); 无任何 unit 头(degenerate)兜底 1。"""
    first_unit = next((u for u, _ in raw if u is not None), 1)
    return [(u if u is not None else first_unit, e) for u, e in raw]


def _parse_section(pages: list[list[str]]) -> list[tuple[int, dict]]:
    """段内逐行块解析 → [(unit_number, entry_dict), ...]; 'Unit N' 头锚当前单元(头前词条回填首单元)."""
    raw: list[tuple] = []
    current_unit: int | None = None
    pend: tuple[str, list[str], bool] | None = None

    def flush():
        nonlocal pend
        if pend:
            entry = _finalize(pend[0], pend[1], pend[2])
            if entry:
                raw.append((current_unit, entry))
        pend = None

    for lines in pages:
        for line in lines:
            uh = _UNIT_HEAD_RE.match(line)
            if uh:
                flush()
                current_unit = int(uh.group(1))
                continue
            started = _start_pending(line)
            if started:
                flush()
                pend = started
                continue
            if pend is not None and _is_entry_continuation(line):
                pend[1].append(line)
    flush()
    return _backfill_first_unit(raw)


def extract_renjiao_vocab(pdf_path: Path, volume_key: str) -> list[dict]:
    """只读「各单元生词」单段, 'Unit N' 头锚单元, 块解析续行; 0 跨单元重复 by 构造."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = _section_pages(pdf)
    if not pages:
        return []
    rows: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for unit_n, entry in _parse_section(pages):
        word = entry["word"]
        if not word or len(word) > 30 or not re.match(r"^[a-z][a-z'\- ]*$", word):
            continue
        key = (word, unit_n)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "version_key": "renjiao", "volume_key": volume_key,
            "unit_number": unit_n, "word": word,
            "pos": entry["pos"], "zh_def": entry["zh_def"], "raw_marker": "",
        })
    return rows


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
    print(json.dumps(run_all(), ensure_ascii=False, indent=2))
