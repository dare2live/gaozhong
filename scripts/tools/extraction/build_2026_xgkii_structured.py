#!/usr/bin/env python3
"""2026 新高考全国II卷英语 → 结构化 subquestions jsonl (题型骨架 + 已核验答案 + 主题).

源 (真相源, 走专用 data_sources 链路获取, 见 sources.yaml local_pdf_xgkii_english_2026):
  - 题面: data/external/exam_sources/local_pdfs/2026_xgkii_english.txt (12页扫描图 双通道 ocrmac×视觉裁决转录)
  - 答案: data/external/exam_sources/local_pdfs/2026_xgkii_english_answers.pdf (官方评分参考, 有文字层)
           答案键已逐项解析 + 内部交叉核验(语法填空56-65 与题面空格语法吻合)。

诚实分层 (坑16):
  - 题型结构(section/question_type) + 答案 = 高保真真值 (verified)。
  - 锦宏 tier-B 民间聚合, 答案待官方教育考试院评析交叉核验 (provenance 标 jhgk_reprint_official_key)。
  - **无逐题 cognitive-skill 子类型(细节/推理/主旨)**: 锦宏答案PDF无逐题解析, 不臆造, analysis 留空待教研标注/真值源补。

输出: data/structured/exam_subquestions/xgkii_2026_subquestions.jsonl (与 xgkii_2021_2025 同 schema)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "structured" / "exam_subquestions" / "xgkii_2026_subquestions.jsonl"
SRC_FILE = "2026_xgkii_english.txt"
PROV = "jhgk_reprint_official_key"  # 锦宏转印官方评分参考 (tier-B, 待官方交叉核验)

# 已核验答案键 (听力1-20 / 阅读21-40 / 完形41-55 字母; 语法填空56-65 词)
ANS_LETTER = {
    1:"C",2:"A",3:"B",4:"C",5:"A",6:"C",7:"B",8:"A",9:"C",10:"B",
    11:"A",12:"C",13:"A",14:"B",15:"A",16:"C",17:"B",18:"A",19:"B",20:"B",
    21:"C",22:"B",23:"D",24:"A",25:"D",26:"B",27:"A",28:"C",29:"B",30:"C",
    31:"B",32:"C",33:"D",34:"D",35:"A",36:"A",37:"C",38:"G",39:"D",40:"F",
    41:"D",42:"B",43:"C",44:"A",45:"C",46:"B",47:"D",48:"D",49:"A",50:"B",
    51:"C",52:"D",53:"B",54:"A",55:"C",
}
ANS_GRAMMAR = {  # 语法填空 (词形/填词); 与题面空格语法已交叉核验
    56:"entirely",57:"instructor",58:"and",59:"feet",60:"am supposed",
    61:"which",62:"descriptive",63:"on",64:"being",65:"to meet",
}

# 阅读 A-D 篇主题 (题材, 供主题分析; 来自题面核验)
READING = {
    "A": {"q": (21, 23), "theme": "饮食文化/餐厅推荐(应用文广告)", "genre": "应用文/广告"},
    "B": {"q": (24, 27), "theme": "人与社会/建筑遗产保护(Frank Lloyd Wright 住宅)", "genre": "记叙文/人物"},
    "C": {"q": (28, 31), "theme": "人与自然/海平面参照系的历史(科普书序)", "genre": "说明文/科普"},
    "D": {"q": (32, 35), "theme": "人与自然/绿色能源(巴塞罗那地铁再生制动)", "genre": "说明文/科技"},
}
# 完形 / 七选五 / 语法 / 读后续写 主题
THEME = {
    "seven": "人与自我/家庭教育(培养孩子责任感 work ethic)",
    "cloze": "人与自我/成长(从教师到追梦写作)",
    "grammar": "人与社会/传统文化(太极 tai chi 初体验)",
    "essay": "人与社会/校园生活(英语作文集配图 给Kate邮件)",
    "continuation": "人与自我/健康(熬夜 night owl 与心脏警示)",
}


def _row(qnum, qtype, section, ans, *, passage_label=None, theme=None, genre=None):
    return {
        "year": 2026, "paper_type": "新高考II卷", "province": "辽宁",
        "question_type": qtype, "section": section,
        "passage_label": passage_label, "question_number": qnum,
        "stem": "", "options": {},   # 题面全文在 2026_xgkii_english.txt; 骨架行不重复存
        "answer": ans,
        "analysis": "",  # 无逐题cognitive-skill解析(锦宏未供); 不臆造 (坑16)
        "theme": theme, "genre": genre,
        "source": PROV, "source_file": SRC_FILE,
        "id": f"xgkii/2026/{qnum}",
    }


def build() -> list[dict]:
    rows = []
    # 听力 1-20
    for n in range(1, 21):
        rows.append(_row(n, "listening", "听力", ANS_LETTER[n]))
    # 阅读 21-35 (A-D)
    for lab, meta in READING.items():
        lo, hi = meta["q"]
        for n in range(lo, hi + 1):
            rows.append(_row(n, "reading_comprehension", "阅读理解", ANS_LETTER[n],
                             passage_label=lab, theme=meta["theme"], genre=meta["genre"]))
    # 七选五 36-40
    for n in range(36, 41):
        rows.append(_row(n, "seven_choose_five", "七选五", ANS_LETTER[n], theme=THEME["seven"]))
    # 完形 41-55
    for n in range(41, 56):
        rows.append(_row(n, "cloze", "完形填空", ANS_LETTER[n], theme=THEME["cloze"]))
    # 语法填空 56-65
    for n in range(56, 66):
        rows.append(_row(n, "grammar_filling", "语法填空", ANS_GRAMMAR[n], theme=THEME["grammar"]))
    # 写作 (无字母答案; 评分档次)
    rows.append(_row(66, "applied_writing", "应用文写作", None, theme=THEME["essay"]))
    rows.append(_row(67, "continuation_writing", "读后续写", None, theme=THEME["continuation"]))
    return rows


def main() -> int:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows → {OUT.relative_to(ROOT)}")
    # 自检: 答案覆盖
    letter = [r for r in rows if r["answer"] and len(str(r["answer"])) <= 1]
    grammar = [r for r in rows if r["question_type"] == "grammar_filling"]
    print(f"  字母答案题: {len(letter)} (听力20+阅读15+七选五5+完形15=55预期)")
    print(f"  语法填空: {len(grammar)} (预期10)")
    print(f"  写作: {len([r for r in rows if r['answer'] is None])} (预期2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
