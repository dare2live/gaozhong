"""EOL 真题入库 — 把 2021/2022 辽宁新高考全国II卷真值入 exam_questions.

数据源 (中国教育在线 EOL, 已 M0 review):
  - structured_draft.jsonl  : 题级元数据 + stem_preview
  - review_decisions.jsonl  : 权威 review (import_ready + 核验答案 + source_span)

只入 decision_status='import_ready' 且有 answer 的项 (宁缺毋滥):
  - 笔试客观题答案源 = 官方 EOL 参考答案表 (偏移编号已核验)
  - 2021 听力答案源 = Sohu 候选 (题面已对 EOL 核验) → analysis 留 lineage 标注
  - 写作 (rescope, 主观题无客观答案) → 不入

替换 GAOKAO-Bench 2021/2022 占位 (那是混合卷, 含全国甲卷, 见 L-N/L-P).
provenance source_repo='eol_xgkii_english_{year}' 被 exam_province / data_accuracy_check
check_21 认作可信源 (可断言辽宁新课标II卷).
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from backend.services.trend import scope

ROOT = Path(__file__).resolve().parents[3]
EOL_DIR = ROOT / "data" / "external" / "exam_sources" / "eol"
YEARS = (2021, 2022)

PROVINCE = scope.LIAONING_XGKII_2021   # G3: province标签收口 scope 单点
PAPER_TYPE = scope.PAPER_XGKII          # paper_type canonical 值收口 scope 单点

# EOL question_type → 项目 exam_questions 题型 taxonomy
QTYPE_MAP = {
    "reading_or_seven_choose_five": "阅读理解",
    "seven_choose_five": "完形填空(七选五/语篇)",
    "cloze_fill_in_blanks": "完形填空",
    "grammar_fill": "语法填空",
    "listening_raw_unkeyed": "听力",
}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _build_rows(year: int) -> list[dict]:
    draft = {
        r["observed_question_number"]: r
        for r in _read_jsonl(EOL_DIR / f"{year}_xgkii_english_eol_structured_draft.jsonl")
        if isinstance(r.get("observed_question_number"), int)
    }
    rows = []
    for d in _read_jsonl(EOL_DIR / "review_decisions" / f"{year}_xgkii_english_eol_review_decisions.jsonl"):
        obs = d.get("observed_question_number")
        if not isinstance(obs, int) or d.get("decision_status") != "import_ready" or not d.get("answer"):
            continue
        qtype = QTYPE_MAP.get(d.get("question_type"))
        if not qtype:
            continue
        analysis = f"答案核验: {d.get('review_note', '')} [source_span: {d.get('source_span', '')}]"
        rows.append({
            "question_id": f"eol/{year}/xgkii/{obs}",
            "year": year, "province": PROVINCE, "paper_type": PAPER_TYPE,
            "question_type": qtype,
            "raw_question": (draft.get(obs, {}).get("stem_preview") or "")[:8000],
            "answer": d["answer"], "analysis": analysis[:4000],
            "source_file": f"{year}_xgkii_english_eol.txt",
            "source_index": obs, "source_repo": f"eol_xgkii_english_{year}",
        })
    return rows


def import_eol_exams(con: duckdb.DuckDBPyConnection) -> dict:
    """入 2021/2022 真题, 替换 GAOKAO-Bench 占位. 返回每年入库数 (idempotent)."""
    summary = {}
    for year in YEARS:
        rows = _build_rows(year)
        if not rows:
            summary[year] = 0
            continue
        # 删旧: GAOKAO-Bench 占位 + 本 EOL 源 (idempotent 重入)
        con.execute(
            "DELETE FROM exam_questions_all WHERE year = ? "
            "AND (source_repo = 'OpenLMLab/GAOKAO-Bench' OR source_repo = ?)",
            [year, f"eol_xgkii_english_{year}"],
        )
        con.executemany(
            "INSERT INTO exam_questions_all (question_id, year, province, paper_type, question_type, "
            "raw_question, answer, analysis, source_file, source_index, source_repo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",   # exam_type 默认'高考'
            [(r["question_id"], r["year"], r["province"], r["paper_type"],
              r["question_type"], r["raw_question"], r["answer"], r["analysis"],
              r["source_file"], r["source_index"], r["source_repo"]) for r in rows],
        )
        summary[year] = len(rows)
    return summary
