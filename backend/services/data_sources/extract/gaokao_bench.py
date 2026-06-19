"""通用 GAOKAO-Bench JSONL 提取工具 (extract 层, 单一职责: 读源 → raw record).

来源 (原 OpenLMLab/GAOKAO-Bench 公开数据集, **已全镜像进本项目** — 互不干扰独立项目, 不读姊妹项目 gaokao):
  - GAOKAO-Bench         base  : data/external/GAOKAO-Bench/Data/{Objective,Subjective}_Questions/*English*.json (2026-06-17 cp 进)
  - GAOKAO-Bench-Updates 2023  : data/external/gaokao_bench_2023/*.json
  - (Updates) 2024       2024  : data/external/gaokao_bench_2024/*.json

边界 (D0 + Rule 1 单一计算点):
  - 本模块**只做 extract**: 读 JSON → yield raw record. 不算 province/paper_type.
  - province/paper_type 卷型分类是 clean 层 (backend/services/data_sources/clean/exam_paper.py)
    的职责 — 它消费本模块 yield 的 `category` 字段做诚实卷型标注.
  - 保留原始 `category`(如 "（新课标）" / "新课标II") 供 clean 层判别, extract 不解释它.
  - 不改 backend/services/extraction/exam.py (那是历史镜像入口, 本模块是其 extract 切片的提纯).

raw record schema (per example):
  {question_id, year, category, question_type, raw_question,
   answer, analysis, source_file, source_index, source_repo}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

# 路径常量 (与 exam.py 对齐, 单一真相): ROOT = 项目根 (.../gaozhong)
ROOT = Path(__file__).resolve().parents[4]
# 2026-06-17: 镜像进本项目, 不再读姊妹项目 gaokao (互不干扰独立项目, 用户硬约束)。
# 原始 GAOKAO-Bench English base 已 cp 进 data/external/GAOKAO-Bench/Data (6 个真实英语文件;
# ENGLISH_SOURCES 列的另 2 个 gaokao 本就没有, iter 优雅 skip — 行为不变)。
GAOKAO_DATA = ROOT / "data/external/GAOKAO-Bench/Data"
UPDATES_DIR = ROOT / "data" / "external" / "gaokao_bench_2023"
UPDATES_DIR_2024 = ROOT / "data" / "external" / "gaokao_bench_2024"

ENGLISH_SOURCES = [
    "Objective_Questions/2010-2022_English_MCQs.json",
    "Objective_Questions/2010-2013_English_MCQs.json",
    "Objective_Questions/2012-2022_English_Cloze_Test.json",
    "Objective_Questions/2014-2022_English_Language_Cloze_Passage.json",
    "Objective_Questions/2010-2022_English_Reading_Comp.json",
    "Objective_Questions/2010-2022_English_Fill_in_Blanks.json",
    "Subjective_Questions/2012-2022_English_Language_Error_Correction.json",
    "Subjective_Questions/2014-2022_English_Language_Cloze_Passage.json",
]
ENGLISH_SOURCES_2023 = [
    "2023_English_Cloze_Test.json",
    "2023_English_Fill_in_Blanks.json",
    "2023_English_Reading_Comp.json",
]
ENGLISH_SOURCES_2024 = [
    "2024_English_Cloze_Test.json",
    "2024_English_Fill_in_Blanks.json",
    "2024_English_Reading_Comp.json",
]

# (base_dir, src_list, id_prefix, source_repo) — 遍历全部源的单一清单.
ALL_SOURCES = [
    (GAOKAO_DATA, ENGLISH_SOURCES, "gb", "OpenLMLab/GAOKAO-Bench"),
    (UPDATES_DIR, ENGLISH_SOURCES_2023, "gbu", "OpenLMLab/GAOKAO-Bench-Updates"),
    (UPDATES_DIR_2024, ENGLISH_SOURCES_2024, "gbu24", "OpenLMLab/GAOKAO-Bench-Updates-2024"),
]

_MAX_QUESTION = 8000
_MAX_ANALYSIS = 4000


def iter_examples(src_file: Path) -> Iterable[tuple[int, dict]]:
    """读 GAOKAO-Bench JSON (dict{'example': [...]} 或裸 list), yield (index, example_dict).

    文件不存在 → 空迭代 (诚实跳过, 不抛错; 与 exam.py 行为一致).
    """
    if not src_file.exists():
        return
    data = json.loads(src_file.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "example" in data:
        items = data["example"]
    elif isinstance(data, list):
        items = data
    else:
        return
    for i, ex in enumerate(items):
        if isinstance(ex, dict):
            yield i, ex


def infer_question_type(file_basename: str) -> str:
    """文件名 (stem/basename) → 题型中文标签.

    保留 L-2026-05-25-O 交叉验证修正 (与 exam.py 完全一致):
      cloze_test=完形填空(七选五/语篇), cloze_passage=语法填空,
      fill_in_blanks=完形填空, reading_comp=阅读理解,
      error_correction=短文改错, mcq=单选(语法/词汇).
    顺序敏感: cloze_test / cloze_passage 必须在通用关键字之前命中.
    """
    name = file_basename.lower()
    if "cloze_test" in name:
        return "完形填空(七选五/语篇)"
    if "cloze_passage" in name:
        return "语法填空"
    if "reading_comp" in name:
        return "阅读理解"
    if "fill_in_blanks" in name:
        return "完形填空"
    if "error_correction" in name:
        return "短文改错"
    if "mcq" in name:
        return "单选(语法/词汇)"
    return "其他"


def _coerce_year(raw) -> int | None:
    """year 字段 ('2012' / 2012 / None / '') → int|None, 不估算不硬填."""
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _build_record(id_prefix: str, base: str, i: int, ex: dict,
                  qtype: str, repo: str) -> dict:
    """单条 example → raw record. 保留原始 category, 不做卷型分类 (clean 层职责)."""
    analysis = ex.get("analysis") or ""
    return {
        "question_id": f"{id_prefix}/{base}/{i}",
        "year": _coerce_year(ex.get("year")),
        "category": ex.get("category") or "",
        "question_type": qtype,
        "raw_question": (ex.get("question") or "")[:_MAX_QUESTION],
        "answer": ex.get("answer", "") or "",
        "analysis": analysis[:_MAX_ANALYSIS],
        "source_file": base,
        "source_index": i,
        "source_repo": repo,
    }


def iter_records() -> Iterator[dict]:
    """遍历全部源 (base + 2023 + 2024), yield raw record dict.

    缺失文件诚实跳过 (iter_examples 内部判断). 不写盘不入库 — 那是上层 (exam.py
    镜像入口 / DB loader) 的职责. 本函数纯产出.
    """
    for base_dir, src_list, id_prefix, repo in ALL_SOURCES:
        for relsrc in src_list:
            src = base_dir / relsrc
            if not src.exists():
                continue
            base = src.stem
            qtype = infer_question_type(base)
            for i, ex in iter_examples(src):
                yield _build_record(id_prefix, base, i, ex, qtype, repo)


if __name__ == "__main__":
    import collections

    recs = list(iter_records())
    dist = collections.Counter((r["year"], r["source_repo"]) for r in recs)
    print(f"total records: {len(recs)}")
    print("year x source_repo:")
    for (year, repo), n in sorted(dist.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        print(f"  {year!s:>6}  {repo:<35} {n}")
