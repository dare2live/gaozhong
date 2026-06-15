# Week62 Review Round1 - 2021/2022 Raw Truth Source Acquisition

Date: 2026-06-12
Scope: Phase A/M0 raw source acquisition for 2021/2022 New Curriculum Paper II English.

## Verdict

PARTIAL PROGRESS. No DB import was performed.

## Sources Acquired

- 2021 EOL landing page: `https://gaokao.eol.cn/shiti/zhenti/202204/t20220430_2223302.shtml`
- 2021 local docx: `data/external/exam_sources/eol/2021_xgkii_english_eol.docx`
- 2021 local text: `data/external/exam_sources/eol/2021_xgkii_english_eol.txt`
- 2021 sha256: `d5f5bf68536c09240533809b1f6cb7bd2f54256bb668069e5ebfabf2293caee3`

- 2022 EOL landing page: `https://gaokao.eol.cn/shiti/yy/202207/t20220713_2237604.shtml`
- 2022 local docx: `data/external/exam_sources/eol/2022_xgkii_english_eol.docx`
- 2022 local text: `data/external/exam_sources/eol/2022_xgkii_english_eol.txt`
- 2022 sha256: `092466a264b8effda7eca0703949dd9f2470c0e3069815096afc2ec79477854f`

## Inventory Evidence

- Source manifest: `data/external/exam_sources/eol/source_manifest_20260612.json`
- Raw inventory report: `data/reports/raw_exam_source_inventory_20260612.json`
- Download / extraction log: `logs/source-download-eol-20260612-091352.log`

## Findings

- 2021 raw source appears complete for the configured M0 target: extracted text has section markers for listening, reading, language use, writing, reference answers, and observed question numbers 1-55.
- 2022 raw source is useful but partial relative to the current strict target: extracted text has reading, language use, writing, and reference answers; observed written-paper numbers are mainly 21-65; no listening section was observed.
- Therefore, 2022 should not be marked complete from this source alone. Either a separate 2022 listening source is required, or the M0 target contract must explicitly split national written paper vs province listening source.

## Next Gate

Before importing to `exam_questions`:

1. Build a reviewed structured JSONL converter for the EOL docx text.
2. Verify per-item question number, answer, type, and source span.
3. For 2022, obtain or explicitly scope the missing listening section.
4. Run `python3 scripts/tools/audit/truth_baseline_audit.py --strict` and compare deltas before and after any DB write.

## Validation

- `python3 scripts/tools/audit/truth_baseline_audit.py --strict`: exit 1 as expected; M0 remains open. Log: `logs/truth-baseline-week62-20260612-091549.log`
- `python3 scripts/data_accuracy_check.py`: PASS. Log: `logs/data-accuracy-week62-20260612-091549.log`
- `moth doctor --repo . --format markdown`: exit 0; no issues; Complexity PASS/new findings 0; WARN remains dirty worktree + CodeGraph stale. Log: `logs/moth-doctor-week62-20260612-091549.md`
