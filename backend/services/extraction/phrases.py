"""教材短语 / 句型 / 功能表达 — 规则版 (E).

不调 LLM, 用预定义模式扫 section_text:
  PHRASES — 动词短语词典 (高频高考短语), e.g. "take ... into account"
  PATTERNS — 句型 regex, e.g. "It is .* that .*"
  FUNCTIONS — 功能表达 (邀请/拒绝/建议), 短句模板
"""
from __future__ import annotations

import re

import duckdb

# 高频动词短语 (示例 ~150, 高考英语词汇手册常见)
VERB_PHRASES = [
    "take into account", "take into consideration", "take part in", "take advantage of",
    "take care of", "take place", "take over", "take off", "take up",
    "look forward to", "look up", "look after", "look into", "look down upon",
    "make up", "make up of", "make use of", "make sense of", "make a difference",
    "give up", "give in", "give away", "give out", "give rise to",
    "get along with", "get over", "get rid of", "get used to", "get through",
    "put up with", "put off", "put forward", "put into practice",
    "set up", "set off", "set out", "set aside",
    "carry out", "carry on", "carry away",
    "break down", "break out", "break up", "break through",
    "bring about", "bring up", "bring in", "bring forward",
    "come up with", "come across", "come into being", "come true",
    "turn out", "turn down", "turn up", "turn into",
    "deal with", "depend on", "result in", "result from",
    "consist of", "be made up of", "play a role in", "play a part in",
    "be aware of", "be capable of", "be familiar with",
    "in addition to", "in terms of", "in spite of", "in case of",
    "as a result of", "as long as", "as far as", "as soon as",
    "due to", "thanks to", "according to", "regardless of",
    "on behalf of", "on account of", "on the contrary", "on the whole",
    "by means of", "by no means", "for the sake of",
    "instead of", "rather than",
    "be supposed to", "be likely to", "be willing to", "be devoted to",
    "have access to", "have something in common", "have an impact on",
    "pay attention to", "lose sight of", "in favor of",
    "concentrate on", "focus on", "insist on", "rely on",
    "agree with", "agree to", "object to", "look up to",
    "live up to", "stand for", "stand by", "stand out",
    "go through", "go against", "go on", "go in for",
    "hold on", "hold up", "hold back",
]

# 句型 (sentence pattern)
# 句型 regex (A1 修, 坑16/坑5 同型): 原版 .* + DOTALL 跨段贪婪 → 73% evidence 重配不上自己正则 +
# such as/so that/形式主语 误命中(32% phrases 污染, 进 lesson_plan 老师可见)。修: (1) 不用 DOTALL(. 不跨行,
# 限同句); (2) 量词限长 .{0,40}? 避跨段; (3) 负向断言排 such as / so that(目的状语) / It is ADJ to V(形式主语);
# (4) "强调句"标签据实改"It is…that 句型"(regex 分不清 cleft 强调 vs 形式主语/报道句, 不假称全强调)。
# evidence 存匹配 span 自身 → 保证可重配(D0 门锁: 每行 evidence 必过其 canonical 正则)。
PATTERNS = [
    (r"\bIt (?:is|was) (?!\w+ to )[\w',\- ]{2,40}? that\b", "It is…that 句型"),
    (r"\bNot only\b.{1,50}?\bbut also\b", "倒装/并列"),
    (r"\bThe more\b.{1,40}?\bthe more\b", "the more...the more"),
    (r"\bSo (?!that\b)\w+.{0,40}? that\b", "so...that 结果状语"),
    (r"\bSuch (?!\w+ as\b).{1,40}? that\b", "such...that"),
    (r"\bif\b.{1,40}?\bwould\b", "虚拟语气"),
    (r"\bI wish\b.{1,30}?\bwere\b", "虚拟语气 (wish)"),
    (r"\bRather than\b.{1,40}?\bprefer\b", "rather than"),
    (r"\bNo sooner\b.{1,40}?\bthan\b", "no sooner...than"),
    (r"\bHardly\b.{1,40}?\bwhen\b", "hardly...when"),
]
# canonical → 正则 (D0 重配门单一源; lib 导入校验每行 evidence 过其正则)
PATTERN_RE = {label: pat for pat, label in PATTERNS}

# 功能表达
FUNCTIONS = [
    ("I'd like to", "邀请/请求"), ("Would you like", "邀请"),
    ("Why don't we", "建议"), ("How about", "建议"),
    ("I'm afraid", "委婉拒绝/担忧"), ("I'd rather", "偏好"),
    ("Thank you for", "感谢"), ("I'm sorry for", "道歉"),
    ("Could you please", "请求"), ("In my opinion", "观点"),
    ("From my point of view", "观点"), ("As far as I know", "限定观点"),
    ("It seems that", "推测"), ("It appears that", "推测"),
    ("In conclusion", "总结"), ("To sum up", "总结"),
    ("On one hand", "对比"), ("On the other hand", "对比"),
    ("For example", "例证"), ("For instance", "例证"),
    ("Generally speaking", "总论"), ("To begin with", "陈述顺序"),
    ("First of all", "陈述顺序"), ("Last but not least", "陈述顺序"),
]


def _scan_text(text: str) -> list[tuple[str, str, str]]:
    """Return [(canonical, phrase_type, evidence)]."""
    lower = text.lower()
    out: list[tuple[str, str, str]] = []
    # verb phrases (substring)
    for ph in VERB_PHRASES:
        if ph.lower() in lower:
            # find sentence containing it
            idx = lower.find(ph.lower())
            start = max(0, idx - 60)
            end = min(len(text), idx + len(ph) + 60)
            evidence = text[start:end].replace("\n", " ")
            out.append((ph, "verb_phrase", evidence))
    # patterns — 不用 DOTALL(. 不跨行限同句); evidence = 匹配 span 自身(保证 D0 重配门过)
    for pat, label in PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            ev = m.group(0).replace("\n", " ").strip()
            out.append((label, "sentence_pattern", ev[:160]))
    # functions
    for trigger, label in FUNCTIONS:
        if trigger.lower() in lower:
            idx = lower.find(trigger.lower())
            ev = text[max(0, idx-30):idx+len(trigger)+50].replace("\n", " ")
            out.append((trigger, f"function_expression:{label}", ev))
    return out


def extract_phrases(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute("""
        SELECT version_key, volume_key, unit_number, seq, raw_text FROM section_text
    """).fetchall()
    con.execute("DELETE FROM phrases")
    seen: set[tuple[str, str, int, str, str]] = set()
    inserted = 0
    by_type: dict[str, int] = {}
    for ver, vol, un, _seq, text in rows:
        for canonical, ptype, ev in _scan_text(text):
            key = (ver, vol, un, canonical, ptype)
            if key in seen:
                continue
            seen.add(key)
            con.execute(
                "INSERT INTO phrases VALUES (nextval('phrase_id_seq'), ?, ?, ?, ?, ?, ?, ?)",
                [ver, vol, un, canonical, ptype, ev, None],
            )
            inserted += 1
            by_type[ptype.split(":")[0]] = by_type.get(ptype.split(":")[0], 0) + 1
    return {"sections": len(rows), "phrases_inserted": inserted, "by_type": by_type}
