"""2026 新高考全国II卷英语真题入库 — group 级 (与 2024 GAOKAO-Bench 同粒度).

数据源 (走专用 data_sources 链路获取, sources.yaml local_pdf_xgkii_english_2026):
  - 题面: data/external/exam_sources/local_pdfs/2026_xgkii_english.txt
           (12页扫描图 双通道 ocrmac×视觉裁决 转录; raw_question 全文供词汇/主题分析)
  - 答案: data/structured/exam_subquestions/xgkii_2026_subquestions.jsonl
           (官方评分参考逐项解析 + 内部交叉核验; group 聚合)

诚实分层 (坑16): 题型结构+答案=高保真真值; provenance source_repo='jhgk_xgkii_english_2026' (锦宏 tier-B 转印
官方评分参考, 待官方教育考试院评析交叉核验, analysis 标注); 无逐题 cognitive-skill 解析不臆造。
听力/读后续写无题面文本或主观题: 听力存问句文本; 写作主观题 answer=NULL (宁缺毋滥)。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from backend.services.trend import scope

ROOT = Path(__file__).resolve().parents[3]
TXT = ROOT / "data" / "external" / "exam_sources" / "local_pdfs" / "2026_xgkii_english.txt"
JSONL = ROOT / "data" / "structured" / "exam_subquestions" / "xgkii_2026_subquestions.jsonl"
YEAR = 2026
SOURCE_REPO = "jhgk_xgkii_english_2026"
SOURCE_FILE = "2026_xgkii_english.txt"
PROVINCE = scope.LIAONING_XGKII_2021   # province 标签收口 scope 单点 (辽宁)
PAPER_TYPE = scope.PAPER_XGKII          # paper_type canonical 单点 (新高考II卷)

# group 定义: (group_id, canonical 题型, 题号范围, 题面切段起止标记)
_GROUPS = [
    ("listening",   "听力",                  (1, 20),  "## 第一部分 听力",        "## 第二部分 阅读"),
    ("reading_A",   "阅读理解",              (21, 23), "#### A —",                "#### B —"),
    ("reading_B",   "阅读理解",              (24, 27), "#### B —",                "#### C —"),
    ("reading_C",   "阅读理解",              (28, 31), "#### C —",                "#### D —"),
    ("reading_D",   "阅读理解",              (32, 35), "#### D —",                "### 第二节 七选五"),
    ("seven",       "完形填空(七选五/语篇)", (36, 40), "### 第二节 七选五",        "## 第三部分"),
    ("cloze",       "完形填空",              (41, 55), "### 第一节 完形填空",      "### 第二节 语法填空"),
    ("grammar",     "语法填空",              (56, 65), "### 第二节 语法填空",      "## 第四部分"),
    # 写作(应用文/读后续写)主观题不入 exam_questions (与 2021/2022 EOL "写作 rescope 不入"惯例一致;
    #  无客观答案 + 题型未登记 question_types.yaml)。题面留 .txt, 主题留 subquestions jsonl 供分析。
]


def _section(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i:j if j >= 0 else len(text)].strip()


def _answers(rows: list[dict], lo: int, hi: int) -> str:
    """group 内题号 lo..hi 的已核验答案聚合成串 (逐题 'n.X', 主观题 None→'')."""
    by_num = {r["question_number"]: r.get("answer") for r in rows}
    parts = [f"{n}.{by_num[n]}" for n in range(lo, hi + 1) if by_num.get(n)]
    return " ".join(parts)


# 2026-07-09全网挖掘补: 语法填空(56-65)逐题解析, 来源 zy.21cnjy.com/25943486(21世纪教育网,
# 标注"网络收集版", 2026-06-12; 与本项目独立OCR转录的raw_question/answer逐字比对100%一致,
# 双独立源吻合可信; 教育部官方评析主题描述[太极课/丹田]间接印证语篇真实性)。
# 诚实分层: 深度较浅(一句话结论式, 非展开推理), tier=Low(C), 标注"简明版"供未来升级。
_GRAMMAR_ANALYSIS_2026 = {
    56: "副词修饰动词remain，表示完全地保持静止，故填entirely。",
    57: "名词，指代太极教练，故填instructor。",
    58: "并列连词，连接mind和body，故填and。",
    59: "名词复数，双脚为复数概念，故填feet。",
    60: "固定搭配be supposed to do(应该做某事)，故填am supposed。",
    61: "非限制性定语从句，指代positions，故填which。",
    62: "形容词修饰名词names，意为描述性的名称，故填descriptive。",
    63: "固定搭配keep eyes on(注视)，故填on。",
    64: "介词despite后接动名词，故填being。",
    65: "固定句型it's time to do sth.(是时候做某事)，故填to meet。",
}


def _grammar_analysis(lo: int, hi: int) -> str:
    """语法填空组逐题解析拼接(简明版, 2026-07-09补, 见_GRAMMAR_ANALYSIS_2026模块注释)."""
    parts = [f"{n}.{_GRAMMAR_ANALYSIS_2026[n]}" for n in range(lo, hi + 1) if n in _GRAMMAR_ANALYSIS_2026]
    return " ".join(parts)


def _build_rows() -> list[dict]:
    text = TXT.read_text(encoding="utf-8") if TXT.exists() else ""
    subq = [json.loads(l) for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()] if JSONL.exists() else []
    rows = []
    for gid, qtype, (lo, hi), start, end in _GROUPS:
        body = _section(text, start, end)
        ans = _answers(subq, lo, hi)
        provenance_note = (f"题号{lo}-{hi}; 答案源=官方评分参考(锦宏转印 tier-B, 待官方评析交叉核验); "
                            f"题面=2026扫描图双通道ocrmac×视觉裁决转录")
        analysis = provenance_note
        if gid == "grammar":
            g_analysis = _grammar_analysis(lo, hi)
            if g_analysis:
                analysis = (f"{g_analysis} | {provenance_note}; 解析源=zy.21cnjy.com/25943486"
                            f"(网络收集版简明解析, tier=Low(C), 与本地独立OCR转录双源吻合)")
        rows.append({
            "question_id": f"xgkii/2026/{gid}",
            "year": YEAR, "province": PROVINCE, "paper_type": PAPER_TYPE,
            "question_type": qtype,
            "raw_question": body[:8000],
            "answer": ans or None,
            "analysis": analysis,
            "source_file": SOURCE_FILE, "source_index": lo, "source_repo": SOURCE_REPO,
        })
    return rows


def import_xgkii_2026(con: duckdb.DuckDBPyConnection) -> dict:
    """入 2026 真题 (group 级, idempotent). 返回入库数 + 客观题答案覆盖."""
    rows = _build_rows()
    con.execute(
        "DELETE FROM exam_questions_all WHERE year = ? AND source_repo = ?",
        [YEAR, SOURCE_REPO],
    )
    con.executemany(
        "INSERT INTO exam_questions_all (question_id, year, province, paper_type, question_type, "
        "raw_question, answer, analysis, source_file, source_index, source_repo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(r["question_id"], r["year"], r["province"], r["paper_type"], r["question_type"],
          r["raw_question"], r["answer"], r["analysis"], r["source_file"],
          r["source_index"], r["source_repo"]) for r in rows],
    )
    return {"groups": len(rows), "with_answer": sum(1 for r in rows if r["answer"])}
