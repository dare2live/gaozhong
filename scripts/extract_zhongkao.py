"""沈阳/辽宁中考英语真题 → exam_question 记录 (按高考 exam_questions schema 结构化).

输入: data/junior_high/exams/<year>_liaoning/exam_ocr.txt (PaddleOCR×视觉双源核对的真题文本)
      + paper_structure.json (题型分段 + 语篇填空考点 + 答案可得性).
输出: data/junior_high/exams/<year>_liaoning/exam_questions.jsonl
      每题 {question_id, year, province, exam_type, paper_type, question_type, question_number,
            raw_question(stem+options), options, answer, kaodian, passage_ref, source, provenance}

题型按题号段判 (paper_structure 定): 1-16四选一/17-20五选四/21-30完形/31-40语篇填空/41-44阅读表达/45书面表达。
MCQ stem+options 从 OCR 解析; 语篇填空考点 从 paper_structure; 答案=2025无key标unknown(语篇填空由hint可得)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _qtype(n: int) -> str:
    if 1 <= n <= 16:
        return "阅读理解(四选一)"
    if 17 <= n <= 20:
        return "阅读理解(五选四/选句填空)"
    if 21 <= n <= 30:
        return "完形填空"
    if 31 <= n <= 40:
        return "语篇填空(语法填空)"
    if 41 <= n <= 44:
        return "阅读与表达(开放问答)"
    return "书面表达(应用文)"


_OPT_RE = re.compile(r"^([A-E])[\.．]\s*(.+)$")


def _add_opts(rec: dict, text: str) -> None:
    """一行可能含多个选项 (A.x B.y) 或单个; 拆进 rec['options']."""
    for mo in re.finditer(r"([A-E])[\.．]\s*([^A-E]+?)(?=\s+[A-E][\.．]|$)", text):
        rec["options"][mo.group(1)] = mo.group(2).strip()


def _parse_mcq(lines: list[str]) -> dict[int, dict]:
    """'N. stem'(阅读) 或 'N. A.opt'(完形无题干) + 后续 A-E 选项行 → {qnum:{stem,options}}."""
    out: dict[int, dict] = {}
    cur = None
    for raw in lines:
        ln = raw.strip()
        m = re.match(r"^(\d{1,2})[\.．]\s*(.*)$", ln)
        if m and 1 <= int(m.group(1)) <= 45:
            cur = int(m.group(1))
            out[cur] = {"stem": "", "options": {}}
            rest = m.group(2).strip()
            if _OPT_RE.match(rest):          # N. 后直接是选项 (完形无题干, 选项A同行)
                _add_opts(out[cur], rest)
            else:
                out[cur]["stem"] = rest      # 阅读: N. 题干
        elif cur is not None and _OPT_RE.match(ln):
            _add_opts(out[cur], ln)
    return out


def _kaodian_map(paper: dict) -> dict[int, str]:
    """统一语篇填空(31-40)考点 — 坑19 跨年异构: 2024=section三 grammar_points dict / 2025=list."""
    km: dict[int, str] = {}
    for s in paper["sections"]:
        gp = s.get("grammar_points")
        if isinstance(gp, dict):                          # 2024: {"31":"and连词",...}
            km.update({int(k): v for k, v in gp.items()})
        elif isinstance(gp, list):                        # 2025: 逐空列表
            km.update({31 + i: v for i, v in enumerate(gp)})
    return km


def _record(n: int, year: int, paper: dict, mcq: dict, kmap: dict, akey: dict | None) -> dict:
    rec = {"question_id": f"ZK-LN-{year}-{n:02d}", "year": year, "province": "辽宁",
           "exam_type": "中考", "paper_type": paper["paper_type"], "question_type": _qtype(n),
           "question_number": n, "source": paper["source"], "provenance": "B", "answer": None}
    if n in mcq and mcq[n]["options"]:                    # 题面驱动(2025): 有 stem+options
        rec["raw_question"], rec["options"] = mcq[n]["stem"], mcq[n]["options"]
    elif paper.get("stem_walled"):                        # 答案key驱动(2024): 题干源门控
        rec["stem_status"] = "walled(各免费源门控,仅官方答案可得)"
    if n in kmap:
        rec["kaodian"] = kmap[n]                          # 逐空语法考点
    if akey and str(n) in akey:                           # 官方答案 key (2024 全45题)
        rec["answer"] = akey[str(n)]
    elif n in kmap:                                       # 2025: 语篇填空答案=考点label英文部分(hint可得)
        em = re.match(r"^([a-zA-Z][a-zA-Z ]*)", kmap[n])
        rec["answer"] = em.group(1).strip() if em else None
    elif paper.get("has_answers"):
        rec["answer"] = "见答案源"
    return rec


def _load_mcq(d: Path) -> dict[int, dict]:
    """题面驱动: 读 exam_ocr.txt 题干 (2025); 无 OCR 则空 (2024 答案key驱动)."""
    ocr = d / "exam_ocr.txt"
    if not ocr.exists():
        return {}
    lines = ocr.read_text(encoding="utf-8").splitlines()
    try:                                                  # 跳过注意事项: '第一部分' 之后才算题
        start = next(i for i, l in enumerate(lines) if "第一部分" in l)
        lines = lines[start:]
    except StopIteration:
        pass
    return _parse_mcq(lines)


def build(year: int) -> dict:
    d = ROOT / "data" / "junior_high" / "exams" / f"{year}_liaoning"
    paper = json.loads((d / "paper_structure.json").read_text(encoding="utf-8"))
    mcq, kmap = _load_mcq(d), _kaodian_map(paper)
    akey = paper.get("answer_key")                        # 答案key驱动: 官方答案 (2024)
    rows = [_record(n, year, paper, mcq, kmap, akey) for n in range(1, 46)]
    with (d / "exam_questions.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"year": year, "mode": "答案key驱动" if akey else "题面驱动", "questions": len(rows),
            "有options(MCQ)": sum(1 for r in rows if r.get("options")),
            "有答案": sum(1 for r in rows if r.get("answer")),
            "语篇填空带考点": sum(1 for r in rows if r.get("kaodian"))}


if __name__ == "__main__":
    import sys
    for y in (sys.argv[1:] or ["2025"]):
        print(json.dumps(build(int(y)), ensure_ascii=False))
