"""高考英语题镜像 + 辽宁卷过滤启发式.

输入: ~/Documents/M/gaokao/data/external/GAOKAO-Bench/Data/{Objective,Subjective}_Questions/*English*.json
输出: data/external/gaokao_bench/<file_basename>.jsonl + DB exam_questions 行

辽宁卷判别 (启发式, 因 GAOKAO-Bench 不显式标省):
  - 2010-2014: 题面含 "辽宁" 优先，否则按题型语料映射为 "独立命题" 占位
  - 2015-2016: 辽宁新课标 II 卷 / 全国统一 II 卷混合, 优先按文本证据分层
  - 2017-2020: 年份已知为 "全国卷 II"；若题面有辽宁标注则标注为“辽宁(全国卷 II, 辽宁证据)"
  - 2021+: 仅遇到明确新课标/辽宁证据时才认定为辽宁；否则按题面/分类器标记为全国卷或未知
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

LIAONING_KEYWORDS = ["辽宁", "辽宁卷", "辽宁(新课标 II", "辽宁(全国"]
NATIONAL_I_KEYWORDS = ["新课标全国Ⅰ卷", "新课标I卷", "新课标 I", "全国I卷", "全国Ⅰ卷"]
NATIONAL_II_KEYWORDS = ["全国甲卷", "全国乙卷", "全国Ⅱ", "全国II", "全国二卷", "新课标全国Ⅱ卷", "新课标Ⅱ", "新课标 II"]


def infer_province(year: int | None, question_text: str, category: str | None = None) -> str:
    """启发式判 province. 返回标准化 province label."""
    if year is None:
        return "未知"
    text = question_text or ""
    cat = category or ""
    if _has_keyword(text, LIAONING_KEYWORDS):
        return "辽宁"
    if _has_keyword(cat, NATIONAL_I_KEYWORDS):
        return "全国 I 卷"
    if year <= 2014:
        return "辽宁 (独立命题, 2010-2014)" if _has_keyword(text, "辽宁") else "辽宁 (独立命题)"
    if 2015 <= year <= 2016:
        if _has_keyword(text, "辽宁"):
            return "辽宁 (新课标 II 卷, 2015-2016)"
        return "全国 II 卷 (2015-2016)"
    if 2017 <= year <= 2020:
        if _has_keyword(cat, NATIONAL_I_KEYWORDS):
            return "全国 I 卷"
        return "辽宁 (全国卷 II, 改革前)" if _has_keyword(text, "辽宁") else "全国 II 卷"
    if year >= 2021:
        if _has_keyword(text, NATIONAL_I_KEYWORDS) or _has_keyword(cat, NATIONAL_I_KEYWORDS):
            return "全国 I 卷"
        if _has_keyword(text, NATIONAL_II_KEYWORDS) or _has_keyword(cat, NATIONAL_II_KEYWORDS):
            # 新课标 II 未必为辽宁，先不默认认定
            return "全国 II 卷"
        return "辽宁 (推断, 2021+ 新课标 II)" if _has_keyword(text, "新课标 II") else "未知"
    return "未知"


def _has_keyword(text: str, keywords: list[str] | str) -> bool:
    if isinstance(keywords, str):
        return keywords in text
    return any(k in text for k in keywords)


def infer_question_type(file_basename: str) -> str:
    name = file_basename.lower()
    # L-2026-05-25-O: 交叉验证发现 cloze_test=七选五, cloze_passage=语法填空, fill_in_blanks=完形填空
    if "cloze_test" in name: return "完形填空(七选五/语篇)"
    if "cloze_passage" in name: return "语法填空"
    if "reading_comp" in name: return "阅读理解"
    if "fill_in_blanks" in name: return "完形填空"
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
    province = infer_province(year, qtext, ex.get("category"))
    paper_type = _infer_paper_type(year, province)
    return {
        "question_id": f"{id_prefix}/{base}/{i}",
        "year": year,
        "province": province,
        "paper_type": paper_type,
        "question_type": qtype,
        "raw_question": qtext[:8000],
        "answer": ex.get("answer", ""),
        "analysis": ex.get("analysis", "")[:4000] if ex.get("analysis") else "",
        "source_file": base, "source_index": i, "source_repo": repo,
    }


def _infer_paper_type(year: int | None, province: str) -> str:
    if not year:
        return "未知"
    if province.startswith("辽宁"):
        if year >= 2021:
            return "新课标 II 卷"
        return "全国 II 卷"
    if province.startswith("全国 I"):
        return "全国 I 卷"
    if province.startswith("全国 II"):
        return "全国 II 卷"
    if "2021" in province and "推断" in province:
        return "新课标 II 卷"
    return "未知"


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
