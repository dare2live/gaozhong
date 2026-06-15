# Week64 Review Round1 - EOL Draft Span Coverage Closure

Date: 2026-06-12
Scope: Improve EOL structured draft extraction so every draft row has a source span preview.

## Verdict

PARTIAL PROGRESS. Source span coverage is now closed for the review-only drafts.

No DB import was performed.

## Change

Updated `scripts/tools/audit/structure_eol_exam_docx.py` to centralize marker matching for EOL docx text patterns, including:

- full-width and ASCII underscore blanks such as `_＿56_＿` and `＿ 60＿`
- grammar-fill numbers followed by Chinese parentheses such as `56 （fall）`
- seven-choose-five blank numbers without dots such as `36 When`
- ordinary dotted question numbers

## Outputs Rebuilt

- 2021 draft: `data/external/exam_sources/eol/2021_xgkii_english_eol_structured_draft.jsonl`
- 2021 audit: `data/reports/eol_structured_draft_audit_2021.json`
- 2022 draft: `data/external/exam_sources/eol/2022_xgkii_english_eol_structured_draft.jsonl`
- 2022 audit: `data/reports/eol_structured_draft_audit_2022.json`
- Build log: `logs/eol-structured-draft-week64-20260612-092257.log`

## Audit Summary

2021:
- Rows: 67
- Keyed rows: 47
- Missing stem preview: 0
- `参考答案` marker in `stem_preview`: 0
- Import ready: false

2022:
- Rows: 46
- Keyed rows: 42
- Missing stem preview: 0
- `参考答案` marker in `stem_preview`: 0
- Import ready: false

## Remaining Blockers Before Import

- 2021 listening rows remain `draft_not_import_ready_unkeyed_listening` because this converter does not yet attach listening answers/transcripts.
- 2022 remains `draft_not_import_ready_written_paper_only`; no listening 1-20 source has been observed.
- Item-level review still needs to confirm question type boundaries, answer mapping, and source span quality before import.

## Validation

- `python3 -m py_compile scripts/tools/audit/structure_eol_exam_docx.py scripts/tools/audit/truth_baseline_audit.py`: PASS
- `python3 scripts/tools/audit/truth_baseline_audit.py --strict`: exit 1 as expected; M0 remains open. Log: `logs/truth-baseline-week64-20260612-092349.log`
- `python3 scripts/data_accuracy_check.py`: PASS. Log: `logs/data-accuracy-week64-20260612-092349.log`
- `codegraph sync`: exit 0. Log: `logs/codegraph-sync-week64-20260612-092349.log`
- `codegraph affected scripts/tools/audit/structure_eol_exam_docx.py`: exit 0, no affected test files. Log: `logs/codegraph-affected-week64-20260612-092349.log`
- `moth doctor --repo . --format markdown`: exit 0, no issues, Complexity PASS/new findings 0, WARN remains dirty worktree + CodeGraph stale. Log: `logs/moth-doctor-week64-20260612-092349.md`
