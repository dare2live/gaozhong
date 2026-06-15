# Week63 Review Round1 - EOL Structured Draft Gate

Date: 2026-06-12
Scope: Convert acquired EOL raw docx text into review-only structured drafts for Phase A/M0.

## Verdict

PARTIAL PROGRESS. Drafts were generated, but they are explicitly not import-ready.

No DB import was performed.

## New Tool

- `scripts/tools/audit/structure_eol_exam_docx.py`

Purpose:
- Read extracted EOL docx text.
- Preserve observed paper number and reference-answer number separately.
- Emit review-only JSONL drafts and audit JSON.
- Prevent direct import when numbering or source-span coverage remains ambiguous.

## Outputs

- 2021 draft: `data/external/exam_sources/eol/2021_xgkii_english_eol_structured_draft.jsonl`
- 2021 audit: `data/reports/eol_structured_draft_audit_2021.json`
- 2022 draft: `data/external/exam_sources/eol/2022_xgkii_english_eol_structured_draft.jsonl`
- 2022 audit: `data/reports/eol_structured_draft_audit_2022.json`
- Build log: `logs/eol-structured-draft-rebuild-20260612-091957.log`

## Audit Summary

2021:
- Rows: 67
- Keyed rows: 47
- Missing stem preview: 6
- Review statuses:
  - `draft_not_import_ready_unkeyed_listening`: 20
  - `draft_not_import_ready_number_shift_minus_20`: 45
  - `draft_not_import_ready_writing_sample_answer`: 2

2022:
- Rows: 46
- Keyed rows: 42
- Missing stem preview: 14
- Review statuses:
  - `draft_not_import_ready_written_paper_only`: 45
  - `draft_not_import_ready_no_sample_answer_in_source`: 1

Contamination check:
- `参考答案` marker in `stem_preview`: 0 rows for both draft files after converter correction.

## Interpretation

- 2021 has enough raw source to start item-level review, but listening answers remain unkeyed in this EOL source and six grammar-fill spans need extraction improvement.
- 2022 remains written-paper-only from this EOL source and still lacks listening 1-20 plus fourteen source-span previews.
- These drafts are useful for review and parser hardening, but must not be imported into `exam_questions` until `import_ready=true` is earned by audit.

## Validation

- `python3 -m py_compile scripts/tools/audit/structure_eol_exam_docx.py scripts/tools/audit/truth_baseline_audit.py`: PASS
- `python3 scripts/tools/audit/truth_baseline_audit.py --strict`: exit 1 as expected; M0 remains open. Log: `logs/truth-baseline-week63-20260612-092045.log`
- `python3 scripts/data_accuracy_check.py`: PASS. Log: `logs/data-accuracy-week63-20260612-092045.log`
- `codegraph sync`: exit 0. Log: `logs/codegraph-sync-week63-20260612-092045.log`
- `codegraph affected scripts/tools/audit/structure_eol_exam_docx.py`: exit 0, no affected test files. Log: `logs/codegraph-affected-week63-20260612-092045.log`
- `moth doctor --repo . --format markdown`: exit 0, no issues, Complexity PASS/new findings 0, WARN remains dirty worktree + CodeGraph stale. Log: `logs/moth-doctor-week63-20260612-092045.md`
