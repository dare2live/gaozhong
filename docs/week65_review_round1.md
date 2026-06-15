# Week65 Review Round1 - Source Registry and Paper Contracts

Date: 2026-06-12
Scope: Convert known historical exam assets into explicit source and import contracts.

## Verdict

PARTIAL PROGRESS. No DB import was performed.

The project has historical exam assets, but they are now classified by source state rather than treated as a single completed truth base.

## Registered Source Families

- `gaokao_bench_english_2010_2022`: mirrored GAOKAO-Bench English JSONL files under `data/external/gaokao_bench`.
- `gaokao_bench_updates_english_2023`: mirrored 2023 GAOKAO-Bench Updates JSON files.
- `local_pdf_xgkii_english_2023_suspicious`: local 2023 PDF candidate, measured at only 427 bytes; it is intentionally configured to fail a real-PDF min-bytes gate until replaced or explained.
- `legacy_local_pdf_xgkii_english_2024`: sibling `gaokao` project PDF used by the legacy importer; current DB rows are passage-level, not full item-level proof.
- `legacy_local_pdf_xgkii_english_2025`: sibling `gaokao` project PDF used by the legacy importer; current DB rows are passage-level, not full item-level proof.
- `sunedu_new_gaokao_i_listening_2021_candidate`: listening candidate labelled New Gaokao I; not accepted as New Curriculum II truth without a shared-listening contract.
- `eol_xgkii_english_2021` and `eol_xgkii_english_2022` were already registered in the previous step.

## New Configuration Contracts

- `backend/config/exam_paper_contracts.yaml`
  - Defines the M0 New Curriculum II English target for 2021-2025.
  - Keeps expected section and row coverage outside parser/import code.
  - Explicitly preserves known gaps for 2021/2022/2023/2024/2025.

- `backend/config/import_policies.yaml`
  - Defines import readiness rules for exam truth sources and benchmark seed imports.
  - Requires dry-run first and blocks import on missing spans, answer contamination, shifted numbering, failed source contracts, empty rows, unknown paper type, or candidate-only sources.

## Tooling Change

- `backend/services/data_sources/registry.py` and `backend/services/data_sources/fetcher.py` now support local-only attachments.
- This is required for legacy local PDF sources that currently live in the sibling `gaokao` project and have no stable download URL in this repository.

## Interpretation

- Historical exam material exists in the project, but its reliability varies by source family.
- GAOKAO-Bench rows remain useful for trends, pattern mining, and question-bank seeding.
- EOL 2021/2022 remains the active path for M0 truth-source repair, but those drafts are still not import-ready.
- The 2023 local PDF candidate is suspiciously small and must not be treated as an authoritative raw paper.
- 2024/2025 DB rows are useful, but current import granularity is passage-level rather than full item-level.

## Validation

Not run in this step. This step only updated contracts and local-only registry support.

Next validation command when approved:

```bash
python3 scripts/tools/data_sources/acquire_external_source.py --reuse-existing --strict
```

Expected behavior:

- Most registered local files should pass sha/size checks.
- `local_pdf_xgkii_english_2023_suspicious` should fail until the 427-byte candidate is replaced or explicitly re-scoped.

## Next Gate

1. Replace or explain `data/external/gaokao_2023_xgkii_english.pdf`.
2. Run source registry strict verification.
3. Move only verified sources toward structured extraction and import-ready review.
4. Keep `truth_baseline_audit.py --strict` as the M0 closure gate.

## Follow-up: Read-only Import Dry-run Contract

Additional change in the same Week65 contract slice:

- Added `backend/services/imports/readiness.py`
- Added `scripts/tools/imports/dry_run_exam_import.py`

Purpose:

- Read structured JSONL rows.
- Read `backend/config/import_policies.yaml`.
- Produce a readiness report with `ready`, `warn`, or `blocked`.
- Refuse import readiness when required source fields, stem/source span, paper type, review status, source status, or numbering explanation are incomplete.

Important boundary:

- This is read-only.
- It does not connect to DuckDB.
- It does not allocate question IDs.
- It does not import rows.

Expected next command when validation is explicitly allowed:

```bash
python3 scripts/tools/imports/dry_run_exam_import.py data/external/exam_sources/eol/2021_xgkii_english_eol_structured_draft.jsonl --strict
```

Expected current result:

- `blocked`, because EOL draft rows are still marked `draft_not_import_ready_*` and do not yet carry all import-required source fields.

## Follow-up: Exam Paper Contract Audit

Additional read-only audit added:

- `backend/services/audit/exam_contracts.py`
- `scripts/tools/audit/exam_paper_contract_audit.py`

Purpose:

- Read `backend/config/exam_paper_contracts.yaml`.
- Connect to `data/db/gaozhong.duckdb` in read-only mode.
- Compare each target year against `expected_min_rows`.
- Report both rows matching the configured paper-type aliases and all rows for the same year.

Why this matters:

- The project can have historical exam rows for a year without satisfying the M0 New Curriculum II contract.
- The checker makes that distinction visible before any parser/import work claims progress.

Expected next command when validation is explicitly allowed:

```bash
python3 scripts/tools/audit/exam_paper_contract_audit.py --strict
```

Expected current result:

- `fail`, because the contract itself records 2021-2025 as not fully closed and current DB row counts are below the configured item-level target for at least the weak years.

## Follow-up: Source Registry Consistency Audit

Additional read-only config audit added:

- `backend/services/audit/source_contracts.py`
- `scripts/tools/audit/source_contract_audit.py`

Purpose:

- Read `backend/config/sources.yaml` through the source registry.
- Read `backend/config/exam_paper_contracts.yaml`.
- Check that every contract-referenced source exists in the registry.
- Check that every source has at least one attachment and minimum byte gate.
- Warn when a contract references a `candidate` or `suspicious` source.
- Warn when an exam/listening source exists in the registry but is not referenced by any paper contract.

Boundary:

- No download.
- No DB connection.
- No file checksum validation.
- No import.

Expected next command when validation is explicitly allowed:

```bash
python3 scripts/tools/audit/source_contract_audit.py --strict
```

This command should run before download/source strict verification, because it catches config-level contradictions first.

## Follow-up: M0 Gate Plan and Runbook

Additional coordination artifacts added:

- `scripts/tools/audit/m0_gate_plan.py`
- `docs/m0_gate_runbook.md`

Purpose:

- Keep the M0 gate sequence in one machine-readable and human-readable place.
- Prevent running later gates when earlier source/config gates are already broken.
- Make the expected current failure points explicit instead of relying on conversation memory.

Boundary:

- `m0_gate_plan.py` prints a plan only.
- It does not run validation commands.
- It does not connect to DuckDB.
- It does not write DB or source artifacts.

## Follow-up: EOL Draft Source Lineage Fields

Additional parser/readiness alignment added:

- Updated `scripts/tools/audit/structure_eol_exam_docx.py`
- Updated `backend/services/imports/readiness.py`

Purpose:

- Future EOL structured draft rebuilds now include import-policy source lineage fields:
  - `source_id`
  - `source_repo`
  - `source_sha256`
  - `source_url`
  - `source_state`
  - `source_span`
- `source_span` is kept equal to the extracted span preview for now, so the dry-run checker can distinguish missing source trace from other import blockers.
- `backend/services/imports/readiness.py` now includes `source_span` when deciding whether a row has usable stem/source text.

Boundary:

- Existing JSONL drafts were not rebuilt in this step.
- No import was attempted.
- Rows remain `draft_not_import_ready_*`, so dry-run should still block until item-level review and missing source gaps are resolved.

## Follow-up: EOL Extraction Service Boundary

Additional service boundary added:

- `backend/services/extraction/exam_eol.py`

Purpose:

- Define the service-level contract for EOL exam source extraction.
- Centralize EOL source metadata for 2021/2022.
- Centralize default text/draft/audit paths.
- Define required structured draft fields expected by import-readiness gates.

Boundary:

- The current parser still lives in `scripts/tools/audit/structure_eol_exam_docx.py`.
- This is not a completed parser migration.
- No JSONL draft was rebuilt.
- No DB import was attempted.

Next migration step:

- Move parser logic from the audit script into `backend/services/extraction/exam_eol.py`.
- Then make `scripts/tools/audit/structure_eol_exam_docx.py` a thin CLI wrapper around the service.

## Follow-up: EOL Metadata Single Source

Additional cleanup:

- Updated `scripts/tools/audit/structure_eol_exam_docx.py` to import `source_metadata` and `draft_paths` from `backend/services/extraction/exam_eol.py`.
- Removed the duplicate EOL metadata dictionary from the script.

Purpose:

- Keep source id, sha256, URL, source state, and default paths in one service-level source.
- Reduce drift before the full parser migration into `backend/services/extraction/exam_eol.py`.

Boundary:

- Parser logic itself still lives in the script.
- No JSONL draft was rebuilt.
- No validation command was run.

## Follow-up: EOL Metadata Registry Ownership

Additional single-source cleanup:

- Updated `backend/services/extraction/exam_eol.py` to load EOL metadata from `backend/config/sources.yaml` through `backend.services.data_sources.load_registry`.
- The service now keeps only the minimal `year -> source_id` mapping and derives source repo, sha256, URL, state, and text path from the source registry.

Purpose:

- Make `backend/config/sources.yaml` the owner of EOL source contracts.
- Prevent source URL, checksum, and state drift between config, service, and script.

Boundary:

- No JSONL draft was rebuilt.
- No source acquisition verification was run.
- No DB import was attempted.

## Follow-up: EOL Parser Moved to Service Layer

Additional architecture migration:

- Moved EOL draft parser logic into `backend/services/extraction/exam_eol.py`.
- Replaced `scripts/tools/audit/structure_eol_exam_docx.py` with a thin CLI wrapper.

Purpose:

- Keep extraction computation in `backend/services/extraction/` instead of an audit script.
- Preserve the CLI command surface while making parser logic reusable by future gates and import dry-runs.
- Continue keeping DB writes out of the extraction step.

Boundary:

- No JSONL draft was rebuilt.
- No validation command was run.
- No DB import was attempted.
- EOL rows remain not import-ready until rebuilt, reviewed, and passed through dry-run gates.

## Follow-up: EOL Extraction CLI Command Surface

Additional command-surface migration:

- Added `scripts/tools/extraction/build_eol_exam_draft.py` as the preferred CLI for EOL draft generation.
- Added `scripts/tools/extraction/__init__.py`.
- Changed `scripts/tools/audit/structure_eol_exam_docx.py` into a backward-compatible wrapper that delegates to the new extraction CLI.

Purpose:

- Keep extraction commands under `scripts/tools/extraction/` instead of `scripts/tools/audit/`.
- Preserve old command compatibility while making the intended command surface explicit.

Boundary:

- No JSONL draft was rebuilt.
- No validation command was run.
- No DB import was attempted.

## Follow-up: M0 Gate Plan Includes EOL Draft Rebuild

Additional gate-plan update:

- Updated `scripts/tools/audit/m0_gate_plan.py`.
- Updated `docs/m0_gate_runbook.md`.

Purpose:

- Insert EOL draft rebuild steps before import-readiness dry-runs.
- Use the new service-backed extraction CLI:
  - `python3 scripts/tools/extraction/build_eol_exam_draft.py --year 2021`
  - `python3 scripts/tools/extraction/build_eol_exam_draft.py --year 2022`

Boundary:

- This update changes the documented gate order only.
- It does not rebuild JSONL drafts.
- It does not run validation.
- It does not write DuckDB.

## Follow-up: Import Readiness Report Aggregates

Additional dry-run report improvement:

- Updated `backend/services/imports/readiness.py`.

Purpose:

- Add `finding_code_counts` to import-readiness JSON reports.
- Add `finding_severity_counts` to import-readiness JSON reports.
- Make blocked dry-runs actionable at controller level without manually scanning every row finding.

Boundary:

- Blocking logic was not changed.
- No dry-run command was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: Source State Taxonomy

Additional config/audit hardening:

- Added `backend/config/source_states.yaml`.
- Updated `backend/services/audit/source_contracts.py`.

Purpose:

- Make source `status` strings machine-checkable.
- Allow descriptive status values while requiring at least one recognized state token.
- Preserve `raw_source_acquired` as a legacy alias for `raw_acquired`.
- Keep `candidate_only` and `suspicious` explicit non-importable states.

Boundary:

- No source-contract audit was run.
- No source files were checked.
- No DB import was attempted.

## Follow-up: Import Readiness Enforces Source State

Additional dry-run gate hardening:

- Updated `backend/config/import_policies.yaml`.
- Updated `backend/services/imports/readiness.py`.

Purpose:

- Require `source_state` in exam truth-source import rows.
- Enforce `policy.required_source_state` during dry-run checks.
- Block rows whose `source_state` is below `import_ready` for `exam_truth_source_import`.

Expected effect:

- Rebuilt EOL draft rows with `source_state=structured_draft_not_import_ready` will be blocked explicitly by `source_state_below_import_policy`.
- This keeps source-state semantics aligned with the M0 data-state machine.

Boundary:

- No dry-run command was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: Shared Import Policy Contract Reader

Additional contract cleanup:

- Added `backend/services/contracts/import_policy.py`.
- Added `backend/services/contracts/__init__.py`.
- Updated `backend/services/imports/readiness.py` to use the shared policy reader.
- Updated `backend/services/extraction/exam_eol.py` so EOL required draft fields combine EOL business fields with `exam_truth_source_import.require_source_fields` from `backend/config/import_policies.yaml`.

Purpose:

- Keep import-policy loading in a shared contract layer.
- Avoid duplicating source lineage field lists in extraction and import-readiness code.
- Preserve dependency direction: extraction and imports both read shared contracts, rather than extraction depending on the imports implementation.

Boundary:

- No validation command was run.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: EOL Draft Field Coverage Audit

Additional pre-readiness audit added:

- Updated `backend/services/extraction/exam_eol.py`.
- Added `scripts/tools/audit/eol_draft_field_audit.py`.
- Updated `scripts/tools/audit/m0_gate_plan.py`.
- Updated `docs/m0_gate_runbook.md`.

Purpose:

- Check rebuilt EOL JSONL drafts for required field coverage before semantic import-readiness checks.
- Reuse EOL business fields plus source fields from `backend/config/import_policies.yaml`.
- Keep schema/lineage failures separate from source-state or review-status failures.

Boundary:

- Field coverage passing does not mean import-ready.
- No audit command was run.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: Source State Matching Bug Fix

Bug fixed:

- Added `backend/services/contracts/source_state.py`.
- Updated `backend/services/contracts/__init__.py`.
- Updated `backend/services/imports/readiness.py`.
- Updated `backend/services/audit/source_contracts.py`.

Problem:

- `readiness.py` previously checked `required_source_state` with substring matching.
- This could incorrectly treat `structured_draft_not_import_ready` as satisfying `import_ready` because the string contains `import_ready`.

Fix:

- Source status is now parsed by recognized state-token prefix.
- `structured_draft_not_import_ready` resolves to `structured_draft`.
- `import_ready` must resolve exactly to `import_ready` for import-readiness policy satisfaction.
- Source-contract audit reuses the same state parser.

Boundary:

- No dry-run command was executed.
- No source-contract audit was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: Nullable Source Fields in Import Policy

Additional contract refinement:

- Updated `backend/config/import_policies.yaml`.
- Updated `backend/services/imports/readiness.py`.
- Updated `backend/services/extraction/exam_eol.py`.

Purpose:

- Distinguish a missing field from a field that is present but legitimately `null`.
- Allow `observed_question_number` and `reference_answer_number` to be null for rows such as writing prompts or unkeyed listening rows while still requiring the field to exist.
- Keep schema/field coverage checks focused on contract shape instead of over-reporting nullable source fields.

Boundary:

- This does not make nullable rows import-ready.
- Review status, source state, source span, and semantic gates still apply.
- No audit command was run.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: EOL Field Audit Nullable Reporting

Additional field-audit report improvement:

- Updated `backend/services/extraction/exam_eol.py`.

Purpose:

- Make EOL draft field coverage reports distinguish:
  - required fields,
  - nullable fields,
  - absent required fields,
  - present but empty non-nullable fields.
- Avoid confusing legitimate `null` values for `observed_question_number` / `reference_answer_number` with missing schema fields.

Boundary:

- Field-audit pass/fail semantics were not loosened.
- No audit command was run.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: EOL Field Audit CLI Summary

Additional CLI usability improvement:

- Updated `scripts/tools/audit/eol_draft_field_audit.py`.

Purpose:

- Print top missing fields in the CLI output when field coverage fails.
- Let the controller see the primary schema/lineage blockers without opening the JSON report first.

Boundary:

- JSON report schema and pass/fail logic did not change.
- No audit command was run.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: Source Contract Audit Matched State Report

Additional report improvement:

- Updated `backend/services/audit/source_contracts.py`.

Purpose:

- Include a `source_states` section in source-contract audit reports.
- Show each source id, raw status, matched state token, and risky flag.
- Make source-state parsing visible after the substring bug fix.

Boundary:

- Audit pass/fail semantics were not changed.
- No source-contract audit command was run.
- No source files were checked.
- No DB import was attempted.

## Follow-up: M0 Gate Sequence Config Ownership

Additional gate-plan cleanup:

- Added `backend/config/m0_gates.yaml`.
- Updated `scripts/tools/audit/m0_gate_plan.py` to read the gate sequence from config.

Purpose:

- Make the M0 gate sequence a configuration contract instead of hard-coded Python.
- Avoid maintaining the same ordered gate list in both code and docs.
- Preserve `m0_gate_plan.py` as a non-executing planner only.

Boundary:

- No planner command was run.
- No gate was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: M0 Runbook Uses Gate Config

Additional documentation cleanup:

- Updated `docs/m0_gate_runbook.md`.

Purpose:

- Stop duplicating the full M0 gate table in the runbook.
- Make `backend/config/m0_gates.yaml` the single source of truth for gate order and commands.
- Keep the runbook focused on execution rules and failure handling.

Boundary:

- No planner command was run.
- No gate was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: M0 Gate Planner Config Validation

Additional planner hardening:

- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Validate `backend/config/m0_gates.yaml` before rendering a plan.
- Fail fast if gates are empty, orders are not contiguous from 1, gate names duplicate, or required fields are blank.
- Prevent a malformed gate config from producing a misleading plan.

Boundary:

- No planner command was run.
- No gate was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: M0 Gate Planner Boolean Flag Validation

Additional planner hardening:

- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Validate `writes_db` and `executes_external_fetch` are real YAML booleans.
- Prevent string values such as `"false"` from being silently accepted in gate risk flags.

Boundary:

- No planner command was run.
- No gate was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: M0 Gate Planner Fetch-Flag Consistency

Additional planner hardening:

- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Validate that `acquire_external_source.py` gates without `--reuse-existing` must declare `executes_external_fetch=true`.
- Allow `--reuse-existing` acquisition verification to remain `executes_external_fetch=false`.
- Prevent real download-capable gates from being mislabeled as local-only.

Boundary:

- No planner command was run.
- No gate was executed.
- No external fetch occurred.
- No DB import was attempted.

## Follow-up: M0 Gate Artifact Write Flag

Additional gate-risk metadata:

- Updated `backend/config/m0_gates.yaml`.
- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Add `writes_artifacts` to every M0 gate.
- Distinguish report/manifest/JSONL/audit writes from DuckDB writes.
- Validate `writes_artifacts` is a real YAML boolean, alongside `writes_db` and `executes_external_fetch`.

Current meaning:

- Current M0 gates write evidence artifacts but do not write DuckDB.
- Therefore current gates are configured with `writes_artifacts=true` and `writes_db=false`.

Boundary:

- No planner command was run.
- No gate was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: M0 Gate Planner Risk Summary

Additional planner output improvement:

- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Add `risk_summary` to JSON output.
- Report which gates write artifacts, write DB, or execute external fetch.
- Make pre-execution risk review possible without scanning every gate manually.

Boundary:

- Markdown output was not changed.
- No planner command was run.
- No gate was executed.
- No DB import was attempted.

## Follow-up: M0 Gate Planner Top-level Risk Booleans

Additional planner output consistency fix:

- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Derive top-level JSON risk booleans from configured gates.
- Keep `writes_artifacts`, `writes_db`, and `executes_external_fetch` consistent with `risk_summary`.
- Avoid future misleading output if any configured gate becomes DB-writing or network-fetching.

Boundary:

- No planner command was run.
- No gate was executed.
- No JSONL draft was rebuilt.
- No DB import was attempted.

## Follow-up: M0 Gate Planner Markdown Risk Columns

Additional planner output improvement:

- Updated `scripts/tools/audit/m0_gate_plan.py`.

Purpose:

- Add `Writes artifacts`, `Writes DB`, and `External fetch` columns to markdown output.
- Make human pre-execution review possible without using JSON output.

Boundary:

- Gate config and execution semantics did not change.
- No planner command was run.
- No gate was executed.
- No DB import was attempted.
