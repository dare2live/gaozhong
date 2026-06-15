# Week61 Review Round1 - M0 Truth Baseline Gate

Date: 2026-06-12
Scope: Phase 7.12 / Milestone A-M0 truth baseline for 2021-2025 New Curriculum Paper II English data.

## Verdict

FAIL as expected. This is a discovery and governance pass, not a DB-write remediation.

The previous `goal.md` status claimed M0 was complete, but the current DB and truth-source reconciliation do not prove that. The strict gate now fails when M0 is not actually closed.

## Evidence

- Strict gate log: `logs/truth-baseline-gate-20260612-091035.log`
- Strict gate command output: `logs/truth-baseline-strict-20260612-091035.log`
- JSON report: `data/reports/truth_baseline_2021_2025.json`
- Markdown report: `data/reports/truth_baseline_2021_2025.md`
- Cross-verify report: `data/reports/cross_verify_2021_2025.json`
- Gap report: `data/reports/cross_verify_gaps_2021_2025.json`

## Current Gate Result

- `python3 -m py_compile scripts/tools/audit/truth_baseline_audit.py`: PASS
- `python3 scripts/tools/audit/truth_baseline_audit.py --strict`: exit 1, expected because open M0 findings remain.
- Status: FAIL
- DB rows in target years: 74
- Truth rows: 65
- Mapped rows: 17
- Truth-only rows: 48
- DB-only rows: 57
- Pollution candidates: 45
- Missing `question_bank` real mappings: 18
- 2021 truth count: 19 / target 55, gap 36
- 2022 truth count: 0 / target 55, gap 55

## Tooling Change

`scripts/tools/audit/truth_baseline_audit.py` now records an explicit `status`, emits `data/reports/truth_baseline_2021_2025.md`, counts DB target gaps, truth-source target gaps, pollution candidates, and missing `question_bank` mappings, and supports `--strict` for non-zero exit when M0 is not closed.

## Interpretation

M0 must be treated as open until the missing 2021/2022 truth source rows, DB-only pollution candidates, and `question_bank` mappings are resolved or explicitly re-scoped with stronger evidence.

## Post-change Validation

- `python3 -m py_compile scripts/tools/audit/truth_baseline_audit.py`: PASS
- `python3 scripts/data_accuracy_check.py`: PASS, see `logs/data-accuracy-week61-20260612-091134.log`
- `codegraph sync`: exit 0, see `logs/codegraph-sync-week61-20260612-091134.log`
- `codegraph affected scripts/tools/audit/truth_baseline_audit.py`: exit 0, no affected test files, see `logs/codegraph-affected-week61-20260612-091134.log`
- `moth doctor --repo . --format markdown`: exit 0, no issues, Complexity PASS/new findings 0, WARN only for dirty worktree + CodeGraph stale, see `logs/moth-doctor-week61-20260612-091134.md`
