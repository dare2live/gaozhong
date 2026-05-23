"""P0: 英语课标 PDF → 3 个 jsonl truth source.

输入:  data/curriculum/national/.../4.普通高中英语课程标准（2017年版2020年修订）.pdf
输出:
  data/structured/curriculum/cefr_vocab.jsonl       # 词汇表 ≈ 3000
  data/structured/curriculum/grammar_items.jsonl    # 语法项目表
  data/structured/curriculum/theme_contexts.jsonl   # 主题语境
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data/curriculum/national/普通高中课程方案及20科课程标准（2017年版2020年修订)/4.普通高中英语课程标准（2017年版2020年修订）.pdf"
OUT_DIR = ROOT / "data/structured/curriculum"
SOURCE_TAG = "4.普通高中英语课程标准（2017年版2020年修订）.pdf"


def _page_text(reader: PdfReader, page_index: int) -> str:
    return reader.pages[page_index].extract_text() or ""


def extract_cefr_vocab(reader: PdfReader) -> list[dict]:
    """词汇表 (附录2, p129-182): 一行一词 + 后缀 * (必修) / ** (选必).
    P0 v2: 支持 'word (alt_form)' (eg 'a (an)', 'mouse (pl. mice)') 也收 alt 词 (alt 视同 hub 词级别).
    """
    rows: list[dict] = []
    seen: set[str] = set()
    # 主词 token: 字母 + 可选 - ' . , 全部允许内嵌
    main_re = re.compile(r"^([A-Za-z][A-Za-z\-'.]*)(\*{1,2})?$")
    # 括号 alt 内的纯英文词 (e.g. 'an', 'mice', 'bicycle')
    alt_word_re = re.compile(r"([A-Za-z][A-Za-z\-']{1,})")
    start_page, end_page = 129 - 1, 182 - 1
    for pi in range(start_page, end_page + 1):
        if pi >= len(reader.pages):
            break
        text = _page_text(reader, pi)
        for raw in text.split("\n"):
            line = raw.strip()
            if not line or line.startswith("│") or line.isdigit():
                continue
            if len(line) == 1 and line.isalpha():
                continue
            if any("一" <= ch <= "鿿" for ch in line):
                continue
            # split into [main, ...parenthesized...]
            paren = re.findall(r"\(([^)]*)\)", line)
            main_part = re.sub(r"\([^)]*\)", "", line).strip()
            for tok in main_part.split():
                m = main_re.match(tok)
                if not m: continue
                w = m.group(1).lower().rstrip(".")
                suffix = m.group(2) or ""
                if w and w not in seen:
                    seen.add(w)
                    rows.append({
                        "word": w, "cefr_level": _level_of(suffix),
                        "raw_suffix": suffix, "source": SOURCE_TAG,
                    })
                # for the same line, 找括号 alt
                for p in paren:
                    # skip "pl. mice" 标记
                    for a in alt_word_re.findall(p):
                        aw = a.lower()
                        # 跳过明显是标注 (pl/sing/eg) 的 token
                        if aw in {"pl", "sing", "eg", "etc", "ie"}:
                            continue
                        if aw not in seen:
                            seen.add(aw)
                            rows.append({
                                "word": aw, "cefr_level": _level_of(suffix),
                                "raw_suffix": suffix + " (alt)", "source": SOURCE_TAG,
                            })
                paren = []  # consume
    return rows


def _level_of(suffix: str) -> str:
    if suffix.startswith("***"): return "选修"
    if suffix.startswith("**"): return "选必"
    if suffix.startswith("*"): return "必修"
    return "义教"


def extract_grammar_items(reader: PdfReader) -> list[dict]:
    """语法项目表 (附录3, p187-191) 层级:
        一、词类 (一级)
          1. 名词 (二级)
            （1）可数名词及其单、复数 (三级)
              a. 一般疑问句 (四级)
        ID 用层级路径: "一/1/(1)/a"; 全局唯一, 父子关系经 cat_of edge.
        星号 *=必修, **=选必, ***=选修.
    """
    rows: list[dict] = []
    start_page, end_page = 187 - 1, 192 - 1
    seq = 0

    # 五种行型 → (depth, normalized_token)
    re_l1   = re.compile(r"^([一二三四五六七八九十]+)、(.+?)(\*+)?$")
    re_l2   = re.compile(r"^(\d+)\.\s*(.+?)(\*+)?$")
    re_l3   = re.compile(r"^[（(](\d+)[)）]\s*(.+?)(\*+)?$")
    re_l4   = re.compile(r"^([a-z])\.\s*(.+?)(\*+)?$")

    cur = {1: None, 2: None, 3: None, 4: None}

    def lvl_of(suffix: str) -> str:
        if not suffix: return "义教"
        if suffix == "*": return "必修"
        if suffix == "**": return "选必"
        return "选修"   # ***

    def emit(depth: int, num: str, label: str, suffix: str, parent_path: str):
        nonlocal seq
        path = parent_path + "/" + num if parent_path else num
        cur[depth] = path
        for k in range(depth + 1, 5):
            cur[k] = None
        seq += 1
        rows.append({
            "grammar_item_id": path,
            "depth": depth,
            "parent_id": parent_path or None,
            "category": cur[1] and cur[1].split("/")[0],
            "label": label.strip().rstrip("：:"),
            "cefr_level": lvl_of(suffix),
            "seq": seq,
            "source": SOURCE_TAG,
        })

    for pi in range(start_page, end_page + 1):
        if pi >= len(reader.pages):
            break
        text = _page_text(reader, pi)
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("│") or line.isdigit():
                continue
            if line.startswith("附录") or "语法项目" in line or line.startswith("说明") or line.startswith("普通高中"):
                continue
            # skip 例句 (含英文字母 > 50% 的行)
            if sum(ch.isascii() and ch.isalpha() for ch in line) > 0.4 * max(1, len(line.replace(" ", ""))):
                continue
            m1 = re_l1.match(line)
            if m1:
                emit(1, m1.group(1), m1.group(2), m1.group(3) or "", "")
                continue
            m2 = re_l2.match(line)
            if m2:
                parent = cur[1] or ""
                emit(2, m2.group(1), m2.group(2), m2.group(3) or "", parent)
                continue
            m3 = re_l3.match(line)
            if m3:
                parent = cur[2] or cur[1] or ""
                emit(3, f"({m3.group(1)})", m3.group(2), m3.group(3) or "", parent)
                continue
            m4 = re_l4.match(line)
            if m4:
                parent = cur[3] or cur[2] or cur[1] or ""
                emit(4, m4.group(1), m4.group(2), m4.group(3) or "", parent)
                continue
    return rows


def extract_theme_contexts(_reader: PdfReader) -> list[dict]:
    """主题语境: 三大语境 + 10 主题群 + 35 子主题 (硬编码自 theme_contexts_hardcoded.json).
    数据源: 课标 §四(一) p22-46, 出表方便人工维护 / 后续 PDF 实抽对比.
    """
    spec_path = OUT_DIR / "theme_contexts_hardcoded.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    structure, level3 = spec["structure"], spec["level3"]
    rows: list[dict] = []
    for lvl1, groups in structure.items():
        rows.append({"theme_context_id": lvl1, "level1": lvl1, "level2": None,
                      "level3": None, "source": f"{SOURCE_TAG} (json hardcoded)"})
        for g in groups:
            rows.append({"theme_context_id": f"{lvl1}/{g}", "level1": lvl1,
                          "level2": g, "level3": None,
                          "source": f"{SOURCE_TAG} (json hardcoded)"})
            for sub in level3.get(f"{lvl1}/{g}", []):
                rows.append({"theme_context_id": f"{lvl1}/{g}/{sub}",
                              "level1": lvl1, "level2": g, "level3": sub,
                              "source": f"{SOURCE_TAG} (json hardcoded)"})
    return rows


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(PDF_PATH)
    reader = PdfReader(PDF_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    vocab = extract_cefr_vocab(reader)
    grammar = extract_grammar_items(reader)
    themes = extract_theme_contexts(reader)

    paths = {
        "cefr_vocab.jsonl": vocab,
        "grammar_items.jsonl": grammar,
        "theme_contexts.jsonl": themes,
    }
    for name, rows in paths.items():
        p = OUT_DIR / name
        with p.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {len(rows):5d} rows -> {p.relative_to(ROOT)}")

    # 显式校验, 不静默吃异常
    vocab_n = len(vocab)
    bixiu = sum(1 for r in vocab if r["cefr_level"] == "必修")
    xuanbi = sum(1 for r in vocab if r["cefr_level"] == "选必")
    yijiao = sum(1 for r in vocab if r["cefr_level"] == "义教")
    print(f"\n  vocab breakdown: 义教={yijiao}, 必修={bixiu}, 选必={xuanbi}, total={vocab_n}")
    if not (2500 <= vocab_n <= 3500):
        print(f"  WARN: 词汇表总数 {vocab_n} 偏离 3000 ±500, 检查 PDF 提取是否被噪音污染")
    if bixiu < 300 or bixiu > 700:
        print(f"  WARN: 必修 (*) 数 {bixiu} 偏离课标声明 500 ±200")
    if xuanbi < 700 or xuanbi > 1300:
        print(f"  WARN: 选必 (**) 数 {xuanbi} 偏离课标声明 1000 ±300")


if __name__ == "__main__":
    main()
