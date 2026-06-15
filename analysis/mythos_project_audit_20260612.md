# Mythos Project Audit（2026-06-12）

- 审计框架：`~/.claude/skills/mythos` 通用方法论 + 本项目 `agent.md` 的 Mythos 迁移规则
- 时间窗：`2026-06-12 08:45~08:51（UTC+8）`
- 当前项目状态：M5 运营试运行持续中，`run_id=20260610T135344Z`，Week1~Week57 周检已有证据
- 审计目标：验证现有绿色门禁是否触达真实 payload、数据完整性、DB 写入边界、告警链路、派生产物稳定性和 Moth/CodeGraph 状态

## 执行证据

| 检查 | 命令/方式 | 结果 | 证据 |
|---|---|---|---|
| D0 数据准确率 | `python3 scripts/data_accuracy_check.py` | PASS | `logs/mythos-data-accuracy-20260612-084514.log` |
| M5 weekly healthcheck | `bash scripts/weekly_healthcheck.sh --port 8765` | PASS | `logs/mythos-weekly-healthcheck-20260612-084514.log` |
| M4/M5 smoke | `bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765` | PASS | `logs/mythos-m4-m5-smoke-20260612-084514.log` |
| API payload audit | stdlib `urllib` GET + JSON predicate | FAIL | `logs/mythos-api-payload-audit-20260612-084514.log` |
| DB 只读摘要 | DuckDB `read_only=True` | PASS | `logs/mythos-db-summary-20260612-084514.log` |
| Moth doctor | `moth doctor --repo . --format markdown` | WARN（仅 dirty worktree） | `logs/mythos-moth-doctor-20260612-084514.md` |

## Verdict

业务数据与核心 D0 门禁当前为 PASS：核心表非空，`audit_findings` 仅有 `OK=44`，`FAIL/WARN=0`。

运营门禁有效性已完成 P1 修复：新增 payload 级审计曾发现 `/api/students/get` 被旧 smoke 判为 PASS，实际返回 `{"error": "missing ?id"}`。现已将 weekly/M4M5 smoke 升级为 `scripts/api_payload_check.py`，使用真实学生 ID 校验 JSON payload。

## P1 Remediation Evidence

| 检查 | 结果 | 证据 |
|---|---|---|
| 新增 payload gate | PASS | `logs/api-payload-check-20260612-085037.log` |
| weekly 接入新 gate | PASS | `logs/gaozhong-weekly-healthcheck-20260612-085037.log` |
| M4/M5 smoke 接入新 gate | PASS | `logs/m4_m5_smoke_20260612-085037.log` |
| D0 回归 | PASS | `logs/data_accuracy_check_20260612-085037.log` |
| CodeGraph sync | PASS | `logs/codegraph-sync-20260612-085218.log` |
| Moth 后置 | WARN | `logs/moth-doctor-20260612-085218.md`（dirty worktree + untracked new script pending added；Complexity PASS） |

## P2 Remediation Evidence

| 检查 | 结果 | 证据 |
|---|---|---|
| 故意失败写告警 flag | PASS | `logs/alert-wrapper-fail-20260612-085640.log`（`--port 1` 失败后 `/tmp/gaozhong_ALERT_weekly_healthcheck.flag` 存在） |
| 恢复成功清理 flag | PASS | `logs/alert-wrapper-pass-20260612-085640.log`（`--port 8765` 成功后 flag 已清理） |
| payload gate 回归 | PASS | `logs/api-payload-check-20260612-085640.log` |
| D0 回归 | PASS | `logs/data_accuracy_check_20260612-085640.log` |
| weekly/M4M5 smoke 回归 | PASS | `logs/gaozhong-weekly-healthcheck-20260612-085640.log`、`logs/m4_m5_smoke_20260612-085640.log` |
| Moth 后置 | WARN | `logs/moth-doctor-20260612-085810.md`（dirty worktree + CodeGraph pending changes；Complexity PASS） |

## Findings

### P1 — API smoke 会把业务错误 JSON 判为 PASS（已修）

- 证据：`scripts/weekly_healthcheck.sh` 第 49~51 行和 `scripts/m4_m5_smoke.sh` 第 75~78 行只执行 `curl -fsS ... > /dev/null`。
- 证据：`backend/api/routes/students.py` 第 39~42 行在缺少 `id` 时返回 `{"error": "missing ?id"}`。
- 实测：`logs/mythos-api-payload-audit-20260612-084514.log` 中 `/api/students/get` 状态码为 200，但 `ok=false`，payload 为 `{"error": "missing ?id"}`。
- 影响：Week1~Week57 的 smoke 证明了 HTTP 可达，但不能证明 `/api/students/get` 业务路径可用。
- 修复：新增 `scripts/api_payload_check.py`，并接入 `scripts/weekly_healthcheck.sh` 与 `scripts/m4_m5_smoke.sh`；`/api/students/get` 现在使用 `/api/students/list` 返回的真实 `student_id` 作为样本。

### P2 — M5 runbook 缺少告警送达验收（已修）

- 证据：`docs/ops_runbook.md` 只要求手工运行 `bash scripts/weekly_healthcheck.sh` 并记录 incident。
- 证据：`rg ALERT|notification|osascript|flag` 未发现健康检查失败写 flag、通知、恢复清 flag 的机制。
- 影响：当前可以证明“人手动跑会失败”，不能证明“无人值守失败会到达人”。
- 修复：新增 `scripts/weekly_healthcheck_alert_wrapper.sh`；失败写 `/tmp/gaozhong_ALERT_weekly_healthcheck.flag`，成功自动清 flag；`docs/ops_runbook.md` 已改为默认使用 wrapper。

### P2 — 运行时写 DuckDB 缺少中心化写窗口（已修）

- 证据：`backend/api/main.py` 使用 `ThreadingHTTPServer`；`backend/api/routes/students.py` 的导入/重算、`backend/api/routes/scan_upload.py` 的上传写入均直接打开 DuckDB 写连接。
- 影响：M5 巡检和真实上传/导入并发时，DuckDB 单 writer 约束可能造成锁冲突或间歇失败。
- 当前状态：本轮审计未触发并发写；DB 只读摘要 PASS。
- 修复：新增 `backend.api.db.db_write()`，通过本地文件锁串行化运行时 DuckDB 写连接；学生导入、弱点重算、扫描上传写入已接入该 helper；`docs/ops_runbook.md` 已记录写窗口规则。

### P3 — manifest/派生产物仍有潜在漂移点

- 证据：`backend/orchestrator/load.py` 第 88~99 行使用 `rglob("*")` 生成 `file_manifest`；`scripts/build_manifest.py` 第 67、85、108 行为每行写入当前 `fetched_at`。
- 当前反证：`git ls-files --others --exclude-standard data/textbooks data/curriculum data/structured data/external` 返回 0，当前没有未跟踪输入混入 manifest。
- 影响：当前不是阻塞项，但后续若输入目录出现未跟踪文件或频繁重跑 manifest，会产生噪音和证据漂移。
- 建议：派生产物扫描时优先使用 tracked 输入清单或显式 allowlist；时间戳放在 report-level metadata，避免每行必然变化。

### P3 — curl 不存在时 API 检查会被跳过为成功

- 证据：`scripts/weekly_healthcheck.sh` 第 52~54 行、`scripts/m4_m5_smoke.sh` 第 79~80 行只打印 skip，不返回 fail/degraded。
- 影响：缺少 `curl` 的环境会跳过 API smoke，但脚本仍可能整体 PASS。
- 建议：把 `curl unavailable` 分类为 `FAIL` 或明确 `DEGRADED` 且非零退出；也可改用 Python stdlib `urllib` 免依赖。

## Passing Evidence

- D0：`scripts/data_accuracy_check.py` 覆盖 manifest、词集、语法、课程讲义、图谱、audit findings、题库、placement、听力/写作和 enriched content，结果 PASS。
- DB：`textbooks=14`、`file_manifest=196`、`courses=40`、`course_materials=560`、`course_handouts=40`、`question_bank=700`、`question_tags=12612`、`students=5`、`student_weakness=11`、`audit_findings.OK=44`。
- Moth：`CodeGraph=PASS`、`Complexity=PASS`、`New findings=0`；唯一 WARN 是 `dirty worktree: 99 path(s)`。

## Recommended Next Slice

1. 处理 P3：让 manifest/派生产物区分 tracked 输入、运行级时间戳和动态扫描盲区。
2. 收敛 CodeGraph/Moth 对未跟踪新增脚本和大量周检产物的 dirty worktree 口径。
3. 后续如引入真实定时任务，再把 wrapper flag 接入 SessionStart 或启动检查。

## 2026-06-12 P3 Remediation Closure

P3 scope: manifest / derived artifact drift and CodeGraph/Moth audit posture convergence.

Code changes:
- `scripts/build_manifest.py` now uses git-tracked input scope first, removes per-row `fetched_at` from JSONL manifest rows, and writes run-level metadata to `data/manifest/_manifest_run.json`.
- `backend/orchestrator/load.py` now uses the same tracked-file-first input scope and no longer silently drops manifest load exceptions.

Validation:
- Manifest determinism: PASS, two consecutive manifest builds produced identical hashes for textbook/curriculum/structured JSONL manifests.
- `python3 -m py_compile`: PASS.
- `scripts/api_payload_check.py --port 8765`: PASS after API startup.
- `scripts/data_accuracy_check.py`: PASS.
- `scripts/weekly_healthcheck_alert_wrapper.sh --port 8765`: PASS and alert flag cleared.
- `scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`: PASS.
- `codegraph sync`: exit 0.
- `moth doctor --repo . --format markdown`: exit 0, no issues, Complexity PASS, new findings 0.

Residual:
- Moth status remains WARN because the worktree contains many modified/untracked files and CodeGraph reports stale until tracking/ignore policy is reconciled.
- This is not a functional P3 blocker; it is a repository hygiene / commit-boundary decision.
