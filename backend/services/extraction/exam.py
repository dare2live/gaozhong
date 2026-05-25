"""高考英语题镜像 + 辽宁卷过滤启发式.

输入: ~/Documents/M/gaokao/data/external/GAOKAO-Bench/Data/{Objective,Subjective}_Questions/*English*.json
输出: data/external/gaokao_bench/<file_basename>.jsonl + DB exam_questions 行

辽宁卷判别 (启发式, 因 GAOKAO-Bench 不显式标省):
  - 2021 起新课标 II 卷 → 辽宁 (用户 2026-05-23 硬约束)
  - 2017-2020 全国卷 II → 辽宁 (省份高考改革前)
  - 2010-2016 辽宁卷独立命题 → 辽宁 (从题面 grep "辽宁"/"新课标全国" 推断)
  - 题面无明显省份信息 → "未知" (保留, 不丢)
不直接覆盖 gaokao 项目 R2 结论 (辽宁卷有效卷级样本 ~11), 我们只做"题级"镜像 + 标 province.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent.parent.parent
GAOKAO_DATA = Path.home() / "Documents/M/gaokao/data/external/GAOKAO-Bench/Data"
OUT_DIR = ROOT / "data/external/gaokao_bench"

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

UPDATES_DIR = ROOT / "data" / "external" / "gaokao_bench_2023"
ENGLISH_SOURCES_2023 = [
    "2023_English_Cloze_Test.json",
    "2023_English_Fill_in_Blanks.json",
    "2023_English_Reading_Comp.json",
]

LIAONING_KEYWORDS = ["辽宁", "新课标全国Ⅱ", "新课标Ⅱ", "新课标II", "全国新课标Ⅱ"]
NATIONAL_II_HINT = ["新课标卷Ⅱ", "全国Ⅱ", "全国II"]


def infer_province(year: int | None, question_text: str) -> str:
    """启发式判 province. 返回 "辽宁" / "全国 II 卷" / "未知"."""
    if year is None:
        return "未知"
    text = question_text or ""
    if _has_keyword(text, LIAONING_KEYWORDS):
        return "辽宁"
    if year >= 2021:
        return "辽宁 (新课标 II)" if _has_keyword(text, NATIONAL_II_HINT) else "辽宁 (推断, 2021+ 新课标 II)"
    if 2017 <= year <= 2020 and _has_keyword(text, NATIONAL_II_HINT):
        return "辽宁 (全国卷 II, 改革前)"
    return "未知"


def _has_keyword(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def infer_question_type(file_basename: str) -> str:
    name = file_basename.lower()
    if "cloze_test" in name: return "完形填空"
    if "cloze_passage" in name: return "完形填空(七选五/语篇)"
    if "reading_comp" in name: return "阅读理解"
    if "fill_in_blanks" in name: return "语法填空"
    if "error_correction" in name: return "短文改错"
    if "mcq" in name: return "单选(语法/词汇)"
    return "其他"


def iter_examples(src_file: Path) -> Iterable[dict]:
    if not src_file.exists():
        return
    data = json.loads(src_file.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "example" in data:
        for i, ex in enumerate(data["example"]):
            yield i, ex
    elif isinstance(data, list):
        for i, ex in enumerate(data):
            yield i, ex


def _build_record(id_prefix: str, base: str, i: int, ex: dict,
                   qtype: str, repo: str) -> dict:
    year = ex.get("year")
    try: year = int(year) if year else None
    except: year = None
    qtext = ex.get("question") or ""
    province = infer_province(year, qtext)
    return {
        "question_id": f"{id_prefix}/{base}/{i}",
        "year": year, "province": province,
        "paper_type": "新课标 II 卷" if "辽宁" in province else "未知",
        "question_type": qtype,
        "raw_question": qtext[:8000],
        "answer": ex.get("answer", ""),
        "analysis": ex.get("analysis", "")[:4000] if ex.get("analysis") else "",
        "source_file": base, "source_index": i, "source_repo": repo,
    }


def mirror_to_jsonl(write_db_conn=None) -> dict:
    """Mirror to data/external/gaokao_bench/*.jsonl, optionally load to DB."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"files": 0, "examples": 0, "by_province": {}, "by_type": {}}
    db_rows = []
    all_sources = [
        (GAOKAO_DATA, ENGLISH_SOURCES, "gb", "OpenLMLab/GAOKAO-Bench"),
        (UPDATES_DIR, ENGLISH_SOURCES_2023, "gbu", "OpenLMLab/GAOKAO-Bench-Updates"),
    ]
    for base_dir, src_list, id_prefix, repo in all_sources:
        for relsrc in src_list:
            src = base_dir / relsrc
            if not src.exists():
                continue
            summary["files"] += 1
            base = src.stem
            qtype = infer_question_type(base)
            for i, ex in iter_examples(src):
                rec = _build_record(id_prefix, base, i, ex, qtype, repo)
                db_rows.append(rec)
                summary["examples"] += 1
                summary["by_province"][rec["province"]] = summary["by_province"].get(rec["province"], 0) + 1
                summary["by_type"][qtype] = summary["by_type"].get(qtype, 0) + 1
    if write_db_conn is not None and db_rows:
        write_db_conn.execute("DELETE FROM exam_questions")
        write_db_conn.executemany(
            "INSERT OR REPLACE INTO exam_questions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["question_id"], r["year"], r["province"], r["paper_type"],
              r["question_type"], r["raw_question"], r["answer"], r["analysis"],
              r["source_file"], r["source_index"], r["source_repo"]) for r in db_rows],
        )
    return summary


if __name__ == "__main__":
    s = mirror_to_jsonl()
    print(json.dumps(s, ensure_ascii=False, indent=2))
