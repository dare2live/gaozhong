# Truth Baseline Audit 2021-2025

- Generated at: `2026-06-12T01:23:49+00:00`
- Run ID: `36f7ccf98310f763`
- Status: `FAIL`
- DB: `/Users/dp/Documents/M/gaozhong/data/db/gaozhong.duckdb`
- Structured truth source: `/Users/dp/Documents/M/gaokao/data/structured/english_xgkii_2021_2025.jsonl`
- Verified JSONL: `/Users/dp/Documents/M/gaozhong/data/gaokao_verified_xgkii_2023_2024.jsonl`

## Summary by Year

| Year | DB rows | Truth rows | Matched | DB only | Truth only | QB mapped | Target min | Gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 16 | 19 | 5 | 11 | 14 | 16 | 55 | 36 |
| 2022 | 16 | 0 | 0 | 16 | 0 | 16 | 55 | 55 |
| 2023 | 24 | 23 | 6 | 18 | 17 | 24 |  |  |
| 2024 | 9 | 23 | 6 | 3 | 17 | 0 |  |  |
| 2025 | 9 | 0 | 0 | 9 | 0 | 0 |  |  |

## Findings

- DB target gaps: `2`
- Truth-source target gaps: `2`
- Truth-only rows: `48`
- Pollution candidates: `45`
- Missing question_bank real mappings: `18`

## Interpretation

- FAIL: M0 truth baseline is not closed for the configured target scope.
- Do not treat Phase A / M0 as complete until DB target gaps, truth-only rows, pollution candidates, and question_bank mapping gaps are resolved or explicitly re-scoped.
