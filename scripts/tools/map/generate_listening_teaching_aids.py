"""Generate listening_transcript_teaching.jsonl from question_bank (2021–2025).

每条讲解可对 stem/answer/transcript 核验:
  - distractor.cue_in_transcript 非空 ⇒ 必须是 transcript 子串
  - answer / 选项字母与库一致
不写跨卷臆测; 技巧为题型模板 + 本题核验事实。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.services.listening.teaching_aid import JSONL  # noqa: E402

TOKEN = re.compile(r"[A-Za-z']+")
DB = ROOT / "data" / "db" / "gaozhong.duckdb"

SKILL_TECHNIQUE = {
    "原因/目的": ["预读 Why/purpose 选项", "听最终意图句, 旁支活动常是诱饵"],
    "时间/频次": ["先标出选项里的时间量", "听比较关系(every/once/other), 不听单个数字"],
    "地点": ["听地点转移词(go/to/at/in)", "场景词出现≠最终所在地"],
    "数字/价格": ["记下运算线索(half/each/last time)", "邻近数字几乎必有干扰"],
    "人物/身份/关系": ["听共事/称呼/生活细节", "别被同场其他人名带走"],
    "主旨/话题": ["听开场+重复主题词", "细节活动选项常是诱饵"],
    "推断/建议": ["听 probably/suggest 对应的决定句", "已做之事≠将做之事"],
    "事实细节/行为": ["盯题干动词时态(did/will/doing)", "同语义场行为替换是高频干扰"],
    "事实细节/其他what": ["题干问什么就只取什么", "同段其他 what 信息当诱饵"],
    "方式": ["听 how / by / feel 锚点句", "态度与事实分开"],
    "其他": ["先定位题干疑问词", "排除原文提过但未回答题干的选项"],
}


def _year_q(origin_ref: str) -> tuple[int | None, int | None]:
    m = re.search(r"(20\d{2}).*?(\d+)$", origin_ref or "")
    if not m:
        m = re.search(r"listening/(20\d{2})/xgkii/(\d+)$", origin_ref or "")
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _section(q: int | None) -> str:
    if q is None:
        return "unknown"
    return "short" if q <= 5 else "long"


def _first_question_block(stem: str) -> str:
    s = stem or ""
    s = re.split(r"听第|第二节|第一节", s, maxsplit=1)[0]
    return s.strip()


def parse_options(stem: str) -> dict[str, str]:
    s = _first_question_block(stem)
    opts: dict[str, str] = {}
    for m in re.finditer(r"\b([A-C])\.\s*(.+?)(?=\s*[A-C]\.|$)", s, re.S):
        opts[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip(" .")
    return opts


def classify_skill(stem: str) -> str:
    first = _first_question_block(stem).lower()
    if re.search(r"\bwhy\b|reason|purpose", first):
        return "原因/目的"
    if re.search(r"\bwhen\b|what time|how long|how often|how soon", first):
        return "时间/频次"
    if re.search(r"\bwhere\b", first):
        return "地点"
    if re.search(r"\bhow much|how many|price|cost", first):
        return "数字/价格"
    if re.search(r"\bwho\b|whom|whose|relationship|probable relationship", first):
        return "人物/身份/关系"
    if re.search(r"probably .{0,40}(man|woman|speaker)|what is probably the", first):
        return "人物/身份/关系"
    if re.search(r"suggest|advice|recommend|imply|infer|probably|most likely", first):
        return "推断/建议"
    if re.search(r"talking about|mainly|main topic|subject", first):
        return "主旨/话题"
    if re.search(r"\bhow\b", first):
        return "方式"
    if re.search(r"\bwhat .{0,40}(do|doing|did|will|going to|happen)", first):
        return "事实细节/行为"
    if re.search(r"\bwhat\b", first):
        return "事实细节/其他what"
    return "其他"


def _tokens(text: str, min_len: int = 4) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text or "") if len(t) >= min_len]


def _sentences(tr: str) -> list[str]:
    parts = re.split(r"(?<=[.?!？！])\s+|\n+", tr or "")
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p and p.strip()]


def _find_span(tr: str, needles: list[str]) -> str | None:
    tr_l = (tr or "").lower()
    for sent in _sentences(tr):
        sl = sent.lower()
        if any(n in sl for n in needles if n):
            return sent[:220]
    # fallback: window around first needle
    for n in needles:
        if not n:
            continue
        i = tr_l.find(n)
        if i >= 0:
            a = max(0, i - 40)
            b = min(len(tr), i + len(n) + 80)
            return re.sub(r"\s+", " ", (tr or "")[a:b]).strip()
    return None


def _trap_for_wrong(opt_text: str, tr: str) -> tuple[str, str | None, str]:
    """Return (trap_label, cue_span_or_None, why)."""
    toks = _tokens(opt_text)
    tr_l = (tr or "").lower()
    hits = [t for t in toks if t in tr_l]
    if re.search(r"\d|\$|£|once|twice|every|year|month|week|minute|hour|am|pm", opt_text, re.I):
        cue = _find_span(tr, hits) if hits else None
        return (
            "数字/时间邻近干扰",
            cue,
            "选项含时间/数量; 原文常出现邻近量, 需听比较关系而非单个数字。",
        )
    if re.search(
        r"teacher|student|doctor|neighbor|colleague|husband|wife|friend|"
        r"journalist|athlete|manager|worker",
        opt_text,
        re.I,
    ):
        cue = _find_span(tr, hits) if hits else None
        return (
            "身份/关系干扰",
            cue,
            "身份类选项靠共事/称呼/生活细节推断; 同场其他人名常是诱饵。",
        )
    if hits:
        cue = _find_span(tr, hits)
        return (
            "原文提及但非答案",
            cue,
            f"原文出现过 {', '.join(hits[:3])} 等词, 但并未回答本题题干。",
        )
    return (
        "语义场替换/概括干扰",
        None,
        "选项与原文用词不同, 属同场景改写或概括; 听最终意图, 勿凭主题词猜测。",
    )


def _answer_support(answer_text: str, tr: str) -> dict:
    # min_len=3 才能抓住 see/go/job 等短动词的改写信号
    toks = _tokens(answer_text, min_len=3)
    tr_l = (tr or "").lower()
    hits = [t for t in toks if t in tr_l]
    missing = [t for t in toks if t not in tr_l]
    span = _find_span(tr, hits or toks) or (_sentences(tr)[-1][:220] if _sentences(tr) else "")
    # 任一 substantive 选项词未原样出现 → 按改写教 (即使 friend 等同现)
    if missing or not toks:
        note = "正确选项与原文为改写对应"
        if missing:
            note += f"（选项侧 {', '.join(missing[:3])} 未原样出现）"
        if hits:
            note += f"；可借原文锚词 {', '.join(hits[:3])} 定位关键句"
        note += "。"
        return {"kind": "paraphrase", "transcript_span": span, "note": note}
    if hits and len(hits) >= max(1, len(toks) // 2):
        return {
            "kind": "literal",
            "transcript_span": span,
            "note": "正确选项关键词在原文中可直接定位。",
        }
    note = "正确选项与原文为改写对应。"
    return {"kind": "paraphrase", "transcript_span": span, "note": note}


def _easy_to_miss(skill: str, support: dict, distractors: list[dict], section: str) -> list[str]:
    out: list[str] = []
    if support.get("kind") == "paraphrase":
        out.append("答案是改写, 不要在原文里死等选项原词。")
    span = (support.get("transcript_span") or "").strip()
    if span:
        out.append(f"关键句: {span}")
    bait = [d for d in distractors if d.get("trap") == "原文提及但非答案"]
    if bait:
        out.append("易忽略: 原文提过的旁支信息常被做成干扰项。")
    if section == "long":
        out.append("长材料多题共用: 先看本题疑问词, 再回听对应锚点, 勿用整段大意蒙题。")
    if skill in ("时间/频次", "数字/价格"):
        out.append("数字题易忽略比较词(every other / half / last time)。")
    # unique preserve order
    seen: set[str] = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq[:4]


def _how_to(skill: str, answer: str, answer_text: str, distractors: list[dict], support: dict) -> str:
    bait_bits = []
    for d in distractors:
        if d.get("trap") == "原文提及但非答案" and d.get("cue_in_transcript"):
            bait_bits.append(f"{d['option']} 提到的内容在原文出现过但答非所问")
    parts = [
        f"本题考查「{skill}」。正确答案 {answer}. {answer_text}。",
        support.get("note") or "",
    ]
    if bait_bits:
        parts.append("排干扰: " + "; ".join(bait_bits[:2]) + "。")
    else:
        parts.append("排干扰: 先删与题干疑问词不对齐的选项, 再在剩余项里听最终意图。")
    if support.get("kind") == "paraphrase":
        parts.append("技巧: 预读选项语义场 → 听时对上同义场景, 而不是搜原词。")
    return " ".join(p for p in parts if p).strip()


def _build_distractors(opts: dict[str, str], ans: str, transcript: str) -> list[dict]:
    out = []
    for letter in "ABC":
        if letter == ans or letter not in opts:
            continue
        trap, cue, why = _trap_for_wrong(opts[letter], transcript)
        out.append({
            "option": letter, "text": opts[letter], "trap": trap,
            "cue_in_transcript": cue, "why_wrong": why,
        })
    return out


def _bottlenecks(support: dict, distractors: list[dict], skill: str, section: str) -> list[str]:
    bots = []
    if support.get("kind") == "paraphrase":
        bots.append("改写定位")
    if any(d.get("trap") == "原文提及但非答案" for d in distractors):
        bots.append("细节诱饵")
    if skill in ("时间/频次", "数字/价格"):
        bots.append("数字精听")
    bots.append("长材料信息过载" if section == "long" else "短对话瞬时抓取")
    return bots or ["语义对齐"]


def _cue_in_transcript(cue: str | None, tr: str) -> str | None:
    if not cue:
        return None
    if cue in tr or cue.lower() in tr.lower():
        return cue
    if re.sub(r"\s+", "", cue.lower()) in re.sub(r"\s+", "", tr.lower()):
        return cue
    return None


def build_row(origin_ref: str, stem: str, answer: str, transcript: str) -> dict | None:
    year, q = _year_q(origin_ref)
    if year is None or q is None or not (2021 <= year <= 2025):
        return None
    opts = parse_options(stem)
    ans = (answer or "").strip().upper()[:1]
    if ans not in opts or len(opts) < 2:
        return None
    skill = classify_skill(stem)
    section = _section(q)
    support = _answer_support(opts[ans], transcript)
    distractors = _build_distractors(opts, ans, transcript)
    for d in distractors:
        d["cue_in_transcript"] = _cue_in_transcript(d.get("cue_in_transcript"), transcript)
    return {
        "origin_ref": origin_ref, "year": year, "q": q, "section": section, "skill": skill,
        "bottleneck": _bottlenecks(support, distractors, skill, section),
        "answer": ans, "answer_text": opts[ans], "answer_support": support,
        "distractors": distractors,
        "easy_to_miss": _easy_to_miss(skill, support, distractors, section),
        "technique": SKILL_TECHNIQUE.get(skill, SKILL_TECHNIQUE["其他"]),
        "how_to": _how_to(skill, ans, opts[ans], distractors, support),
        "provenance": "agent_transcript_grounded",
        "review_status": "auto_verified_against_transcript",
    }


def fetch_rows(con: duckdb.DuckDBPyConnection) -> list[tuple]:
    return con.execute(
        "SELECT origin_ref, stem, answer, transcript "
        "FROM question_bank "
        "WHERE has_audio = true AND question_type = '听力' "
        "AND origin_ref IS NOT NULL "
        "AND origin_ref NOT LIKE '%2026%' "
        "ORDER BY origin_ref"
    ).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=JSONL)
    args = ap.parse_args()
    con = duckdb.connect(str(DB), read_only=True)
    try:
        rows = fetch_rows(con)
    finally:
        con.close()
    out_rows = []
    skip = Counter()
    for origin_ref, stem, answer, transcript in rows:
        if not transcript or len(transcript) < 40:
            skip["no_transcript"] += 1
            continue
        row = build_row(origin_ref, stem, answer, transcript)
        if not row:
            skip["parse_fail"] += 1
            continue
        out_rows.append(row)
    out_rows.sort(key=lambda r: (r["year"], r["q"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    skills = Counter(r["skill"] for r in out_rows)
    print(f"wrote {len(out_rows)} → {args.out}")
    print("skills", dict(skills))
    print("skip", dict(skip))
    return 0 if len(out_rows) >= 90 else 1


if __name__ == "__main__":
    raise SystemExit(main())
