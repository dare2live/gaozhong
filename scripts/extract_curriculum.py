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
    """词汇表 (附录2, p129-182): 一行一词 + 后缀 * (必修) / ** (选必)."""
    rows: list[dict] = []
    seen: set[str] = set()
    word_re = re.compile(r"^([A-Za-z][A-Za-z\-']*?)(\*{1,2})?\s*$")
    # 词汇表起始/结束页 (0-indexed). 课标 p129 = "附录 2 词汇表"; p182 末; 第 183 起是附录 3 语法.
    start_page, end_page = 129 - 1, 182 - 1
    for pi in range(start_page, end_page + 1):
        if pi >= len(reader.pages):
            break
        text = _page_text(reader, pi)
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 跳过页眉 "│ 附录 │", 页码
            if line.startswith("│") or line.isdigit():
                continue
            # 跳过单字母分组标 (A B C ...)
            if len(line) == 1 and line.isalpha():
                continue
            # 课标说明段也跳过 (含中文)
            if any("一" <= ch <= "鿿" for ch in line):
                continue
            # 拆 token: 一页里词条用空格分隔, 而非换行
            for tok in line.split():
                m = word_re.match(tok)
                if not m:
                    continue
                w = m.group(1).lower()
                suffix = m.group(2) or ""
                if w in seen:
                    continue
                seen.add(w)
                level = "选必" if suffix == "**" else ("必修" if suffix == "*" else "义教")
                rows.append({
                    "word": w,
                    "cefr_level": level,
                    "raw_suffix": suffix,
                    "source": SOURCE_TAG,
                })
    return rows


def extract_grammar_items(reader: PdfReader) -> list[dict]:
    """语法项目表 (附录3, p187-191): 编号 + 标题层级 + * / ** 标."""
    rows: list[dict] = []
    start_page, end_page = 187 - 1, 192 - 1
    current_category = None
    item_re = re.compile(r"^(\d+(?:\.\d+)*|\([0-9一二三四五六七八九十]+\))\s*(.*?)(\*{1,2})?\s*$")
    for pi in range(start_page, end_page + 1):
        if pi >= len(reader.pages):
            break
        text = _page_text(reader, pi)
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("│") or line.isdigit():
                continue
            if line.startswith("附录") or "语法项目" in line or "说明" in line:
                continue
            m = item_re.match(line)
            if not m:
                continue
            num, label, suffix = m.group(1), m.group(2).strip(), (m.group(3) or "")
            # 课标行型 "5. 谓语动词的时态" — 我们的 regex 抓 num="5" label=". 谓语动词的时态"
            label = label.lstrip(".。:：、 ").strip()
            if not label:
                continue
            level = "选必" if suffix == "**" else ("必修" if suffix == "*" else "义教")
            # 顶级数字 (无小数点) 视为类目
            if re.match(r"^\d+$", num):
                current_category = label.rstrip("：:")
            rows.append({
                "grammar_item_id": num,
                "category": current_category,
                "label": label,
                "cefr_level": level,
                "source": SOURCE_TAG,
            })
    return rows


def extract_theme_contexts(_reader: PdfReader) -> list[dict]:
    """主题语境: 三大语境 + 6 主题群 (硬编码 — 课标 p22-23 明文定义).

    课标原文 (p22, §四(一)):
      人与自我 (生活与学习 / 做人与做事 — 2 个主题群, 9 项子主题)
      人与社会 (社会服务与人际沟通 / 文学、艺术与体育 / 历史、社会与文化 / 科学与技术 — 4 个主题群)
      人与自然 (自然生态 / 环境保护 / 灾害防范 / 宇宙探索 — 4 个主题群)
    子主题 (level3) 待 STEP 2 P0.3 增量抽; 当前 MVP 用 level1/level2 已够.
    """
    structure = {
        "人与自我": ["生活与学习", "做人与做事"],
        "人与社会": [
            "社会服务与人际沟通", "文学、艺术与体育",
            "历史、社会与文化", "科学与技术",
        ],
        "人与自然": ["自然生态", "环境保护", "灾害防范", "宇宙探索"],
    }
    rows: list[dict] = []
    for lvl1, groups in structure.items():
        rows.append({
            "theme_context_id": lvl1,
            "level1": lvl1, "level2": None, "level3": None,
            "source": f"{SOURCE_TAG} (硬编码自 p22-23)",
        })
        for g in groups:
            rows.append({
                "theme_context_id": f"{lvl1}/{g}",
                "level1": lvl1, "level2": g, "level3": None,
                "source": f"{SOURCE_TAG} (硬编码自 p22-23)",
            })
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
