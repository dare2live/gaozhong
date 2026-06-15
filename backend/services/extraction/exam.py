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

UPDATES_DIR_2024 = ROOT / "data" / "external" / "gaokao_bench_2024"
ENGLISH_SOURCES_2024 = [
    "2024_English_Cloze_Test.json",
    "2024_English_Fill_in_Blanks.json",
    "2024_English_Reading_Comp.json",
]

# 卷型 ↔ 辽宁 (provenance honest): GAOKAO-Bench/Updates 的 category 区分
# 新课标I/II/III/甲/乙. 辽宁卷型史: 2010-2014 自主命题(无国家卷) / 2015 起用新课标全国II卷.
# 故只有 "新课标II + year>=2015" = 辽宁卷; 其余诚实标非辽宁卷型, 不冒充辽宁 (L-N/L-P/L-R 防回归).
LN_II_2015_2020 = "辽宁 (新课标 II 卷, 2015-2020)"
LN_II_2021 = "辽宁 (新课标 II 卷, 2021+)"


def _norm_cat(category: str | None) -> str:
    c = category or ""
    for a, b in (("Ⅰ", "I"), ("Ⅱ", "II"), ("Ⅲ", "III"), ("ⅰ", "I"), ("ⅱ", "II"), ("ⅲ", "III")):
        c = c.replace(a, b)
    return c.upper()


def _juan_token(c: str) -> str:
    """normalized category → 卷型 token (甲/乙/III/II/I/'')."""
    if "甲" in c:
        return "甲"
    if "乙" in c:
        return "乙"
    if "III" in c or "三" in c:
        return "III"
    if "II" in c or "二" in c:
        return "II"
    if "I" in c or "一" in c:
        return "I"
    return ""


# 卷型 token → (province, paper_type); II 因 year 区分辽宁与否, 单独处理.
_JUAN_MAP = {
    "甲": ("全国甲卷 (非辽宁)", "全国甲卷"),
    "乙": ("全国乙卷 (非辽宁)", "全国乙卷"),
    "III": ("全国新课标 III 卷 (非辽宁)", "新课标 III 卷"),
    "I": ("全国新课标 I 卷 (非辽宁)", "新课标 I 卷"),
}


def classify_paper(year: int | None, category: str | None,
                   question_text: str = "") -> tuple[str, str]:
    """(province, paper_type) — category-aware 诚实卷型标注 (见上注释).

    只有 "新课标II + year>=2015" = 辽宁卷; 其余诚实标非辽宁卷型.
    """
    if year is None:
        return "未知", "未知"
    tok = _juan_token(_norm_cat(category))
    if tok in _JUAN_MAP:
        return _JUAN_MAP[tok]
    if tok == "II":
        if year >= 2015:
            return (LN_II_2021 if year >= 2021 else LN_II_2015_2020), "新课标 II 卷"
        return "全国新课标 II 卷 (2010-2014, 非辽宁; 辽宁当年自主命题)", "新课标 II 卷"
    if "解析版" in (category or ""):
        return "未知 (解析版, 待核验卷型)", "未知"
    return "未知 (GAOKAO-Bench 无明确卷型)", "未知"


def infer_province(year: int | None, question_text: str = "", category: str | None = None) -> str:
    """compat wrapper — 仅返 province. 实际分类见 classify_paper."""
    return classify_paper(year, category, question_text)[0]


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
    province, paper_type = classify_paper(year, ex.get("category"), qtext)
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


def mirror_to_jsonl(write_db_conn=None) -> dict:
    """Mirror to data/external/gaokao_bench/*.jsonl, optionally load to DB."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"files": 0, "examples": 0, "by_province": {}, "by_type": {}}
    db_rows = []
    all_sources = [
        (GAOKAO_DATA, ENGLISH_SOURCES, "gb", "OpenLMLab/GAOKAO-Bench"),
        (UPDATES_DIR, ENGLISH_SOURCES_2023, "gbu", "OpenLMLab/GAOKAO-Bench-Updates"),
        (UPDATES_DIR_2024, ENGLISH_SOURCES_2024, "gbu24", "OpenLMLab/GAOKAO-Bench-Updates-2024"),
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
