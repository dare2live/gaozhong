# Week60 Review Round1 - Mythos P3 Remediation

Date: 2026-06-12
Scope: Mythos P3: manifest / derived artifact drift control and Moth / CodeGraph audit posture.

## Verdict

PASS with residual audit posture WARN.

Functional gates passed:
- Manifest JSONL determinism: PASS. Two consecutive `scripts/build_manifest.py` runs produced identical SHA-256 hashes for `data/manifest/textbook_manifest.jsonl`, `data/manifest/curriculum_manifest.jsonl`, and `data/manifest/structured_manifest.jsonl`.
- Python syntax check: PASS.
- API payload gate: PASS after starting `backend/api/main.py --port 8765`.
- D0 data accuracy: PASS.
- Weekly healthcheck alert wrapper: PASS and cleared `/tmp/gaozhong_ALERT_weekly_healthcheck.flag`.
- M4/M5 smoke: PASS.
- CodeGraph sync: exit 0.
- Moth doctor: exit 0, status WARN only.

Residual WARN:
- Moth still reports dirty worktree and CodeGraph stale / index not up to date.
- This is expected until the current new/untracked project artifacts are intentionally staged/tracked or excluded by policy.
- Moth issues: none.
- Complexity diff: PASS, new findings 0, new high findings 0.

## Evidence

- Manifest determinism log: `logs/mythos-p3-validation-20260612-090329.log`
- Manifest diff log: `logs/build-manifest-p3-20260612-090329-diff.log`
- API payload pass: `logs/api-payload-check-20260612-090447.log`
- D0 data accuracy pass: `logs/data-accuracy-20260612-090329.log`
- Weekly wrapper pass: `logs/weekly-healthcheck-wrapper-20260612-090447.log`
- M4/M5 smoke pass: `logs/m4-m5-smoke-20260612-090447.log`
- CodeGraph sync: `logs/codegraph-sync-20260612-090447.log`
- Moth report: `logs/moth-doctor-20260612-090447.md`

## Implementation Notes

- `scripts/build_manifest.py` now uses a tracked-file-first input scope for manifest generation, falling back to filesystem scan only when no tracked files are available.
- Manifest JSONL rows no longer carry per-row `fetched_at`, preventing timestamp-only drift across reruns.
- Run-level generation metadata is written separately to `data/manifest/_manifest_run.json`.
- `backend/orchestrator/load.py` now mirrors the tracked-file-first input scope and avoids silently swallowing per-file manifest load exceptions.
- DB `file_manifest.fetched_at` remains a run-level load timestamp to satisfy the existing schema without contaminating row-level source lineage.
