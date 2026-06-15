"""EOL exam-source extraction service boundary.

The current parser still lives in scripts/tools/audit/structure_eol_exam_docx.py.
This module defines the service-level contract that CLI tools should migrate to:
source metadata, default paths, required draft fields, and import-readiness
state ownership. It intentionally does not write DuckDB.

Text parsing helpers live in exam_eol_parse; JSONL IO + field-coverage audit live
in exam_eol_io. Both are re-exported here so the public service API is stable.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.data_sources import SourceSpec, load_registry
from backend.services.extraction.exam_eol_io import (
    audit_draft_field_coverage,
    read_jsonl,
    write_draft_outputs,
)
from backend.services.extraction.exam_eol_parse import (
    EOL_BUSINESS_DRAFT_FIELDS,
    compact,
    find_marker,
    marker_patterns,
    now_iso,
    parse_compact_answer_tables,
    parse_explicit_answers,
    reference_answers,
    required_draft_fields,
    section_between,
    snippet_for_number,
)

__all__ = [
    "EOLExamSource",
    "EOL_BUSINESS_DRAFT_FIELDS",
    "EOL_SOURCE_IDS",
    "REPORT_DIR",
    "ROOT",
    "SOURCE_DIR",
    "add_rows",
    "audit_draft_field_coverage",
    "build_draft",
    "compact",
    "draft_paths",
    "find_marker",
    "get_eol_source",
    "marker_patterns",
    "now_iso",
    "parse_compact_answer_tables",
    "parse_explicit_answers",
    "read_jsonl",
    "reference_answers",
    "required_draft_fields",
    "section_between",
    "snippet_for_number",
    "source_metadata",
    "write_draft_outputs",
]

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


def _build_draft_2021(rows: list[dict[str, Any]], year: int, text: str, answers: dict[int, str], source_file: str) -> None:
    listening = section_between(text, "第一部分 听力", "第二部分 阅读")
    reading = section_between(text, "第二部分 阅读", "第三部分 语言运用")
    language = section_between(text, "第三部分 语言运用", "第四部分 写作")
    writing = section_between(text, "第四部分 写作", "参考答案")

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


def _build_draft_2022(rows: list[dict[str, Any]], year: int, text: str, answers: dict[int, str], source_file: str) -> None:
    reading = section_between(text, "阅读", "第三部分 语言运用")
    language = section_between(text, "第三部分 语言运用", "第四部分 写作")
    writing = section_between(text, "第四部分 写作", "参考答案")
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


def build_draft(year: int, text_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = text_path.read_text(encoding="utf-8")
    answers = reference_answers(text)
    rows: list[dict[str, Any]] = []
    answer_text = section_between(text, "参考答案", None)
    source_file = text_path.name

    if year == 2021:
        _build_draft_2021(rows, year, text, answers, source_file)
    elif year == 2022:
        _build_draft_2022(rows, year, text, answers, source_file)
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
