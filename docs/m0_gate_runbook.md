# M0 gate runbook

Date: 2026-06-12

Purpose: define how to execute the M0 truth-baseline gate sequence without duplicating the gate list.

## Single source of truth

The gate sequence is owned by:

- `backend/config/m0_gates.yaml`

The human/machine-readable rendering command is:

```bash
python3 scripts/tools/audit/m0_gate_plan.py --format markdown
```

To write a machine-readable plan:

```bash
python3 scripts/tools/audit/m0_gate_plan.py --format json --output data/reports/m0_gate_plan.json
```

This runbook intentionally does not copy the full gate table. If the order, command, expected current status, or failure action changes, update `backend/config/m0_gates.yaml`.

## Operating rule

Run gates in configured order. Stop at the first failing gate unless the failure is already documented as the expected current blocker and the controller explicitly chooses the next diagnostic slice.

An earlier failed gate weakens later evidence:

- A broken source contract makes acquisition results untrustworthy.
- A failed source acquisition makes parser/import output untrustworthy.
- A failed draft field audit means import-readiness findings will be noisy.
- A blocked import dry-run means DB writes are not allowed.
- A failed paper contract means row presence does not prove target coverage.
- A failed strict truth baseline means M0 remains open.

## Failure handling

### Source-contract consistency failure

Fix only configuration first:

- `backend/config/sources.yaml`
- `backend/config/exam_paper_contracts.yaml`
- `backend/config/source_states.yaml`
- `backend/config/m0_gates.yaml`

Do not download, parse, import, or patch DB rows around a config contradiction.

### Source acquisition verification failure

Fix source artifacts or source contracts:

- Replace corrupt or tiny files.
- Correct expected sha256 only after confirming the file is the intended source.
- Lower `min_bytes` only with a written explanation in `docs/data_accuracy_audit.md`.
- Candidate or suspicious sources must not become truth sources by accident.

### EOL draft rebuild failure

Fix extraction before any import-readiness check:

- Parser failures belong in `backend/services/extraction/exam_eol.py`.
- CLI argument/file-output failures belong in `scripts/tools/extraction/build_eol_exam_draft.py`.
- Rebuilt drafts are review-only and must keep `import_ready=false` until review and dry-run gates pass.

### EOL draft field audit failure

Fix draft schema/lineage fields before semantic import-readiness checks:

- Required fields come from `backend/services/extraction/exam_eol.py` plus `backend/config/import_policies.yaml`.
- Field coverage passing does not mean the source is import-ready.
- It only proves JSONL rows carry the required contract fields.

### EOL import-readiness failure

Fix structured drafts before import:

- Add source fields required by `backend/config/import_policies.yaml`.
- Remove answer-section contamination.
- Resolve missing source spans.
- Explain numbering shifts.
- Keep listening and written-paper provenance separate if their sources differ.
- Do not write `exam_questions` while dry-run is blocked.

### Paper contract coverage failure

Use the report to choose the next year/source slice.

Do not use any-year row counts as proof of target paper coverage.

### Strict truth-baseline failure

Treat `truth_baseline_audit.py --strict` findings as authoritative M0 repair input.

Do not close Phase A/M0 while this gate fails.

## Current known blockers

- `data/external/gaokao_2023_xgkii_english.pdf` is currently only 427 bytes.
- 2021 EOL listening rows are unkeyed.
- 2022 EOL source appears written-paper-only and lacks observed listening 1-20.
- 2024/2025 legacy PDF import produced passage-level rows, not full item-level rows.

## 2026-06-12 Update / External Source Inventory Gate

`backend/config/m0_gates.yaml` now includes `external_source_inventory` immediately after `source_contract_consistency`. The gate command is:

```bash
python3 scripts/tools/audit/external_source_inventory.py --strict --fail-on-warn
```

This gate is intentionally stricter than file acquisition verification: it fails on WARN so candidate, suspicious, and outside-project absolute-path dependencies cannot silently pass into import work. Current expected status remains FAIL until the 2023 suspicious PDF, 2024/2025 sibling-project PDF dependency, and 2021 listening candidate scope are resolved or explicitly re-scoped.

## 2026-06-12 Update / 2024-2025 PDF Local Mirror

2024/2025 New Curriculum II English PDF artifacts are now mirrored under this project:

```text
data/external/exam_sources/local_pdfs/2024_xgkii_english.pdf
data/external/exam_sources/local_pdfs/2025_xgkii_english.pdf
```

`backend/config/sources.yaml` now points to those project-local paths. `external_source_inventory` should no longer treat 2024/2025 as outside-project absolute-path dependencies. This does not imply item-level D0 completion; these sources remain passage-level legacy import evidence until parser/import/reconciliation gates prove full coverage.

## 2026-06-12 Update / 2023-2024 Verified Structured Seed

`data/gaokao_verified_xgkii_2023_2024.jsonl` is now registered as `gaokao_verified_xgkii_2023_2024` and referenced by the 2023/2024 paper contracts. It contains 12 verified structured rows, split evenly across 2023 and 2024.

This source is useful for lineage and partial reconciliation, but it is not a replacement for the missing/invalid 2023 full-paper PDF and cannot close item-level M0 coverage on its own.

## 2026-06-12 Update / 2023 Third-Party PDF Acquisition

The active 2023 PDF source is now `third_party_pdf_xgkii_english_2023_zizzs`, acquired through the project data-source acquisition tool. The locked local artifact is:

```text
data/external/exam_sources/third_party_pdfs/2023_xgkii_english_zizzs.pdf
```

- bytes: `194602`
- sha256: `c51421c891f7e1344b5e8bb058fbfa57b7fbf3fec4b6d05d1ca7bbcbe0e39eda`
- acquisition manifest: `data/reports/external_source_acquisition_2023_zizzs.json`

The previous `data/external/gaokao_2023_xgkii_english.pdf` file remains a rejected 427-byte artifact and is no longer an active source contract. The new PDF is still a third-party source, so item-level D0 closure requires EOL/structured-row cross-check and parser/import gates.

## 2026-06-12 Update / Registry-Driven PDF Cross-Verify

`cross_verify_pdf.py` now resolves PDF inputs from `backend/config/sources.yaml` instead of hard-coded 2024/2025 sibling-project paths. The M0 gate sequence includes:

```bash
python3 scripts/tools/audit/cross_verify_pdf.py --year 2023
```

This gate checks the registry-owned 2023 PDF against DB rows and `data/gaokao_verified_xgkii_2023_2024.jsonl`. It should run before treating the third-party PDF as usable 2023 truth evidence. 2024/2025 import input paths now point to the project-local PDF mirrors.

Known follow-up: preserve or remove old `PDF_MAP` imports in legacy callers after reviewing call sites.

## 2026-06-12 Update / PDF_MAP Compatibility Shim

`cross_verify_pdf.py` now exports `PDF_MAP` again for legacy callers. The map is generated from the source registry through `build_pdf_map()`, so old imports remain compatible without reintroducing hard-coded 2024/2025 sibling-project paths.

## 2026-06-12 Update / PDF Cross-Verify Strict Exit

`pdf_cross_verify_2023` now uses strict mode:

```bash
python3 scripts/tools/audit/cross_verify_pdf.py --year 2023 --strict
```

Strict mode returns non-zero when the requested year fails or skips, so missing PDFs, unregistered PDF sources, and text mismatches cannot silently pass the M0 gate sequence.

## 2026-06-12 Update / 2023 EOL Landing Page Acquisition

The 2023 EOL landing page is now a registered and acquired source:

```text
data/external/exam_sources/eol/2023_xgkii_english_eol.html
```

- source id: `eol_xgkii_english_2023_page`
- bytes: `167619`
- sha256: `acf5ddd6e6be42fbfd39b05304bf0abca2a9997802a9f9cd2e70c30cb04cc140`
- acquisition manifest: `data/reports/external_source_acquisition_2023_eol_page.json`

This page strengthens the 2023 source lineage but does not close item-level D0 coverage. It should be used with `pdf_cross_verify_2023` and later parser/import gates.

## 2026-06-12 Update / EOL HTML Identity in PDF Cross-Verify

`pdf_cross_verify_2023` now checks both layers:

```text
1. registry-owned PDF vs DB / verified structured seed text
2. registered EOL HTML landing page identity markers: year, English subject, New Curriculum II marker
```

The report now includes `html_identity_checks` and `html_summary`. In strict mode, either PDF/structured mismatch or HTML identity failure returns non-zero.

## 2026-06-12 Update / Source Cross-Check Rules Config

HTML landing-page identity rules now live in:

```text
backend/config/source_crosscheck_rules.yaml
```

`pdf_cross_verify_2023` reads identity required groups from that config by source id. `external_source_inventory` also fails landing-page sources that do not have identity rules, so source identity checks remain configuration-owned and fail closed.

## 2026-06-12 Update / Cross-Check Rule Consistency Audit

`source_contract_consistency` now audits `backend/config/source_crosscheck_rules.yaml`. It blocks landing-page sources without identity rules and invalid rule definitions such as unknown source ids, empty groups, or empty tokens. This catches source identity rule drift before `pdf_cross_verify_2023` runs.

## 2026-06-12 Update / 2021 Listening Candidate Quarantine

`sunedu_new_gaokao_i_listening_2021_candidate` is now quarantined outside active `exam_sources`. It remains documented in `backend/config/sources.yaml` under `quarantined_exam_sources`, but active source registry and M0 paper contracts should not use it to close 2021 New Curriculum II truth coverage without explicit shared-listening proof.

The remaining 2021 work is content-level: rebuild/review the EOL draft, key listening rows where supported by the EOL source, and pass import-readiness gates before DB writes.

## 2026-06-12 Update / Quarantined Source Reference Guard

`source_contract_consistency` now reads `quarantined_exam_sources` from `backend/config/sources.yaml`. Paper contracts that reference quarantined source ids are blocked with `contract_references_quarantined_source`, and duplicate active/quarantined source ids are blocked with `source_id_active_and_quarantined`.

## 2026-06-12 Update / EOL Review Backlog Gate

The M0 gate sequence now includes explicit EOL review backlog gates between field coverage and import readiness:

```bash
python3 scripts/tools/audit/eol_review_backlog.py --year 2021 --strict
python3 scripts/tools/audit/eol_review_backlog.py --year 2022 --strict
```

Rules live in `backend/config/eol_review_rules.yaml`. These gates do not judge answers automatically or write DB rows; they list unresolved item-level review backlog such as blocking review statuses, missing source spans, missing required answers, and unkeyed listening answers.

## 2026-06-12 Update / EOL Review Rule Consistency Audit

`source_contract_consistency` now audits `backend/config/eol_review_rules.yaml`. It blocks missing `eol_review_backlog`, required token lists that are empty, empty tokens, and `priority_issue_codes` that are not emitted by the EOL review backlog tool. This catches review-rule drift before `eol_review_backlog` gates run.

## 2026-06-12 Update / EOL Review Decision Overlay

EOL review backlog gates now support review-decision overlays. The contract lives in:

```text
backend/config/eol_review_decisions.yaml
```

Default per-year decision files live under:

```text
data/external/exam_sources/eol/review_decisions/{year}_xgkii_english_eol_review_decisions.jsonl
```

The stable key is `year + paper_type + observed_question_number + question_type`. `import_ready` decisions must include `answer`, `source_id`, and `source_span`. The backlog gate validates decisions, applies overlays, and then computes remaining backlog without mutating the generated draft.

## 2026-06-12 Update / EOL Review Worksheet Generator

To prepare manual/programmatic review decisions, generate a worksheet from remaining backlog rows:

```bash
python3 scripts/tools/audit/eol_review_worksheet.py --year 2021
python3 scripts/tools/audit/eol_review_worksheet.py --year 2022
```

The worksheet is written under `data/reports/` and is not consumed by gates. Reviewers should copy completed decisions into the official per-year decision files defined by `backend/config/eol_review_decisions.yaml`:

```text
data/external/exam_sources/eol/review_decisions/{year}_xgkii_english_eol_review_decisions.jsonl
```

Backlog gates then validate and apply those official decision files without mutating the generated draft.

## 2026-06-12 Update / EOL Review Decision Materializer

After a reviewer fills worksheet rows, convert completed rows into the official decision file with:

```bash
python3 scripts/tools/audit/eol_review_decision_materialize.py --year 2021 --worksheet data/reports/eol_review_worksheet_2021_<stamp>.jsonl
python3 scripts/tools/audit/eol_review_decision_materialize.py --year 2022 --worksheet data/reports/eol_review_worksheet_2022_<stamp>.jsonl
```

The materializer only includes rows with `decision_status`, validates them against `backend/config/eol_review_decisions.yaml`, and writes to the official per-year decision path by default. It does not mutate generated drafts or write DB rows.

## 2026-06-12 Update / EOL Review Worksheet Stable-Key Alignment

Backlog identities now expose `paper_type` and `observed_question_number`, matching the review-decision stable key. Worksheet generation uses `observed_question_number` directly, so reviewer rows can be materialized into official decisions without losing the original draft row context.

## 2026-06-12 Update / EOL Review Worksheet Shape Validation

The worksheet materializer now validates worksheet shape before creating official review decisions. Required worksheet fields are configured in `backend/config/eol_review_decisions.yaml` under `worksheet_required_fields`. Missing stable-key fields or an unknown `worksheet_kind` block output.

## 2026-06-12 Update / EOL Review Materializer Safety Guards

The review decision materializer now blocks worksheet rows whose `year` does not match CLI `--year`, and reports `decision_output_exists` before writing if the official decision file already exists and `--overwrite` was not passed. This keeps manifest status aligned with actual write behavior.

## 2026-06-12 Update / Non-Import-Ready Decision Blocking

EOL review backlog rules now treat `review_decision_*` review statuses as blocking. Only an `import_ready` decision is overlaid as `review_status=import_ready`; `needs_followup`, `rejected`, and `rescope` remain backlog blockers until resolved or explicitly re-scoped through contract changes.

## 2026-06-12 Update / EOL Review Decision Coverage Audit

After materializing official review decisions, inspect stable-key coverage with:

```bash
python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2021 --strict
python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2022 --strict
```

Backlog gates also now report `unmatched_review_decision_key` when an official decision key does not match the current draft. This prevents typoed or stale decisions from silently doing nothing.

## 2026-06-12 Update / EOL Review Decision Coverage Gates

The M0 gate sequence now runs decision coverage before review backlog:

```bash
python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2021 --strict
python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2022 --strict
```

These gates catch missing, stale, or unmatched official review decisions before backlog gates apply overlays. They write reports only; they do not mutate generated drafts or write DB rows.
