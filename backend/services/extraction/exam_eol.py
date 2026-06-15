"""EOL exam-source extraction service boundary.

The current parser still lives in scripts/tools/audit/structure_eol_exam_docx.py.
This module defines the service-level contract that CLI tools should migrate to:
source metadata, default paths, required draft fields, and import-readiness
state ownership. It intentionally does not write DuckDB.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.contracts import load_import_policy
from backend.services.data_sources import SourceSpec, load_registry

ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "data" / "external" / "exam_sources" / "eol"
REPORT_DIR = ROOT / "data" / "reports"
EOL_SOURCE_IDS = {
    2021: "eol_xgkii_english_2021",
    2022: "eol_xgkii_english_2022",
}


@dataclass(frozen=True)
class EOLExamSource:
    year: int
    source_id: str
    source_repo: str
    source_sha256: str
    source_url: str
    source_state: str
    text_path: Path
    draft_path: Path
    audit_path: Path


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


def _registry_source(year: int) -> SourceSpec:
    try:
        source_id = EOL_SOURCE_IDS[year]
    except KeyError as exc:
        supported = ", ".join(str(item) for item in sorted(EOL_SOURCE_IDS))
        raise ValueError(f"unsupported EOL exam year {year}; supported={supported}") from exc
    return load_registry().get(source_id)


def get_eol_source(year: int) -> EOLExamSource:
    source = _registry_source(year)
    if not source.attachments:
        raise ValueError(f"EOL source has no attachments: {source.source_id}")
    attachment = source.attachments[0]
    return EOLExamSource(
        year=year,
        source_id=source.source_id,
        source_repo=source.org or source.family,
        source_sha256=attachment.expected_sha256 or "",
        source_url=source.publish_url,
        source_state=source.status,
        text_path=attachment.text_path or SOURCE_DIR / f"{year}_xgkii_english_eol.txt",
        draft_path=SOURCE_DIR / f"{year}_xgkii_english_eol_structured_draft.jsonl",
        audit_path=REPORT_DIR / f"eol_structured_draft_audit_{year}.json",
    )


def source_metadata(year: int) -> dict[str, str]:
    source = get_eol_source(year)
    return {
        "source_id": source.source_id,
        "source_repo": source.source_repo,
        "source_sha256": source.source_sha256,
        "source_url": source.source_url,
        "source_state": source.source_state,
    }


def draft_paths(year: int) -> dict[str, Path]:
    source = get_eol_source(year)
    return {
        "text": source.text_path,
        "draft": source.draft_path,
        "audit": source.audit_path,
    }


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


def add_rows(
    rows: list[dict[str, Any]],
    *,
    year: int,
    question_type: str,
    observed_numbers: range,
    answer_numbers: range | None,
    answers: dict[int, str],
    section: str,
    source_file: str,
    status: str,
    marker_style: str,
) -> None:
    observed_list = list(observed_numbers)
    answer_list = list(answer_numbers) if answer_numbers is not None else [None] * len(observed_list)
    meta = source_metadata(year)
    for observed, answer_number in zip(observed_list, answer_list):
        source_span = snippet_for_number(section, observed, observed_list, marker_style)
        row = {
            "id": f"EOL-XGKII-{year}-{observed:03d}",
            "year": year,
            "province": "辽宁",
            "paper_type": "新高考全国II卷",
            "question_type": question_type,
            "observed_question_number": observed,
            "reference_answer_number": answer_number,
            "answer": answers.get(answer_number) if answer_number is not None else None,
            "stem_preview": source_span,
            "source_span": source_span,
            "source": "China Education Online / EOL",
            "source_file": source_file,
            "review_status": status,
            **meta,
        }
        rows.append(row)


def _writing_row(
    *,
    year: int,
    row_id: str,
    question_type: str,
    answer: str | None,
    stem: str,
    source_file: str,
    review_status: str,
    reference_answer_number: int | None,
) -> dict[str, Any]:
    meta = source_metadata(year)
    source_span = compact(stem, 900)
    return {
        "id": row_id,
        "year": year,
        "province": "辽宁",
        "paper_type": "新高考全国II卷",
        "question_type": question_type,
        "observed_question_number": None,
        "reference_answer_number": reference_answer_number,
        "answer": answer,
        "stem_preview": source_span,
        "source_span": source_span,
        "source": "China Education Online / EOL",
        "source_file": source_file,
        "review_status": review_status,
        **meta,
    }


def build_draft(year: int, text_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = text_path.read_text(encoding="utf-8")
    answers = reference_answers(text)
    rows: list[dict[str, Any]] = []
    answer_section = section_between(text, "参考答案", None)
    source_file = text_path.name

    if year == 2021:
        listening = section_between(text, "第一部分 听力", "第二部分 阅读")
        reading = section_between(text, "第二部分 阅读", "第三部分 语言运用")
        language = section_between(text, "第三部分 语言运用", "第四部分 写作")
        writing = section_between(text, "第四部分 写作", "参考答案")
        answer_text = answer_section

        add_rows(
            rows,
            year=year,
            question_type="listening_raw_unkeyed",
            observed_numbers=range(1, 21),
            answer_numbers=None,
            answers=answers,
            section=listening,
            source_file=source_file,
            status="draft_not_import_ready_unkeyed_listening",
            marker_style="dotted",
        )
        add_rows(
            rows,
            year=year,
            question_type="reading_or_seven_choose_five",
            observed_numbers=range(21, 36),
            answer_numbers=range(1, 16),
            answers=answers,
            section=reading,
            source_file=source_file,
            status="draft_not_import_ready_number_shift_minus_20",
            marker_style="dotted",
        )
        add_rows(
            rows,
            year=year,
            question_type="seven_choose_five",
            observed_numbers=range(36, 41),
            answer_numbers=range(16, 21),
            answers=answers,
            section=reading,
            source_file=source_file,
            status="draft_not_import_ready_number_shift_minus_20",
            marker_style="undotted",
        )
        add_rows(
            rows,
            year=year,
            question_type="cloze_fill_in_blanks",
            observed_numbers=range(41, 56),
            answer_numbers=range(21, 36),
            answers=answers,
            section=language,
            source_file=source_file,
            status="draft_not_import_ready_number_shift_minus_20",
            marker_style="cloze",
        )
        add_rows(
            rows,
            year=year,
            question_type="grammar_fill",
            observed_numbers=range(56, 66),
            answer_numbers=range(36, 46),
            answers=answers,
            section=language,
            source_file=source_file,
            status="draft_not_import_ready_number_shift_minus_20",
            marker_style="blank",
        )
        for answer_number, qtype in [(46, "applied_writing"), (47, "narrative_writing")]:
            rows.append(
                _writing_row(
                    year=year,
                    row_id=f"EOL-XGKII-{year}-{answer_number:03d}",
                    question_type=qtype,
                    answer=answers.get(answer_number),
                    stem=writing,
                    source_file=source_file,
                    review_status="draft_not_import_ready_writing_sample_answer",
                    reference_answer_number=answer_number,
                )
            )
    elif year == 2022:
        reading = section_between(text, "阅读", "第三部分 语言运用")
        language = section_between(text, "第三部分 语言运用", "第四部分 写作")
        writing = section_between(text, "第四部分 写作", "参考答案")
        answer_text = answer_section
        add_rows(
            rows,
            year=year,
            question_type="reading_or_seven_choose_five",
            observed_numbers=range(21, 36),
            answer_numbers=range(21, 36),
            answers=answers,
            section=reading,
            source_file=source_file,
            status="draft_not_import_ready_written_paper_only",
            marker_style="dotted",
        )
        add_rows(
            rows,
            year=year,
            question_type="seven_choose_five",
            observed_numbers=range(36, 41),
            answer_numbers=range(36, 41),
            answers=answers,
            section=reading,
            source_file=source_file,
            status="draft_not_import_ready_written_paper_only",
            marker_style="undotted",
        )
        add_rows(
            rows,
            year=year,
            question_type="cloze_fill_in_blanks",
            observed_numbers=range(41, 56),
            answer_numbers=range(41, 56),
            answers=answers,
            section=language,
            source_file=source_file,
            status="draft_not_import_ready_written_paper_only",
            marker_style="cloze",
        )
        add_rows(
            rows,
            year=year,
            question_type="grammar_fill",
            observed_numbers=range(56, 66),
            answer_numbers=range(56, 66),
            answers=answers,
            section=language,
            source_file=source_file,
            status="draft_not_import_ready_written_paper_only",
            marker_style="blank",
        )
        rows.append(
            _writing_row(
                year=year,
                row_id=f"EOL-XGKII-{year}-WRITING",
                question_type="writing_prompt_unanswered",
                answer=None,
                stem=writing,
                source_file=source_file,
                review_status="draft_not_import_ready_no_sample_answer_in_source",
                reference_answer_number=None,
            )
        )
    else:
        raise ValueError(f"unsupported year: {year}")

    status_counts = Counter(row["review_status"] for row in rows)
    keyed = [row for row in rows if row.get("answer")]
    missing_stem = [row["id"] for row in rows if not row.get("stem_preview")]
    audit = {
        "generated_at": now_iso(),
        "year": year,
        "source_text": str(text_path),
        "row_count": len(rows),
        "keyed_count": len(keyed),
        "missing_stem_count": len(missing_stem),
        "missing_stem_ids": missing_stem[:50],
        "review_status_counts": dict(status_counts),
        "reference_answer_numbers": sorted(answers),
        "import_ready": False,
        "reason": "draft preserves numbering and source spans; item-level review is required before DB import",
    }
    if answer_text and "参考答案" not in answer_text[:20]:
        audit["warnings"] = ["answer_section_marker_unexpected"]
    return rows, audit


def write_draft_outputs(rows: list[dict[str, Any]], audit: dict[str, Any], out_path: Path, audit_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit_draft_field_coverage(
    rows: list[dict[str, Any]],
    *,
    policy_name: str = "exam_truth_source_import",
) -> dict[str, Any]:
    policy = load_import_policy(policy_name)
    required = required_draft_fields(policy_name)
    nullable = set(policy.get("nullable_source_fields") or ())
    missing_by_field: dict[str, int] = {field: 0 for field in required}
    absent_by_field: dict[str, int] = {field: 0 for field in required}
    empty_non_nullable_by_field: dict[str, int] = {field: 0 for field in required}
    missing_by_row: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        missing: list[str] = []
        absent: list[str] = []
        empty_non_nullable: list[str] = []
        for field in required:
            if field not in row:
                absent.append(field)
                missing.append(field)
            elif field not in nullable and (row.get(field) is None or row.get(field) == ""):
                empty_non_nullable.append(field)
                missing.append(field)
        for field in missing:
            missing_by_field[field] += 1
        for field in absent:
            absent_by_field[field] += 1
        for field in empty_non_nullable:
            empty_non_nullable_by_field[field] += 1
        if missing:
            missing_by_row.append({
                "row_id": row.get("id") or f"row:{idx}",
                "missing_fields": missing,
                "absent_fields": absent,
                "empty_non_nullable_fields": empty_non_nullable,
            })

    missing_by_field = {field: count for field, count in missing_by_field.items() if count}
    absent_by_field = {field: count for field, count in absent_by_field.items() if count}
    empty_non_nullable_by_field = {field: count for field, count in empty_non_nullable_by_field.items() if count}
    return {
        "generated_at": now_iso(),
        "tool": "backend.services.extraction.exam_eol.audit_draft_field_coverage",
        "policy_name": policy_name,
        "status": "fail" if missing_by_field else "pass",
        "row_count": len(rows),
        "required_fields": list(required),
        "nullable_fields": sorted(nullable),
        "missing_by_field": missing_by_field,
        "absent_required_by_field": absent_by_field,
        "empty_required_by_field": empty_non_nullable_by_field,
        "missing_row_count": len(missing_by_row),
        "missing_by_row": missing_by_row[:100],
    }
