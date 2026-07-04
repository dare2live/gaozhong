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
    """一行可能含多个选项 (A.x B.y) 或单个; 拆进 rec['options'].
    marker-based: 找各 'X.' 标记取到下一标记/行尾 — 修选项文本以 A-E 大写开头(Discovery/Braver)被吞 (强验证 Z1)。"""
    markers = list(re.finditer(r"(?:^|\s)([A-E])[\.．]\s*", text))
    for i, mo in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        rec["options"][mo.group(1)] = text[mo.end():end].strip()


_BANK_RE = re.compile(r"^([A-E])[\.．]\s*(.+\.)\s*$")   # 五选四句库行: "A. 完整句子."


def _parse_mcq(lines: list[str]) -> dict[int, dict]:
    """'N. stem'(阅读) 或 'N. A.opt'(完形无题干) + 后续 A-E 选项行 → {qnum:{stem,options}}."""
    out: dict[int, dict] = {}
    cur = None
    for raw in lines:
        ln = raw.strip()
        if "第二节" in ln and "方框" in ln:   # 五选四段: cur=None 防句库选项污染 Q16 (强验证 Z1)
            cur = None
            continue
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


def _bank_from_segment(seg: list[str]) -> dict[str, str]:
    """段内 5 个完整句 'X. ....' → 共享句库 (非短选项/passage碎句)."""
    bank: dict[str, str] = {}
    for l in seg:
        m = _BANK_RE.match(l.strip())
        if m and len(m.group(2)) > 8:
            bank[m.group(1)] = m.group(2).strip()
    return bank


def _parse_wuxuansi(lines: list[str]) -> dict[int, dict]:
    """五选四/选句填空(17-20): 共享 A-E 句库 → 每空同 options (强验证 Z1余, 题#19).
    段在'第二节...方框'后到'完形/二、'前。"""
    try:
        start = next(i for i, l in enumerate(lines) if "第二节" in l and "方框" in l)
    except StopIteration:
        return {}
    end = next((i for i in range(start, len(lines))
                if "完形填空" in lines[i] or lines[i].strip().startswith("二、")), len(lines))
    bank = _bank_from_segment(lines[start:end])
    if len(bank) < 4:
        return {}
    return {n: {"stem": "选句填空(共享段落,见原卷第二节)", "options": dict(bank)} for n in range(17, 21)}


_YPTK_SKIP = ("阅读短文", "通顺、连贯")  # 段内说明文字行(含跨行续写"...使短文\n通顺、连贯。"), 非原文不进 raw_question


def _find_section_bounds(lines: list[str], is_start, is_end) -> tuple[int, int] | None:
    """定位段边界(start行索引+1 到 end行索引, 不含起止标记行本身); 找不到start返回None.
    共用于完形填空(21-30)/语篇填空(31-40)两段的段落抽取(Rule5可复用, 同结构不同marker)。"""
    try:
        start = next(i for i, l in enumerate(lines) if is_start(l))
    except StopIteration:
        return None
    end = next((i for i in range(start, len(lines)) if is_end(lines[i])), len(lines))
    return start, end


def _passage_from_bounds(lines: list[str], bounds: tuple[int, int] | None) -> str:
    """段边界内的行拼成一段(去说明性文字_YPTK_SKIP, 去空行); 无边界/无内容返回空串."""
    if not bounds:
        return ""
    start, end = bounds
    return "\n".join(
        l.strip() for l in lines[start + 1:end]
        if l.strip() and not any(s in l for s in _YPTK_SKIP))


def _parse_wanxing(lines: list[str], mcq: dict) -> None:
    """完形填空(21-30, 同根因顺带补: 与31-40语篇填空同结构——连续短文+隐式空号内嵌如'the21',
    旧版从未把共享段落接到stem, 21-30 的 raw_question 恒为空字符串, content_status 视图误标
    'stem_walled', 实际A-D选项本身已被_parse_mcq正确抓取, 只缺passage上下文).
    只原地补 stem 字段(mcq[n]['stem']), 不碰已有 options(避免用 dict.update() 整体替换
    冲掉_parse_mcq已抓到的真实A-D选项)。段在'二、'后到首个题号'21.'行前。"""
    bounds = _find_section_bounds(
        lines, lambda l: l.strip().startswith("二、"),
        lambda l: bool(re.match(r"^21[.．]", l.strip())))
    passage = _passage_from_bounds(lines, bounds)
    if not passage:
        return
    for n in range(21, 31):
        if n in mcq:
            mcq[n]["stem"] = passage


def _parse_yupian_tiankong(lines: list[str]) -> dict[int, dict]:
    """语篇填空(31-40, 坑2026-07-04全数据审计补: 旧版完全无此段解析, mcq[31..40]恒 None,
    被 _set_stem 静默留空后被 content_status 误标"题面门控", 实为解析器缺口非源头不可得).
    整段连续短文(非独立选项, 空号内嵌在词间如 'full31new'), 10个空共享同一篇 raw_question
    (仿17-20五选四共享句库模式); 具体每空语法考点另由 paper_structure.json (_kaodian_map) 提供。
    段在'三、语篇填空'标题后到'四、阅读与表达'前。"""
    bounds = _find_section_bounds(
        lines, lambda l: "语篇填空" in l and l.strip().startswith("三"),
        lambda l: l.strip().startswith("四、") or "阅读与表达" in l)
    passage = _passage_from_bounds(lines, bounds)
    if not passage:
        return {}
    return {n: {"stem": passage, "options": {}} for n in range(31, 41)}


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


def _set_stem(rec: dict, n: int, mcq: dict, paper: dict) -> None:
    """题面(2025): stem+options (四选一仅A-D, 挡五选四bank渗入 强验证Z1); 门控(2024): 标 walled.

    坑(2026-07-04 全数据审计): 旧条件要求 options 非空才写入, 41-45(阅读与表达开放问答/
    书面表达作文题, 本无选项)虽被 _parse_mcq 正确解析出 stem 却因 options={} 判 falsy
    被整个跳过, 且 2025 非 stem_walled 年份故 elif 分支也不触发, 静默留 raw_question=None
    (无任何 stem_status 标记, 比误标 walled 更差); 下游 zhongkao_questions 视图的
    content_status CASE(raw_question IS NULL → 'stem_walled') 把它冒充成"题面门控",
    实为解析器条件写反, 非源头不可得。改判据: stem 或 options 任一非空即写入(完形填空
    21-30 反过来是 stem='' 但 options 非空, 只判 stem 会漏掉这类——两个字段各自可能为空,
    只要有一个有内容就该落库, 不能要求两个同时非空/同时判其中一个)。"""
    if n in mcq and (mcq[n].get("stem") or mcq[n]["options"]):
        opts = mcq[n]["options"]
        if 1 <= n <= 16:
            opts = {k: v for k, v in opts.items() if k in "ABCD"}
        rec["raw_question"], rec["options"] = mcq[n]["stem"], opts
    elif paper.get("stem_walled"):
        rec["stem_status"] = "walled(各免费源门控,仅官方答案可得)"
    else:
        rec["stem_status"] = "unparsed(exam_ocr.txt 未能解析出该题stem, 非源头不可得, 需修解析器)"


def _set_answer(rec: dict, n: int, kmap: dict, akey: dict | None, paper: dict) -> None:
    """答案: 官方key(2024全45) > 语篇填空考点label英文部分(2025 hint可得) > has_answers占位."""
    if akey and str(n) in akey:
        rec["answer"] = akey[str(n)]
    elif n in kmap:
        em = re.match(r"^([a-zA-Z][a-zA-Z ]*)", kmap[n])
        rec["answer"] = em.group(1).strip() if em else None
    elif paper.get("has_answers"):
        rec["answer"] = "见答案源"


def _record(n: int, year: int, paper: dict, mcq: dict, kmap: dict, akey: dict | None) -> dict:
    rec = {"question_id": f"ZK-LN-{year}-{n:02d}", "year": year, "province": "辽宁",
           "exam_type": "中考", "paper_type": paper["paper_type"], "question_type": _qtype(n),
           "question_number": n, "source": paper["source"], "provenance": "B", "answer": None}
    _set_stem(rec, n, mcq, paper)
    if n in kmap:
        rec["kaodian"] = kmap[n]                          # 逐空语法考点
    _set_answer(rec, n, kmap, akey, paper)
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
    mcq = _parse_mcq(lines)
    mcq.update(_parse_wuxuansi(lines))          # 五选四(17-20)共享句库
    mcq.update(_parse_yupian_tiankong(lines))   # 语篇填空(31-40)共享段落 (2026-07-04坑补)
    _parse_wanxing(lines, mcq)                  # 完形填空(21-30)原地补stem, 不碰已有options (同坑同修)
    return mcq


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
