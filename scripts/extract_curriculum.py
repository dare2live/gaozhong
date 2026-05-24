"""P0: 英语课标 PDF → 3 个 jsonl truth source.

输入:  data/curriculum/national/.../4.普通高中英语课程标准（2017年版2020年修订）.pdf
输出:
  data/structured/curriculum/cefr_vocab.jsonl       # 词汇表 ≈ 3000
  data/structured/curriculum/grammar_items.jsonl    # 语法项目表
  data/structured/curriculum/theme_contexts.jsonl   # 主题语境

注: vocab + grammar 抽器拆到 scripts/lib/curriculum_*.py (4.5 CC 拆).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.lib import curriculum_grammar, curriculum_vocab  # noqa: E402

PDF_PATH = ROOT / "data/curriculum/national/普通高中课程方案及20科课程标准（2017年版2020年修订)/4.普通高中英语课程标准（2017年版2020年修订）.pdf"
OUT_DIR = ROOT / "data/structured/curriculum"
SOURCE_TAG = "4.普通高中英语课程标准（2017年版2020年修订）.pdf"


def _page_text(reader: PdfReader, page_index: int) -> str:
    return reader.pages[page_index].extract_text() or ""


def extract_cefr_vocab(reader: PdfReader) -> list[dict]:
    """词汇表抽取 — 委托给 scripts/lib/curriculum_vocab (4.5 CC 拆)."""
    return curriculum_vocab.extract_cefr_vocab(reader, SOURCE_TAG)


def extract_grammar_items(reader: PdfReader) -> list[dict]:
    """语法项目表抽取 — 委托给 scripts/lib/curriculum_grammar (4.5 CC 拆)."""
    return curriculum_grammar.extract_grammar_items(reader, SOURCE_TAG)


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
