"""高考英语题镜像入口 (thin orchestrator) — extract + clean 两层组装入库.

2026-06-15 模块化 (M6): 抽取/分类逻辑下沉到 data_sources 专门模块, 本文件只做"装配 + 入库":
  - extract 层  backend/services/data_sources/extract/gaokao_bench.py
      读 3 个 repo JSON → raw record (含 category, 不算卷型)
  - clean 层    backend/services/data_sources/clean/exam_paper.py
      classify_paper(year, category, text) → (province, paper_type) 诚实卷型标注

辽宁卷判别 (category-aware, 见 clean/exam_paper.py 注释):
  只有 "新课标II + year>=2015" = 辽宁卷; 其余诚实标非辽宁卷型 (L-N/L-P/L-R 防回归).
  辽宁卷型史: 2010-2014 自主命题(无国家卷) / 2015 起用新课标全国II卷.

不直接覆盖 gaokao 项目 R2 结论 (辽宁卷有效卷级样本 ~11), 只做"题级"镜像 + 标 province.

兼容层: classify_paper / infer_province / infer_question_type / iter_examples / LN_II_*
常量保留 re-export, 历史 import 不破 (Rule 6 可扩展; 单一真相在 data_sources 模块).
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.services.data_sources.clean.exam_paper import (
    LN_II_2015_2020,
    LN_II_2021,
    classify_paper,
)
from backend.services.data_sources.extract.gaokao_bench import (
    GAOKAO_DATA,
    UPDATES_DIR,
    UPDATES_DIR_2024,
    infer_question_type,
    iter_examples,
    iter_records,
)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT_DIR = ROOT / "data/external/gaokao_bench"

# local_pdf 是这些年辽宁卷的**权威源**(更全: 含应用文/续写/语法填空分项); GAOKAO-Bench(-Updates)
# 的同年辽宁记录是**同一份卷的重复采集**(强验证 wf_9d0ef21a B1: 2024 四篇阅读逐字相同), 让位 superseded。
# 真相源 = scripts/import_recent_exams._local_pdf_sources() / sources.yaml(family=exam_truth_source_local_pdf);
# 此处常量与之对账(local_pdf 仅 2024/2025; gbu 最高到 2024 → 实际仅 2024 有重复, 2025 为前瞻 guard)。
LOCAL_PDF_LIAONING_YEARS = (2024, 2025)

# 兼容 re-export (上述 import 已引入 classify_paper / infer_question_type / iter_examples /
# LN_II_* / 路径常量); 下面只补 infer_province 这个仅 province 的 compat wrapper.
__all__ = [
    "classify_paper", "infer_province", "infer_question_type", "iter_examples",
    "iter_records", "mirror_to_jsonl", "LN_II_2015_2020", "LN_II_2021",
    "GAOKAO_DATA", "UPDATES_DIR", "UPDATES_DIR_2024", "OUT_DIR",
]


def infer_province(year: int | None, question_text: str = "", category: str | None = None) -> str:
    """compat wrapper — 仅返 province. 实际分类见 clean.exam_paper.classify_paper."""
    return classify_paper(year, category, question_text)[0]


def _to_db_row(raw: dict) -> dict:
    """extract 层 raw record (含 category) → DB exam_questions 行 (含 province/paper_type).

    单一计算点 (Rule 1): 卷型分类只在 clean.exam_paper.classify_paper 算一次.
    """
    province, paper_type = classify_paper(raw["year"], raw["category"], raw["raw_question"])
    return {
        "question_id": raw["question_id"],
        "year": raw["year"],
        "province": province,
        "paper_type": paper_type,
        "question_type": raw["question_type"],
        "raw_question": raw["raw_question"],
        "answer": raw["answer"],
        "analysis": raw["analysis"],
        "source_file": raw["source_file"],
        "source_index": raw["source_index"],
        "source_repo": raw["source_repo"],
    }


def mirror_to_jsonl(write_db_conn=None) -> dict:
    """组装 GAOKAO-Bench(+Updates 2023/2024) → DB exam_questions, 返回分布 summary.

    extract (gaokao_bench.iter_records) → clean (classify_paper) → load (DB).
    write_db_conn 为 None 时只统计不入库 (dry-run / CLI 自检).
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"files": set(), "examples": 0, "by_province": {}, "by_type": {}}
    db_rows = []
    summary["superseded_by_local_pdf"] = 0
    for raw in iter_records():
        row = _to_db_row(raw)
        if row["province"].startswith("辽宁") and row["year"] in LOCAL_PDF_LIAONING_YEARS:
            summary["superseded_by_local_pdf"] += 1   # B1: 同卷 local_pdf 更全, gbu 让位
            continue
        db_rows.append(row)
        summary["files"].add(row["source_file"])
        summary["examples"] += 1
        summary["by_province"][row["province"]] = summary["by_province"].get(row["province"], 0) + 1
        summary["by_type"][row["question_type"]] = summary["by_type"].get(row["question_type"], 0) + 1
    summary["files"] = len(summary["files"])
    if write_db_conn is not None and db_rows:
        # P0-1 (架构优化 2026-06-26): 只删本 mirror 自己写的 source_repo, 不再 DELETE WHERE exam_type='高考'。
        # 旧谓词过宽 — EOL(110)/2026锦宏(8)/中考 写的也是 exam_type='高考', 单独重跑此 mirror 会**静默清空它们**
        # (仅靠 init_db Layer 2<2a<2a2 层序侥幸); 按 source_repo 精确删 = 幂等且不误伤邻入库路径 (死红线: 真值不可被捷径清空)。
        repos = sorted({r["source_repo"] for r in db_rows})
        write_db_conn.executemany("DELETE FROM exam_questions_all WHERE source_repo = ?",
                                  [(r,) for r in repos])
        write_db_conn.executemany(
            "INSERT OR REPLACE INTO exam_questions_all (question_id, year, province, paper_type, "
            "question_type, raw_question, answer, analysis, source_file, source_index, source_repo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",   # exam_type 默认'高考'
            [(r["question_id"], r["year"], r["province"], r["paper_type"],
              r["question_type"], r["raw_question"], r["answer"], r["analysis"],
              r["source_file"], r["source_index"], r["source_repo"]) for r in db_rows],
        )
    return summary


if __name__ == "__main__":
    s = mirror_to_jsonl()
    print(json.dumps(s, ensure_ascii=False, indent=2))
