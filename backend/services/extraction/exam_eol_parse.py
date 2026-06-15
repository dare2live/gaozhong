"""EOL exam-source text parsing helpers.

Pure text/regex parsing extracted from exam_eol.py to keep that module under the
god-module line budget (Rule 8). No DuckDB, no IO side effects beyond reading the
import policy for the draft field spec. exam_eol re-exports these symbols so the
public service API stays stable.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.services.contracts import load_import_policy

EOL_BUSINESS_DRAFT_FIELDS = (
    "id",
    "year",
    "province",
    "paper_type",
    "question_type",
    "observed_question_number",
    "reference_answer_number",
    "answer",
    "stem_preview",
    "source_file",
    "review_status",
)


def required_draft_fields(policy_name: str = "exam_truth_source_import") -> tuple[str, ...]:
    policy = load_import_policy(policy_name)
    source_fields = tuple(policy.get("require_source_fields") or ())
    return tuple(dict.fromkeys(EOL_BUSINESS_DRAFT_FIELDS + source_fields))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compact(text: str, limit: int = 900) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit]


def section_between(text: str, start: str, end: str | None) -> str:
    s = text.find(start)
    if s < 0:
        return ""
    e = text.find(end, s) if end else -1
    return text[s:e if e >= 0 else len(text)]


def parse_compact_answer_tables(tail: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    for match in re.finditer(r"题号([0-9]{4,})答案([A-G]+)", tail):
        nums_blob, ans_blob = match.groups()
        nums = [int(nums_blob[i:i + 2]) for i in range(0, len(nums_blob), 2)]
        if len(nums) != len(ans_blob):
            continue
        for num, ans in zip(nums, ans_blob):
            answers[num] = ans
    return answers


def parse_explicit_answers(tail: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    matches = list(re.finditer(r"(?<!\d)(\d{1,2})\.\s*", tail))
    for idx, match in enumerate(matches):
        num = int(match.group(1))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tail)
        value = compact(tail[start:end], 500)
        value = re.split(r"第一部分|第二部分|第三部分|第四部分|扫码关注|20\d{2}年普通高等学校", value)[0].strip()
        if value:
            answers[num] = value
    return answers


def reference_answers(text: str) -> dict[int, str]:
    idx = text.find("参考答案")
    if idx < 0:
        return {}
    tail = text[idx:]
    answers = parse_compact_answer_tables(tail)
    answers.update(parse_explicit_answers(tail))
    return answers


def marker_patterns(number: int, marker_style: str) -> list[str]:
    escaped = re.escape(str(number))
    if marker_style == "dotted":
        return [rf"(?<!\d){escaped}\s*[.．]\s*(?=[A-Z\"“])"]
    if marker_style == "undotted":
        return [
            rf"[＿_]+\s*{escaped}\s*[.．]?\s*[＿_]+",
            rf"[＿_]+\s*{escaped}\s*[＿_]?",
            rf"(?<![\d.]){escaped}\s+(?=[A-Z\"“])",
        ]
    if marker_style == "cloze":
        return [
            rf"[＿_]+\s*{escaped}\s*[.．]?\s*[＿_]+",
            rf"[＿_]+\s*{escaped}\s*[＿_]?",
            rf"(?<!\d){escaped}\s*[.．]\s*(?=[A-Z])",
            rf"(?<=\s){escaped}\s+(?=[a-zA-Z\"“])",
        ]
    if marker_style == "blank":
        return [
            rf"[＿_]+\s*{escaped}\s*[.．]?\s*[＿_]+",
            rf"[＿_]+\s*{escaped}\s*[＿_]?",
            rf"(?<!\d){escaped}\s*(?=[（(])",
            rf"(?<=\s){escaped}\s+(?=[a-zA-Z\"“])",
        ]
    raise ValueError(f"unknown marker_style: {marker_style}")


def find_marker(section: str, number: int, marker_style: str, offset: int = 0) -> int:
    best = -1
    text = section[offset:]
    for pat in marker_patterns(number, marker_style):
        match = re.search(pat, text)
        if not match:
            continue
        pos = offset + match.start()
        if best < 0 or pos < best:
            best = pos
    return best


def snippet_for_number(section: str, number: int, next_numbers: list[int], marker_style: str) -> str:
    start = find_marker(section, number, marker_style)
    if start < 0:
        return ""
    end = len(section)
    for nxt in next_numbers:
        if nxt <= number:
            continue
        next_pos = find_marker(section, nxt, marker_style, start + 1)
        if next_pos >= 0:
            end = next_pos
            break
    return compact(section[start:end])
