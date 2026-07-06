# Truth Baseline Audit 2021-2025

- Generated at: `2026-07-06T10:56:35+00:00`
- Run ID: `e97e3209fa5e733a`
- Status: `FAIL`
- DB: `/Users/dp/Documents/M/gaozhong/data/db/gaozhong.duckdb`
- Structured truth source: `/Users/dp/Documents/M/gaozhong/data/external/gaokao_xgkii_2021_2025_mirror.jsonl`
- Verified JSONL: `/Users/dp/Documents/M/gaozhong/data/gaokao_verified_xgkii_2023_2024.jsonl`

## Summary by Year

| Year | DB rows | Truth rows | Matched | DB only | Truth only | QB mapped | Target min | Gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 65 | 19 | 1 | 64 | 18 | 65 | 55 | 36 |
| 2022 | 45 | 0 | 0 | 45 | 0 | 45 | 55 | 55 |
| 2023 | 6 | 23 | 6 | 0 | 17 | 6 |  |  |
| 2024 | 9 | 23 | 6 | 3 | 17 | 9 |  |  |
| 2025 | 9 | 0 | 0 | 9 | 0 | 9 |  |  |

## Findings

- DB target gaps: `1`
- Truth-source target gaps: `2`
- Truth-only rows: `52`
- Pollution candidates: `109`
- Missing question_bank real mappings: `0`

## Interpretation

- FAIL: M0 truth baseline is not closed for the configured target scope.
- Do not treat Phase A / M0 as complete until DB target gaps, truth-only rows, pollution candidates, and question_bank mapping gaps are resolved or explicitly re-scoped.
