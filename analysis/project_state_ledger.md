# gaozhong Project State Ledger

> 仅保留当月+上月条目；每月按项目约定归档。
> 用于承载完成事项、历史状态与证据快照，当前运行契约以 `goal.md` 为准。

## 2026-06-11 — M5 Week39 运营闭环与总指挥审计

- 2026-06-11T07:38:31+08:00（Week39 复盘）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`
  - 结果：全部 PASS（0 FAIL / 0 WARN）；复盘记录：`docs/week39_review_round1.md`
  - 产物日志：`logs/gaozhong-weekly-healthcheck-20260611-153831.log`、`logs/m4_m5_smoke_20260611-153850.log`
- 2026-06-11T07:39:36.801544Z（总指挥工具审计）
  - `moth doctor --repo . --format markdown`：Status `WARN`（仅 `dirty worktree: 81 path(s)`）
  - 业务可回放结论：`issues: none`，`CodeGraph: PASS`，`Complexity: PASS`，`New findings: 0`
  - 说明：存在本会话未提交审计与复核产物，未形成 `FAIL/WARN` 门禁级阻塞。

## 2026-06-11 — M5 Week40 运营闭环持续复核

- 2026-06-11T07:40:12Z（复用脚本 PASS 循环）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-074012.log`、`logs/gaozhong-weekly-healthcheck-20260611-074012.log`、`logs/m4_m5_smoke_20260611-074012.log`、`logs/moth-doctor-20260611-074012.md`
- 本轮复盘：`docs/week40_review_round1.md`

## 2026-06-11 — M5 Week41 运营闭环持续复核

- 2026-06-11T07:42:34Z（继续周检）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-074228.log`、`logs/gaozhong-weekly-healthcheck-20260611-074228.log`、`logs/m4_m5_smoke_20260611-074228.log`、`logs/moth-doctor-20260611-074228.md`
- 本轮复盘：`docs/week41_review_round1.md`

## 2026-06-11 — M5 Week42 运营闭环持续复核

- 2026-06-11T07:44:42Z（总指挥工具审计）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree (83 path(s))`；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-074435.log`、`logs/gaozhong-weekly-healthcheck-20260611-074435.log`、`logs/m4_m5_smoke_20260611-074435.log`、`logs/moth-doctor-20260611-074435.md`
- 本轮复盘：`docs/week42_review_round1.md`

- 2026-06-11T07:47:02Z（文档更新后总指挥复核）
  - 命令：`moth doctor --repo . --format markdown`
  - 结果：`moth` 为 `WARN`，仅 `dirty worktree: 84 path(s)`；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/moth-doctor-20260611-154700.md`

- 2026-06-11T07:48:30Z（Week43 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-154733.log`、`logs/gaozhong-weekly-healthcheck-20260611-154017.log`、`logs/m4_m5_smoke_20260611-154805.log`、`logs/moth-doctor-20260611-154829.md`
- 本轮复盘：`docs/week43_review_round1.md`

## 2026-06-11 — M5 Week44 运营闭环续检

- 2026-06-11T15:51:43+08:00（Week44 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（85 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-155106.log`、`logs/gaozhong-weekly-healthcheck-20260611-155106.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-155111.log`）、`logs/m4_m5_smoke_20260611-155106.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-155127.log`）、`logs/moth-doctor-20260611-155106.md`
- 本轮复盘：`docs/week44_review_round1.md`

## 2026-06-11 — M5 Week45 运营闭环续检

- 2026-06-11T16:02:35+08:00（Week45 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（86 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-160127.log`、`logs/gaozhong-weekly-healthcheck-20260611-160127.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-160135.log`）、`logs/m4_m5_smoke_20260611-160127.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-160207.log`）、`logs/moth-doctor-20260611-160127.md`
- 本轮复盘：`docs/week45_review_round1.md`

## 2026-06-11 — M5 Week46 运营闭环续检

- 2026-06-11T16:06:47+08:00（Week46 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（87 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-160547.log`、`logs/gaozhong-weekly-healthcheck-20260611-160547.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-160557.log`）、`logs/m4_m5_smoke_20260611-160547.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-160626.log`）、`logs/moth-doctor-20260611-160547.md`
- 本轮复盘：`docs/week46_review_round1.md`

## 2026-06-11 — M5 Week47 运营闭环续检

- 2026-06-11T16:10:42+08:00（Week47 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（88 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-160948.log`、`logs/gaozhong-weekly-healthcheck-20260611-160948.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-160957.log`）、`logs/m4_m5_smoke_20260611-160948.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-161022.log`）、`logs/moth-doctor-20260611-160948.md`
- 本轮复盘：`docs/week47_review_round1.md`

## 2026-06-11 — M5 Week48 运营闭环续检

- 2026-06-11T16:14:35+08:00（Week48 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（89 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-161346.log`、`logs/gaozhong-weekly-healthcheck-20260611-161346.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-161353.log`）、`logs/m4_m5_smoke_20260611-161346.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-161417.log`）、`logs/moth-doctor-20260611-161346.md`
- 本轮复盘：`docs/week48_review_round1.md`

## 2026-06-11 — M5 Week49 运营闭环续检

- 2026-06-11T16:18:30+08:00（Week49 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（90 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-161740.log`、`logs/gaozhong-weekly-healthcheck-20260611-161740.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-161747.log`）、`logs/m4_m5_smoke_20260611-161740.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-161812.log`）、`logs/moth-doctor-20260611-161740.md`
- 本轮复盘：`docs/week49_review_round1.md`

## 2026-06-11 — M5 Week50 运营闭环续检

- 2026-06-11T16:22:14+08:00（Week50 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（91 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-162129.log`、`logs/gaozhong-weekly-healthcheck-20260611-162129.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-162136.log`）、`logs/m4_m5_smoke_20260611-162129.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-162158.log`）、`logs/moth-doctor-20260611-162129.md`
- 本轮复盘：`docs/week50_review_round1.md`

## 2026-06-11 — M5 Week51 运营闭环续检

- 2026-06-11T16:26:04+08:00（Week51 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（92 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-162519.log`、`logs/gaozhong-weekly-healthcheck-20260611-162519.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-162525.log`）、`logs/m4_m5_smoke_20260611-162519.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-162548.log`）、`logs/moth-doctor-20260611-162519.md`
- 本轮复盘：`docs/week51_review_round1.md`

## 2026-06-11 — M5 Week52 运营闭环续检

- 2026-06-11T16:30:06+08:00（Week52 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（93 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-162923.log`、`logs/gaozhong-weekly-healthcheck-20260611-162923.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-162929.log`）、`logs/m4_m5_smoke_20260611-162923.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-162951.log`）、`logs/moth-doctor-20260611-162923.md`
- 本轮复盘：`docs/week52_review_round1.md`

## 2026-06-11 — M5 Week53 运营闭环续检

- 2026-06-11T16:33:58+08:00（Week53 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（94 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-163313.log`、`logs/gaozhong-weekly-healthcheck-20260611-163313.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-163320.log`）、`logs/m4_m5_smoke_20260611-163313.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-163343.log`）、`logs/moth-doctor-20260611-163313.md`
- 本轮复盘：`docs/week53_review_round1.md`

## 2026-06-11 — M5 Week54 运营闭环续检

- 2026-06-11T16:37:35+08:00（Week54 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（95 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-163658.log`、`logs/gaozhong-weekly-healthcheck-20260611-163658.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-163703.log`）、`logs/m4_m5_smoke_20260611-163658.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-163720.log`）、`logs/moth-doctor-20260611-163658.md`
- 本轮复盘：`docs/week54_review_round1.md`

## 2026-06-11 — M5 Week55 运营闭环续检

- 2026-06-11T16:40:57+08:00（Week55 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（96 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-164022.log`、`logs/gaozhong-weekly-healthcheck-20260611-164022.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-164027.log`）、`logs/m4_m5_smoke_20260611-164022.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-164042.log`）、`logs/moth-doctor-20260611-164022.md`
- 本轮复盘：`docs/week55_review_round1.md`

## 2026-06-11 — M5 Week56 运营闭环续检

- 2026-06-11T16:44:30+08:00（Week56 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（97 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260611-164355.log`、`logs/gaozhong-weekly-healthcheck-20260611-164355.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260611-164400.log`）、`logs/m4_m5_smoke_20260611-164355.log`（脚本内记录见 `logs/m4_m5_smoke_20260611-164415.log`）、`logs/moth-doctor-20260611-164355.md`
- 本轮复盘：`docs/week56_review_round1.md`

## 2026-06-12 — M5 Week57 运营闭环续检

- 2026-06-12T08:38:06+08:00（Week57 一体化复核）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、`moth doctor --repo . --format markdown`
  - 结果：`data_accuracy_check`、`weekly_healthcheck`、`m4_m5_smoke` 均 PASS；`moth` 结果 `WARN`，仅 `dirty worktree`（98 path(s)）；`issues: none`、`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/data_accuracy_check_20260612-083806.log`、`logs/gaozhong-weekly-healthcheck-20260612-083806.log`（脚本内记录见 `logs/gaozhong-weekly-healthcheck-20260612-083812.log`）、`logs/m4_m5_smoke_20260612-083806.log`（脚本内记录见 `logs/m4_m5_smoke_20260612-083828.log`）、`logs/moth-doctor-20260612-083806.md`
- 本轮复盘：`docs/week57_review_round1.md`

## 2026-06-12 — Mythos 全面审计

- 2026-06-12T08:45:14+08:00（Mythos 方法论项目级审计）
  - 命令：`python3 scripts/data_accuracy_check.py`、`bash scripts/weekly_healthcheck.sh --port 8765`、`bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`、API payload predicate 审计、DuckDB 只读摘要、`moth doctor --repo . --format markdown`
  - 结果：D0、weekly、M4/M5 smoke、DB 摘要、Moth 均可执行；新增 API payload 审计发现 `/api/students/get` 现有 smoke 只看 HTTP 200，会把 `{"error":"missing ?id"}` 判为 PASS。
  - Moth：`WARN`，仅 `dirty worktree`（99 path(s)）；`CodeGraph: PASS`、`Complexity: PASS`、`New findings: 0`
  - 产物：`analysis/mythos_project_audit_20260612.md`
  - 证据日志：`logs/mythos-data-accuracy-20260612-084514.log`、`logs/mythos-weekly-healthcheck-20260612-084514.log`、`logs/mythos-m4-m5-smoke-20260612-084514.log`、`logs/mythos-api-payload-audit-20260612-084514.log`、`logs/mythos-db-summary-20260612-084514.log`、`logs/mythos-moth-doctor-20260612-084514.md`

- 2026-06-12T08:50:37+08:00（Mythos P1 修复 + Week58 复核）
  - 改动：新增 `scripts/api_payload_check.py`；`scripts/weekly_healthcheck.sh` 与 `scripts/m4_m5_smoke.sh` 不再用 `curl -fsS > /dev/null`，改跑 JSON payload gate。
  - 结果：payload gate、D0、weekly、M4/M5 smoke 均 PASS；`/api/students/get` 使用真实样本 `sy-2024-001` 校验 payload。
  - Moth：`WARN`，`dirty worktree: 100 path(s)`；CodeGraph 仍把未跟踪新脚本标为 pending added（`codegraph sync` 已返回 0），`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/api-payload-check-20260612-085037.log`、`logs/data_accuracy_check_20260612-085037.log`、`logs/gaozhong-weekly-healthcheck-20260612-085037.log`、`logs/m4_m5_smoke_20260612-085037.log`、`logs/codegraph-sync-20260612-085218.log`、`logs/moth-doctor-20260612-085218.md`
  - 本轮复盘：`docs/week58_review_round1.md`

- 2026-06-12T08:56:40+08:00（Mythos P2 修复 + Week59 复核）
  - 改动：新增 `scripts/weekly_healthcheck_alert_wrapper.sh`；新增 `backend.api.db.db_write()` 并接入学生导入、弱点重算、扫描上传写路径；`docs/ops_runbook.md` 改为默认使用 wrapper 并记录 DuckDB 写窗口规则。
  - 告警验收：`bash scripts/weekly_healthcheck_alert_wrapper.sh --port 1` 按预期失败并写 `/tmp/gaozhong_ALERT_weekly_healthcheck.flag`；随后 `--port 8765` PASS 并清理 flag。
  - 结果：payload gate、D0、weekly、M4/M5 smoke 均 PASS。
  - Moth：`WARN`，`dirty worktree: 106 path(s)`；CodeGraph 仍提示 pending changes（`codegraph sync` 已返回 0），`Complexity: PASS`、`New findings: 0`
  - 产物日志：`logs/alert-wrapper-fail-20260612-085640.log`、`logs/alert-wrapper-pass-20260612-085640.log`、`logs/api-payload-check-20260612-085640.log`、`logs/data_accuracy_check_20260612-085640.log`、`logs/gaozhong-weekly-healthcheck-20260612-085640.log`、`logs/m4_m5_smoke_20260612-085640.log`、`logs/codegraph-sync-20260612-085810.log`、`logs/moth-doctor-20260612-085810.md`
  - 本轮复盘：`docs/week59_review_round1.md`

## 2026-06-11 — 审计与总指挥纪律对齐复核

- 已补齐 `agent.md` 的通用治理约束，明确：
  - 采用 Codex 总指挥模式（controller/architect/reviewer）；
  - 任何改动后必须执行 `moth doctor`；
  - 对复杂改动/验收继续复核 `codegraph`/复杂度视角，不以 `PASS` 字样替代闭环；
  - 真实字段/内容级别验收优先于端口可达。
- 本次改动后审计：
  - `moth doctor --repo . --format markdown`（2026-06-11T07:36:57.772323Z）→ Status `WARN`，原因仅 `dirty worktree`（80 paths）；
  - `CodeGraph`: `PASS`，`Index up to date: True`；
  - `Complexity`: `PASS`，`New findings: 0`，`high: 80` 继续沿用基线。
  - `moth snapshot --repo . --format json` 与 `issues: []`，同样为 `WARN`，唯一警告仍为 `dirty worktree`。
- 业务门禁复核：
  - `python3 scripts/data_accuracy_check.py` 全部通过（`D0 100%`，`0 FAIL / 0 WARN`）。
- 输出变更与本次审计已体现在本 ledger 与 `agent.md`。

## 2026-06-11 — M5 运营试运行闭环（周检复核与脚本自检）

- 2026-06-11T15:35:51 追加复测：启动 `backend/api/main.py`（8765）后再次执行 `scripts/weekly_healthcheck.sh --port 8765` 与 `scripts/m4_m5_smoke.sh --port 8765`，两套脚本均 `PASS`（含 `api /api/stats` / `/api/course/list` / `/api/students/get` / `/api/scan/list` 与全部课程/复核检查项）。
  - 产物日志: `logs/gaozhong-weekly-healthcheck-20260611-153535.log`, `logs/m4_m5_smoke_20260611-153551.log`

- 通过 `bash scripts/weekly_healthcheck.sh --port 8765` 完成 PASS。
  - 证明命令: `bash scripts/weekly_healthcheck.sh --port 8765`
  - 产物日志: `logs/gaozhong-weekly-healthcheck-20260611-152737.log`
- 通过 `bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765` 完成 PASS。
  - 证明命令: `bash scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765`
  - 产物日志: `logs/m4_m5_smoke_20260611-152753.log`
- 2026-06-11T15:28:52 继续执行 `week38` 复盘演练：`scripts/weekly_healthcheck.sh --port 8765` 与 `scripts/m4_m5_smoke.sh --run-id 20260610T135344Z --port 8765` 均 PASS（课程链路与弱点推荐闭环均可复核）。
  - 产物日志: `logs/gaozhong-weekly-healthcheck-20260611-152837.log`, `logs/m4_m5_smoke_20260611-152852.log`
  - 复盘文档: `docs/week38_review_round1.md`
- `goal.md` 当前里程碑状态保持：M5 进行中（周检序列持续中）。
- moth 健康审计（本项）
  - `moth doctor --repo . --format markdown` 的阻塞原因此前来自 `analysis` 与 `analysis/project_state_ledger.md` 缺失；该条已补齐。
  - 下次复验应以 `moth doctor --repo . --format markdown` 作为 truth source。
- 数据层与接口层复核口径：`course smoke test` / `api /api/stats` / `api /api/course/list` / `api /api/students/get` 均为 PASS。


## 2026-06-11 — M5 工具链清洁（complexity baseline）

- 已补齐 `moth` complexity 基线配置：` .moth/profile.yaml`
  - 新增 `complexity_baseline_path: data/reports/tooling/complexity_baseline.json`
  - `complexity_command` 统一为 `analyze_complexity.py` 输出 JSON 可比对。
- 已生成基线文件：`data/reports/tooling/complexity_baseline.json`
- 复验：`moth doctor --repo . --format markdown`
  - Complexity: `PASS`（Baseline loaded, Diff compared, New findings 0）
  - 仍有 `dirty worktree` 告警（当前会话有大量未提交产物，属于周检与复核快照积累）

## 2026-06-11 — M5 总指挥审计复测（服务启动依赖校验）

- 运行 `moth report --repo . --format markdown` 后仍为 `WARN`，唯一阻塞为 `dirty worktree`（约 80 path，含本轮审计产物与历史复核文件）。
- 进行 `scripts/m4_m5_smoke.sh --port 8765` 与 `scripts/weekly_healthcheck.sh --port 8765` 时先后出现 `api /api/stats` 连接失败（未监听 8765）。
- 结论：失败为环境问题，不是接口逻辑失效；在手动启动服务后通过复测。
- 复测步骤：
  - `nohup python3 backend/api/main.py --host 127.0.0.1 --port 8765 > /tmp/gaozhong-api-8765.log 2>&1 &`
  - `curl -s -o /dev/null http://127.0.0.1:8765/api/stats`
  - `bash scripts/m4_m5_smoke.sh --port 8765`
    - 日志: `logs/m4_m5_smoke_20260611-153331.log`
  - `bash scripts/weekly_healthcheck.sh --port 8765`
    - 日志: `logs/gaozhong-weekly-healthcheck-20260611-153347.log`
- 复测结论：两套脚本全部通过（`data_accuracy_check` / `stop_gate` / `course smoke test` / `api /api/stats` / `/api/course/list` / `/api/students/get` / `/api/scan/list`）。

## 2026-06-12 - Mythos P3 remediation + Week60 review

- Scope: close Mythos P3 manifest drift and audit posture finding.
- Changed manifest generation to tracked-file-first input scope and removed per-row timestamp drift from JSONL manifests.
- Changed manifest DB load to use the same input-scope policy and to fail visibly instead of silently ignoring file errors.
- Evidence: `docs/week60_review_round1.md`, `logs/mythos-p3-validation-20260612-090329.log`, `logs/api-payload-check-20260612-090447.log`, `logs/weekly-healthcheck-wrapper-20260612-090447.log`, `logs/m4-m5-smoke-20260612-090447.log`, `logs/moth-doctor-20260612-090447.md`.
- Result: functional gates PASS; Moth returns WARN only for dirty worktree / CodeGraph stale tracking posture; Complexity PASS with 0 new findings.

## 2026-06-12 - Week61 M0 truth-baseline gate correction

- Scope: Phase 7.12 / M0 truth baseline status correction.
- Changed `scripts/tools/audit/truth_baseline_audit.py` to emit explicit PASS/FAIL status, markdown report, strict non-zero mode, DB/truth target gaps, pollution candidate count, and missing `question_bank` mapping count.
- Ran `python3 scripts/tools/audit/truth_baseline_audit.py --strict`; exit 1 is expected and proves M0 is not closed under current evidence.
- Evidence: `docs/week61_review_round1.md`, `logs/truth-baseline-gate-20260612-091035.log`, `data/reports/truth_baseline_2021_2025.md`, `data/reports/truth_baseline_2021_2025.json`.
- Result: `goal.md` M0 status corrected from completed to open; next work should close 2021/2022 truth-source gaps, pollution candidates, and `question_bank` real mappings before M0 can be restored to done.

### Week61 validation tail

- `python3 scripts/data_accuracy_check.py`: PASS (`logs/data-accuracy-week61-20260612-091134.log`).
- `codegraph sync`: exit 0 (`logs/codegraph-sync-week61-20260612-091134.log`).
- `codegraph affected scripts/tools/audit/truth_baseline_audit.py`: exit 0, no affected test files (`logs/codegraph-affected-week61-20260612-091134.log`).
- `moth doctor --repo . --format markdown`: exit 0, no issues, Complexity PASS/new findings 0; WARN remains dirty worktree + CodeGraph stale (`logs/moth-doctor-week61-20260612-091134.md`).

## 2026-06-12 - Week62 raw truth-source acquisition for 2021/2022

- Scope: Phase A/M0 raw source acquisition before structured import.
- Acquired EOL docx candidates for 2021 and 2022 New Curriculum Paper II English under `data/external/exam_sources/eol/`.
- Extracted docx text to local `.txt` files and recorded SHA-256/source metadata.
- Evidence: `docs/week62_review_round1.md`, `data/external/exam_sources/eol/source_manifest_20260612.json`, `data/reports/raw_exam_source_inventory_20260612.json`, `logs/source-download-eol-20260612-091352.log`.
- Result: 2021 raw text appears complete for question numbers 1-55; 2022 raw text appears to cover written paper 21-65 only and requires separate listening source or explicit target split. No DB import was performed.

### Week62 validation tail

- `python3 scripts/tools/audit/truth_baseline_audit.py --strict`: exit 1 as expected, proving M0 remains open (`logs/truth-baseline-week62-20260612-091549.log`).
- `python3 scripts/data_accuracy_check.py`: PASS (`logs/data-accuracy-week62-20260612-091549.log`).
- `moth doctor --repo . --format markdown`: exit 0, no issues, Complexity PASS/new findings 0; WARN remains dirty worktree + CodeGraph stale (`logs/moth-doctor-week62-20260612-091549.md`).

## 2026-06-12 - Week63 EOL structured draft gate

- Scope: Convert acquired EOL 2021/2022 raw docx text into review-only structured drafts.
- Added `scripts/tools/audit/structure_eol_exam_docx.py`; it preserves observed paper numbers and reference-answer numbers separately and marks all rows `draft_not_import_ready`.
- Generated 2021 draft: 67 rows, 47 keyed, 6 missing stem.
- Generated 2022 draft: 46 rows, 42 keyed, 14 missing stem; source remains written-paper-only.
- Evidence: `docs/week63_review_round1.md`, `data/reports/eol_structured_draft_audit_2021.json`, `data/reports/eol_structured_draft_audit_2022.json`, `logs/eol-structured-draft-rebuild-20260612-091957.log`.
- Result: progress toward M0 truth-source structuring, but no DB import; strict gate should remain FAIL until drafts are review-clean and 2022 listening/source contract is resolved.

### Week63 validation tail

- `py_compile`: PASS for `structure_eol_exam_docx.py` and `truth_baseline_audit.py`.
- `truth_baseline_audit.py --strict`: exit 1 as expected; M0 remains open (`logs/truth-baseline-week63-20260612-092045.log`).
- `data_accuracy_check.py`: PASS (`logs/data-accuracy-week63-20260612-092045.log`).
- `codegraph sync`: exit 0 (`logs/codegraph-sync-week63-20260612-092045.log`).
- `codegraph affected scripts/tools/audit/structure_eol_exam_docx.py`: exit 0, no affected test files (`logs/codegraph-affected-week63-20260612-092045.log`).
- `moth doctor`: exit 0, no issues, Complexity PASS/new findings 0; WARN remains dirty worktree + CodeGraph stale (`logs/moth-doctor-week63-20260612-092045.md`).

## 2026-06-12 - Week64 EOL draft span coverage closure

- Scope: reduce EOL structured draft source-span gaps before any DB import.
- Updated `scripts/tools/audit/structure_eol_exam_docx.py` marker matching for full-width blanks, grammar-fill blanks, and seven-choose-five undotted numbers.
- Rebuilt 2021/2022 drafts; both now have `missing_stem_count=0` and no `参考答案` marker contamination in `stem_preview`.
- Evidence: `docs/week64_review_round1.md`, `data/reports/eol_structured_draft_audit_2021.json`, `data/reports/eol_structured_draft_audit_2022.json`, `logs/eol-structured-draft-week64-20260612-092257.log`.
- Result: source span coverage is closed for review-only drafts; import remains blocked by listening/source-contract and item-level review requirements.

### Week64 validation tail

- `py_compile`: PASS for `structure_eol_exam_docx.py` and `truth_baseline_audit.py`.
- `truth_baseline_audit.py --strict`: exit 1 as expected; M0 remains open (`logs/truth-baseline-week64-20260612-092349.log`).
- `data_accuracy_check.py`: PASS (`logs/data-accuracy-week64-20260612-092349.log`).
- `codegraph sync`: exit 0 (`logs/codegraph-sync-week64-20260612-092349.log`).
- `codegraph affected scripts/tools/audit/structure_eol_exam_docx.py`: exit 0, no affected test files (`logs/codegraph-affected-week64-20260612-092349.log`).
- `moth doctor`: exit 0, no issues, Complexity PASS/new findings 0; WARN remains dirty worktree + CodeGraph stale (`logs/moth-doctor-week64-20260612-092349.md`).

## 2026-06-12 Week65 / First-principles top-level architecture

- Added `docs/top_level_architecture_first_principles.md` as the controller-level architecture contract for modules, data states, and configuration ownership.
- Current historical exam evidence is split by state, not treated as a single completed asset: GAOKAO-Bench 2010-2022 JSONL, GAOKAO-Bench Updates 2023 JSON, 2024/2025 local PDF imports, EOL 2021/2022 docx/text/drafts, and a 2021 listening candidate all exist, but only some are canonical DB rows and none of that alone closes the M0 New Curriculum II strict truth baseline.
- Architecture decision: source acquisition, extraction, import, canonical facts, derived graph, API, frontend, and evidence reports must remain separate contracts. `backend/config/sources.yaml` owns source contracts; services own computation; DuckDB owns canonical facts; reports/docs own evidence.
- Tool observations: `codegraph status .` reported 118 files / 1252 nodes / 2732 edges and stale index; `moth doctor --repo . --format markdown` reported WARN for dirty worktree and stale CodeGraph, no issues, Complexity PASS/new findings 0.
- Next action: register all known historical exam artifacts in `backend/config/sources.yaml`, run source-contract acquisition verification in reuse-existing strict mode, then graduate only clean sources toward structured review and import-ready gates.

## 2026-06-12 Week65b / Historical exam source registry

- Updated `backend/config/sources.yaml` to register known historical exam assets: GAOKAO-Bench 2010-2022, GAOKAO-Bench Updates 2023, suspicious local 2023 PDF candidate, legacy local 2024/2025 sibling-project PDFs, and 2021 Sunedu listening candidate.
- Added `backend/config/exam_paper_contracts.yaml` to keep M0 expected paper coverage outside parser/import code.
- Added `backend/config/import_policies.yaml` to define dry-run-first import readiness and source-state blockers.
- Updated `backend/services/data_sources/registry.py` and `backend/services/data_sources/fetcher.py` so local-only attachments can be verified without pretending they have a download URL.
- Added `docs/week65_review_round1.md` with the source-state interpretation and the known 427-byte 2023 PDF risk.
- No DB import or verification gate was run in this step. Next command when approved: `python3 scripts/tools/data_sources/acquire_external_source.py --reuse-existing --strict`.

## 2026-06-12 Week65c / Read-only import readiness module

- Added `backend/services/imports/readiness.py` as a read-only import readiness checker driven by `backend/config/import_policies.yaml`.
- Added `scripts/tools/imports/dry_run_exam_import.py` as the CLI wrapper for structured JSONL import dry runs.
- Boundary: the module does not connect to DuckDB, allocate question IDs, import rows, or modify canonical tables.
- The checker blocks rows with missing source fields, missing stem/source span, answer-section contamination, draft/not-import-ready status, candidate-only source state, unexplained numbering shifts, or unknown paper type.
- Next validation command when explicitly allowed: `python3 scripts/tools/imports/dry_run_exam_import.py data/external/exam_sources/eol/2021_xgkii_english_eol_structured_draft.jsonl --strict`.

## 2026-06-12 Week65d / Exam paper contract audit

- Added paper-type aliases to `backend/config/exam_paper_contracts.yaml` for the New Curriculum II / New Standard II naming mismatch.
- Added `backend/services/audit/exam_contracts.py`, a read-only DuckDB coverage checker for configured exam paper contracts.
- Added `scripts/tools/audit/exam_paper_contract_audit.py` as a CLI that writes a JSON report and can fail under `--strict`.
- The checker reports both paper-alias-matching rows and any-year rows, making it harder to confuse historical exam presence with M0 item-level contract closure.
- No validation command was run in this step.

## 2026-06-12 Week65e / Source registry consistency audit

- Added `backend/services/audit/source_contracts.py`, a read-only config consistency checker for source registry and paper contracts.
- Added `scripts/tools/audit/source_contract_audit.py` as the CLI wrapper.
- The checker catches unknown contract source references, sources with no attachments, attachments without positive min-bytes gates, docx transforms missing text paths, risky candidate/suspicious source usage, and unreferenced exam/listening sources.
- No validation command was run in this step.

## 2026-06-12 Week65f / M0 gate plan and runbook

- Added `scripts/tools/audit/m0_gate_plan.py`, a non-executing planner that prints the M0 gate sequence as markdown or JSON.
- Added `docs/m0_gate_runbook.md` documenting ordered gate execution, current expected failures, and failure handling.
- The gate sequence is now explicit: source-contract consistency, source acquisition verification, EOL import readiness, paper contract coverage, and strict truth baseline.
- No validation command was run in this step.

## 2026-06-12 Week65g / EOL source lineage fields

- Updated `scripts/tools/audit/structure_eol_exam_docx.py` so future EOL structured draft rows include `source_id`, `source_repo`, `source_sha256`, `source_url`, `source_state`, and `source_span`.
- Updated `backend/services/imports/readiness.py` so `source_span` contributes to the stem/source-text presence check.
- Existing JSONL drafts were not rebuilt and no validation command was run. EOL rows remain not import-ready by review status.

## 2026-06-12 Week65h / EOL extraction service boundary

- Added `backend/services/extraction/exam_eol.py` as the service-level boundary for EOL exam extraction metadata, paths, and required draft fields.
- The actual parser remains in `scripts/tools/audit/structure_eol_exam_docx.py`; no JSONL drafts were rebuilt and no validation command was run.
- Next migration step is to move parser logic into the service and reduce the script to a thin CLI wrapper.

## 2026-06-12 Week65i / EOL metadata single source

- Updated `scripts/tools/audit/structure_eol_exam_docx.py` to reuse `source_metadata(year)` and `draft_paths(year)` from `backend/services/extraction/exam_eol.py`.
- Removed the script-local duplicate EOL metadata dictionary, reducing drift risk for source id, sha256, URL, state, and default paths.
- Parser logic remains in the script; no JSONL drafts were rebuilt and no validation command was run.

## 2026-06-12 Week65j / EOL metadata registry ownership

- Updated `backend/services/extraction/exam_eol.py` to load EOL source metadata from `backend/config/sources.yaml` through the source registry.
- The service keeps only `year -> source_id`; URL, sha256, source state, org, and text path now come from the registry contract.
- No JSONL drafts were rebuilt and no validation command was run.

## 2026-06-12 Week65k / EOL parser service migration

- Moved EOL structured draft parser logic into `backend/services/extraction/exam_eol.py`.
- Replaced `scripts/tools/audit/structure_eol_exam_docx.py` with a thin CLI wrapper that calls the service and writes draft/audit files.
- The extraction service remains read-only with respect to DuckDB. No JSONL drafts were rebuilt and no validation command was run.

## 2026-06-12 Week65l / EOL extraction CLI command surface

- Added `scripts/tools/extraction/build_eol_exam_draft.py` as the preferred EOL structured draft CLI.
- Added `scripts/tools/extraction/__init__.py`.
- Changed `scripts/tools/audit/structure_eol_exam_docx.py` into a backward-compatible wrapper.
- No JSONL drafts were rebuilt and no validation command was run.

## 2026-06-12 Week65m / M0 gate plan includes EOL rebuild

- Updated `scripts/tools/audit/m0_gate_plan.py` and `docs/m0_gate_runbook.md` to include 2021/2022 EOL draft rebuild steps before import-readiness gates.
- The new planned commands use `scripts/tools/extraction/build_eol_exam_draft.py --year 2021` and `--year 2022`.
- No draft rebuild or validation command was run in this step.

## 2026-06-12 Week65n / Import readiness report aggregates

- Updated `backend/services/imports/readiness.py` so readiness reports include `finding_code_counts` and `finding_severity_counts`.
- The blocking logic did not change. No dry-run command was executed and no DB writes occurred.

## 2026-06-12 Week65o / Source state taxonomy

- Added `backend/config/source_states.yaml` to define source state tokens, a legacy `raw_source_acquired` alias, non-importable states, and qualifiers.
- Updated `backend/services/audit/source_contracts.py` to warn when source registry status values lack a known state token.
- No audit command was run and no DB writes occurred.

## 2026-06-12 Week65p / Import readiness enforces source state

- Updated `backend/config/import_policies.yaml` so `source_state` is required for exam truth-source imports.
- Updated `backend/services/imports/readiness.py` so rows are blocked when their source state does not satisfy the policy `required_source_state`.
- Added effective blocker code `source_state_below_import_policy`; no dry-run command was run and no DB writes occurred.

## 2026-06-12 Week65q / Shared import policy contract reader

- Added `backend/services/contracts/import_policy.py` and `backend/services/contracts/__init__.py` as a shared import-policy reader.
- Updated `backend/services/imports/readiness.py` to use the shared contract reader.
- Updated `backend/services/extraction/exam_eol.py` so required draft fields combine EOL business fields with `exam_truth_source_import.require_source_fields` from config, reducing duplicate lineage field maintenance.
- No validation command was run and no DB writes occurred.

## 2026-06-12 Week65r / EOL draft field coverage audit

- Added `audit_draft_field_coverage` and `read_jsonl` to `backend/services/extraction/exam_eol.py`.
- Added `scripts/tools/audit/eol_draft_field_audit.py` as a read-only JSONL field coverage checker.
- Updated `scripts/tools/audit/m0_gate_plan.py` and `docs/m0_gate_runbook.md` to insert field coverage gates between EOL draft rebuild and import readiness.
- No audit command was run, no JSONL draft was rebuilt, and no DB writes occurred.

## 2026-06-12 Week65s / Source state matching bug fix

- Added `backend/services/contracts/source_state.py` as the shared source-state parser.
- Updated `backend/services/imports/readiness.py` to use state-token matching instead of substring matching for `required_source_state`.
- Updated `backend/services/audit/source_contracts.py` to reuse the shared state parser.
- This fixes the false-positive risk where `structured_draft_not_import_ready` could satisfy `import_ready` by substring. No validation command was run and no DB writes occurred.

## 2026-06-12 Week65t / Nullable source fields in import policy

- Added `nullable_source_fields` to `backend/config/import_policies.yaml` for `observed_question_number` and `reference_answer_number`.
- Updated `backend/services/imports/readiness.py` and `backend/services/extraction/exam_eol.py` to distinguish missing fields from present nullable fields.
- This avoids schema-level false positives for writing prompts and unkeyed listening rows while preserving semantic import blockers. No validation command was run and no DB writes occurred.

## 2026-06-12 Week65u / EOL field audit nullable reporting

- Updated `backend/services/extraction/exam_eol.py` so EOL draft field coverage reports distinguish nullable fields, absent required fields, and empty non-nullable fields.
- The change improves report interpretation only; no audit command was run, no JSONL draft was rebuilt, and no DB writes occurred.

## 2026-06-12 Week65v / EOL field audit CLI summary

- Updated `scripts/tools/audit/eol_draft_field_audit.py` to print top missing fields in CLI output.
- This is a usability improvement only; no audit command was run and no DB writes occurred.

## 2026-06-12 Week65w / Source contract audit matched state report

- Updated `backend/services/audit/source_contracts.py` so source-contract audit reports include `source_states` with raw status, matched state token, and risky flag for each source.
- This improves report explainability after the source-state matching fix. No audit command was run and no DB writes occurred.

## 2026-06-12 Week65x / M0 gate sequence config ownership

- Added `backend/config/m0_gates.yaml` as the single source for the M0 gate sequence.
- Updated `scripts/tools/audit/m0_gate_plan.py` to load gate definitions from config rather than hard-coded Python constants.
- No planner or gate command was run and no DB writes occurred.

## 2026-06-12 Week65y / M0 runbook uses gate config

- Updated `docs/m0_gate_runbook.md` so it references `backend/config/m0_gates.yaml` and `scripts/tools/audit/m0_gate_plan.py` instead of duplicating the full gate command table.
- The runbook now focuses on execution rules, failure handling, and current known blockers. No planner/gate command was run.

## 2026-06-12 Week65z / M0 gate planner config validation

- Updated `scripts/tools/audit/m0_gate_plan.py` to validate `backend/config/m0_gates.yaml` before rendering plans.
- Validation checks non-empty gate list, contiguous orders from 1, unique names, and required non-empty fields.
- No planner/gate command was run and no DB writes occurred.

## 2026-06-12 Week65aa / M0 gate planner boolean flag validation

- Updated `scripts/tools/audit/m0_gate_plan.py` to validate that `writes_db` and `executes_external_fetch` are YAML booleans for every configured gate.
- No planner/gate command was run and no DB writes occurred.

## 2026-06-12 Week65ab / M0 gate planner fetch-flag consistency

- Updated `scripts/tools/audit/m0_gate_plan.py` to require `executes_external_fetch=true` when an `acquire_external_source.py` command omits `--reuse-existing`.
- Current configured acquisition verification remains local-only because it uses `--reuse-existing --strict`. No planner/gate command was run.

## 2026-06-12 Week65ac / M0 gate artifact write flag

- Added `writes_artifacts` to `backend/config/m0_gates.yaml` so evidence-file writes are distinguished from DuckDB writes.
- Updated `scripts/tools/audit/m0_gate_plan.py` to validate `writes_artifacts` as a YAML boolean.
- No planner/gate command was run and no DB writes occurred.

## 2026-06-12 Week65ad / M0 gate planner risk summary

- Updated `scripts/tools/audit/m0_gate_plan.py` so JSON output includes `risk_summary` with artifact-write, DB-write, and external-fetch gate lists and counts.
- No planner/gate command was run and no DB writes occurred.

## 2026-06-12 Week65ae / M0 gate planner top-level risk booleans

- Updated `scripts/tools/audit/m0_gate_plan.py` so top-level JSON risk booleans are derived from configured gates and stay consistent with `risk_summary`.
- No planner/gate command was run and no DB writes occurred.

## 2026-06-12 Week65af / M0 gate planner markdown risk columns

- Updated `scripts/tools/audit/m0_gate_plan.py` so markdown output includes `Writes artifacts`, `Writes DB`, and `External fetch` columns.
- No planner/gate command was run and no DB writes occurred.

## 2026-06-12 Week65ag / External source inventory gate

- Added `backend/services/audit/external_source_inventory.py` to inventory registered source artifacts and emit findings for missing files, undersized files, outside-project absolute attachments, missing derived text, unknown states, candidate states, and suspicious states.
- Added `scripts/tools/audit/external_source_inventory.py` as the report-writing CLI with `--strict` and `--fail-on-warn`.
- Inserted `external_source_inventory` into `backend/config/m0_gates.yaml` after source-contract consistency and before source acquisition verification.
- No gate was run and no DB write was performed; expected current status remains blocked until 2023 suspicious PDF, 2024/2025 outside-project PDFs, and candidate listening scope are resolved or explicitly re-scoped.

## 2026-06-12 Week65ah / 2024-2025 PDF local mirror

- Mirrored 2024/2025 New Curriculum II English PDF artifacts from the sibling `gaokao` project into `data/external/exam_sources/local_pdfs/`.
- Updated `backend/config/sources.yaml` so `legacy_local_pdf_xgkii_english_2024` and `legacy_local_pdf_xgkii_english_2025` use project-local relative attachment paths while retaining the same sha256 contracts.
- Updated `backend/config/m0_gates.yaml` so `external_source_inventory` no longer lists 2024/2025 outside-project PDF paths as expected blockers.
- No gate was run and no DB write was performed; this only resolves artifact ownership, not item-level D0 truth coverage.

## 2026-06-12 Week65ai / 2023-2024 verified structured seed registry

- Registered `data/gaokao_verified_xgkii_2023_2024.jsonl` as `gaokao_verified_xgkii_2023_2024` in `backend/config/sources.yaml` with sha256 `32d9ae31b9f19fd3d1e5c212312f88bcd617ba9e7202b5ded99f03c12d50e448`.
- Added the source to 2023/2024 `current_known_sources` in `backend/config/exam_paper_contracts.yaml`.
- Recorded that the artifact has 12 rows total, 6 for 2023 and 6 for 2024, so it is partial structured evidence and cannot close item-level M0 coverage.
- No gate was run and no DB write was performed; the 2023 suspicious PDF blocker remains unresolved.

## 2026-06-12 Week65aj / 2023 third-party PDF acquisition

- Replaced the active 2023 suspicious PDF source contract with `third_party_pdf_xgkii_english_2023_zizzs` in `backend/config/sources.yaml`.
- Acquired the PDF through `scripts/tools/data_sources/acquire_external_source.py --source third_party_pdf_xgkii_english_2023_zizzs --output data/reports/external_source_acquisition_2023_zizzs.json --strict`.
- Artifact path: `data/external/exam_sources/third_party_pdfs/2023_xgkii_english_zizzs.pdf`; bytes `194602`; sha256 `c51421c891f7e1344b5e8bb058fbfa57b7fbf3fec4b6d05d1ca7bbcbe0e39eda`.
- Updated `backend/config/exam_paper_contracts.yaml` to reference the new PDF source and record that it still requires EOL/structured-row cross-check before item-level D0 closure.
- Updated `backend/config/m0_gates.yaml` expected inventory blockers; no DB write was performed.

## 2026-06-12 Week65ak / Registry-driven PDF cross-verify gate

- Updated `scripts/tools/audit/cross_verify_pdf.py` so PDF selection is registry-driven through `backend/config/sources.yaml`, with the old 2020 path left only as fallback.
- Added `pdf_cross_verify_2023` to `backend/config/m0_gates.yaml` after source acquisition verification and before EOL draft rebuild gates.
- Updated `scripts/import_recent_exams.py` so 2024/2025 PDF imports use project-local mirrors under `data/external/exam_sources/local_pdfs/` instead of sibling-project absolute paths.
- No gate was run and no DB write was performed.
- Known compatibility risk: older callers importing `PDF_MAP` from `cross_verify_pdf.py` need a compatibility shim or migration to the registry helper.

## 2026-06-12 Week65al / PDF_MAP compatibility shim

- Added `build_pdf_map()` to `scripts/tools/audit/cross_verify_pdf.py`.
- Restored `PDF_MAP = build_pdf_map()` for legacy callers while keeping registry-owned PDF path resolution.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65am / PDF cross-verify strict exit

- Added `--strict` to `scripts/tools/audit/cross_verify_pdf.py`.
- Updated `pdf_cross_verify_2023` in `backend/config/m0_gates.yaml` to use `python3 scripts/tools/audit/cross_verify_pdf.py --year 2023 --strict`.
- Strict mode returns non-zero when any requested year fails or skips; no gate was run and no DB write was performed.

## 2026-06-12 Week65an / 2023 EOL landing page acquisition

- Added `eol_xgkii_english_2023_page` to `backend/config/sources.yaml`.
- Acquired the EOL 2023 landing page through `scripts/tools/data_sources/acquire_external_source.py --source eol_xgkii_english_2023_page --output data/reports/external_source_acquisition_2023_eol_page.json --strict`.
- Artifact path: `data/external/exam_sources/eol/2023_xgkii_english_eol.html`; bytes `167619`; sha256 `acf5ddd6e6be42fbfd39b05304bf0abca2a9997802a9f9cd2e70c30cb04cc140`.
- Added the source to 2023 `current_known_sources` in `backend/config/exam_paper_contracts.yaml`.
- No DB write was performed; this is landing-page/source-lineage evidence only.

## 2026-06-12 Week65ao / EOL HTML identity in PDF cross-verify

- Updated `scripts/tools/audit/cross_verify_pdf.py` to load registered EOL HTML landing-page sources for the target year and emit `html_identity_checks`.
- HTML identity checks require year, English subject, and New Curriculum II marker hits in the local HTML artifact.
- Updated `overall` so PDF/structured text failures or HTML identity failures both produce `FAIL`, which `--strict` turns into non-zero exit.
- Updated `backend/config/m0_gates.yaml` gate purpose/expected status for `pdf_cross_verify_2023`.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65ap / Source cross-check rules config ownership

- Added `backend/config/source_crosscheck_rules.yaml` as the owner of HTML identity required groups.
- Added `backend/services/contracts/source_crosscheck.py` to load source cross-check rules.
- Updated `scripts/tools/audit/cross_verify_pdf.py` to read HTML identity groups by source id and fail closed when a landing-page source lacks rules.
- Updated `backend/services/audit/external_source_inventory.py` so landing-page sources without identity rules emit `landing_page_identity_rule_missing`.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65aq / Cross-check rule consistency audit

- Added `validate_html_identity_rules()` to `backend/services/contracts/source_crosscheck.py`.
- Updated `backend/services/audit/source_contracts.py` so source-contract consistency reports landing-page sources missing identity rules and invalid `source_crosscheck_rules.yaml` entries as BLOCK findings.
- This moves cross-check rule drift detection into the early `source_contract_consistency` gate.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65ar / 2021 listening candidate quarantine

- Moved `sunedu_new_gaokao_i_listening_2021_candidate` out of active `exam_sources` into `quarantined_exam_sources` in `backend/config/sources.yaml`.
- Removed the candidate source from 2021 `current_known_sources` in `backend/config/exam_paper_contracts.yaml`.
- Updated `backend/config/m0_gates.yaml` expected source inventory status so active candidate listening source is no longer listed as the blocker.
- No gate was run and no DB write was performed; EOL 2021 listening rows still require keying/review before import readiness.

## 2026-06-12 Week65as / Quarantined source reference guard

- Updated `backend/services/audit/source_contracts.py` to read `quarantined_exam_sources` from `backend/config/sources.yaml`.
- Added BLOCK finding `contract_references_quarantined_source` when a paper contract references a quarantined source id.
- Added BLOCK finding `source_id_active_and_quarantined` when a source id appears in both active and quarantined sections.
- Added `quarantined_sources` to the audit summary.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65at / EOL review backlog gate

- Added `backend/config/eol_review_rules.yaml` to own EOL draft review backlog rules.
- Added `backend/services/audit/eol_review_backlog.py` and `scripts/tools/audit/eol_review_backlog.py`.
- Inserted `eol_2021_review_backlog` and `eol_2022_review_backlog` into `backend/config/m0_gates.yaml` after EOL field audits and before import-readiness dry-runs.
- The backlog gate reports unresolved item-level review issues such as blocking review statuses, missing source spans, missing required answers, and unkeyed listening answers.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65au / EOL review rule consistency audit

- Added `backend/services/contracts/eol_review.py` with `load_eol_review_rules()` and `validate_eol_review_rules()`.
- Updated `backend/services/audit/eol_review_backlog.py` to use the shared contracts loader.
- Updated `backend/services/audit/source_contracts.py` so source-contract consistency reports invalid EOL review-rule config as BLOCK findings.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65av / EOL review decision overlay contract

- Added `backend/config/eol_review_decisions.yaml` to define the decision overlay contract for EOL draft review.
- Added `backend/services/contracts/eol_review_decisions.py` for loading, validating, keying, and applying review decisions.
- Updated `backend/services/audit/eol_review_backlog.py` to read default per-year decision JSONL files, validate decisions, apply overlays, and include decision statistics/findings in reports.
- Updated `scripts/tools/audit/eol_review_backlog.py` with `--decisions` and decision-count summary fields.
- Updated `backend/services/audit/source_contracts.py` so source-contract consistency validates the decision contract config.
- No gate was run and no DB write was performed.

## 2026-06-12 Week65aw / EOL review worksheet generator

- Added `backend/services/audit/eol_review_worksheet.py` to build reviewer worksheet rows from unresolved EOL review backlog items.
- Added `scripts/tools/audit/eol_review_worksheet.py` CLI that writes worksheet JSONL and a manifest under `data/reports/` by default.
- The worksheet is separate from official review decision files and does not mutate generated drafts or write DB rows.
- No tool/gate was run.

## 2026-06-12 Week65ax / EOL review decision materializer

- Added `backend/services/audit/eol_review_decision_materialize.py` to convert completed worksheet rows into official EOL review decision JSONL rows using the existing decision contract validator.
- Added `scripts/tools/audit/eol_review_decision_materialize.py` CLI.
- The CLI writes a manifest and only writes the decision JSONL when validation passes; it fails on empty completed rows unless `--allow-empty` and on existing output unless `--overwrite`.
- No tool/gate was run and no DB write was performed.

## 2026-06-12 Week65ay / EOL review worksheet stable-key alignment

- Updated `backend/services/audit/eol_review_backlog.py` so backlog identities include `paper_type` and `observed_question_number` separately from compatibility `question_number`.
- Updated `backend/services/audit/eol_review_worksheet.py` so worksheet rows use `observed_question_number` from backlog identity.
- This aligns worksheet row keys with the review-decision stable key contract.
- No tool/gate was run and no DB write was performed.

## 2026-06-12 Week65az / EOL review worksheet shape validation

- Added `worksheet_required_fields` to `backend/config/eol_review_decisions.yaml`.
- Added `validate_worksheet_rows()` to `backend/services/contracts/eol_review_decisions.py`.
- Updated `backend/services/audit/eol_review_decision_materialize.py` so worksheet shape findings block official decision output.
- No tool/gate was run and no DB write was performed.

## 2026-06-12 Week65ba / EOL review materializer year and output guards

- Updated `backend/services/contracts/eol_review_decisions.py` so worksheet validation can enforce an expected year and emit `review_worksheet_year_mismatch`.
- Updated `backend/services/audit/eol_review_decision_materialize.py` to pass expected year and to report `decision_output_exists` before writing unless overwrite is requested.
- Updated `scripts/tools/audit/eol_review_decision_materialize.py` to pass `--overwrite` into the service-layer report generation.
- No tool/gate was run and no DB write was performed.

## 2026-06-12 Week65bb / Non-import-ready decision blocking rule

- Updated `backend/config/eol_review_rules.yaml` so `blocking_review_status_tokens` includes `review_decision_`.
- This makes non-`import_ready` decision overlays such as `needs_followup`, `rejected`, and `rescope` remain backlog blockers.
- No gate/tool was run and no DB write was performed.

## 2026-06-12 Week65bc / EOL review decision coverage audit

- Added `unmatched_review_decision_key` to `backend/config/eol_review_rules.yaml` and known EOL review issue codes.
- Updated `backend/services/audit/eol_review_backlog.py` so unmatched official review decisions become backlog issues.
- Added `backend/services/audit/eol_review_decision_coverage.py` and `scripts/tools/audit/eol_review_decision_coverage.py`.
- The coverage audit reports matched decisions, unmatched decisions, undecided draft rows, decision findings, and remaining backlog count.
- No tool/gate was run and no DB write was performed.

## 2026-06-12 Week65bd / EOL review decision coverage gates

- Inserted `eol_2021_review_decision_coverage` and `eol_2022_review_decision_coverage` into `backend/config/m0_gates.yaml`.
- Coverage gates run after EOL field audits and before EOL review backlog gates.
- Shifted downstream gate order numbers through `truth_baseline_strict`.
- No gate was run and no DB write was performed.

### 2026-06-12 - Mythos lessons absorbed
- Source: Claude root `mythos` skill, previously read directly from `/Users/dp/.claude/skills/mythos/SKILL.md`.
- Project rule update: `/Users/dp/Documents/M/gaozhong/agent.md` gained an additional Mythos absorption section covering evidence quality, source probing, PIT reasoning, DuckDB concurrency, hook diagnosis, external sync classification, experiment exit criteria, derived artifact reproducibility, and remediation closure.
- Validation status: not run by design for this documentation-only update; no M0/Moth/CodeGraph gate executed and no DuckDB write performed.

## 2026-06-12 Week65be / EOL review decision coverage CLI evidence

- Updated `scripts/tools/audit/eol_review_decision_coverage.py` so its console summary includes `decision_path_exists` and total `findings`.
- Reason: the service report already emits `review_decision_file_missing`; stdout now makes missing official decision files distinguishable from empty decision files during strict gate triage.
- Validation status: not run by design; no coverage/backlog/materializer/worksheet command executed and no DuckDB write performed.

## 2026-06-12 Week65bf / Non-import-ready review decision rationale

- Updated `backend/config/eol_review_decisions.yaml` with `non_import_ready_required_fields: [review_note]`.
- Updated `backend/services/contracts/eol_review_decisions.py` so non-`import_ready` official decisions missing `review_note` emit `review_decision_non_import_ready_field_missing`.
- Reason: official decisions that keep an item out of import must remain explainable and auditable, not just syntactically valid.
- Validation status: not run by design; no materializer, coverage, backlog, M0 gate, or DB write executed.

## 2026-06-12 Week65bg / EOL review worksheet contract guidance

- Updated `backend/services/audit/eol_review_worksheet.py` so generated worksheets include a `decision_contract` summary at manifest and row level.
- The summary exposes allowed decision statuses, decision required fields, `import_ready_required_fields`, `non_import_ready_required_fields`, and status guidance.
- Reason: reviewer-facing worksheets should be self-describing and reduce invalid official decision rows before materializer validation.
- Validation status: not run by design; no worksheet, materializer, coverage, backlog, M0 gate, or DB write executed.

## 2026-06-12 Week65bh / Review decision finding taxonomy

- Updated `backend/services/contracts/eol_review.py` to include official review-decision validator findings in `KNOWN_REVIEW_BACKLOG_ISSUE_CODES`.
- Updated `backend/config/eol_review_rules.yaml` so decision duplicate, unmatched, status, required-field, import-ready evidence, and non-import-ready rationale issues are prioritized before item content backlog issues.
- Reason: malformed official decision files should be first-class review backlog blockers, not bucketed as `other`.
- Validation status: not run by design; no source-contract consistency, coverage, backlog, materializer, M0 gate, or DB write executed.

## 2026-06-12 Week65bi / Worksheet partial decision fail-closed guard

- Updated `backend/services/audit/eol_review_decision_materialize.py` to detect worksheet rows that contain reviewer input or changed answer/source fields without `decision_status`.
- Such rows now emit `review_worksheet_partial_decision_missing_status`, count as `partial_rows`, and fail materialization instead of being silently ignored.
- Updated `scripts/tools/audit/eol_review_decision_materialize.py` so CLI output includes `partial_rows` in both fail and pass summaries.
- Validation status: not run by design; no worksheet, materializer, coverage, backlog, M0 gate, or DB write executed.

## 2026-06-12 Week65bj / Materializer missing worksheet guard

- Updated `backend/services/audit/eol_review_decision_materialize.py` so missing worksheet paths emit `review_worksheet_file_missing` and report `worksheet_path_exists` in summary.
- Updated `scripts/tools/audit/eol_review_decision_materialize.py` so CLI output includes `worksheet_path_exists`.
- Reason: missing worksheet files must not be indistinguishable from empty worksheets during official decision materialization triage.
- Validation status: not run by design; no worksheet, materializer, coverage, backlog, M0 gate, or DB write executed.

## 2026-06-12 Week65bk / Materializer output path existence evidence

- Updated `backend/services/audit/eol_review_decision_materialize.py` so reports include `output_path_exists`.
- Updated `scripts/tools/audit/eol_review_decision_materialize.py` so CLI output includes `output_path_exists` in pass/fail summaries.
- Reason: official decision output overwrite protection should be visible in stdout, not only hidden in finding details.
- Validation status: not run by design; no worksheet, materializer, coverage, backlog, M0 gate, or DB write executed.

## 2026-06-12 Week65bl / Materializer issue taxonomy

- Updated `backend/config/eol_review_decisions.yaml` with `materializer_priority_issue_codes`.
- Updated `backend/services/contracts/eol_review_decisions.py` with `KNOWN_MATERIALIZER_ISSUE_CODES` and `eol_review_decision_materializer_issue_unknown` validation.
- Updated `backend/services/audit/eol_review_decision_materialize.py` so materializer reports include `priority_buckets` derived from the decision contract.
- Reason: worksheet/materializer operational failures should be classified separately from EOL backlog content failures.
- Validation status: not run by design; no worksheet, materializer, coverage, backlog, M0 gate, or DB write executed.

## 2026-06-12 Week65bm / 2022 EOL official review decisions batch 1

- Created `data/external/exam_sources/eol/review_decisions/2022_xgkii_english_eol_review_decisions.jsonl` with 20 `import_ready` review decisions for 2022 questions 21-40.
- Evidence source: local EOL source artifact `data/external/exam_sources/eol/2022_xgkii_english_eol.txt`, line 1 reference answer table.
- Corrected the draft overlay for question 33 from `E` to `C` and filled missing answers for questions 38-40 as `E/F/G`.
- Residual scope: 2021 listening rows remain unkeyed; 2022 questions 41-65 and writing prompts still need review decisions or explicit rescope/rejection decisions.
- Validation status: not run by design; no materializer, coverage, backlog, import-readiness, M0 gate, or DuckDB write executed.

## 2026-06-12 Week65bn / 2022 EOL official review decisions batch 2

- Appended 25 `import_ready` review decisions for 2022 questions 41-65 to `data/external/exam_sources/eol/review_decisions/2022_xgkii_english_eol_review_decisions.jsonl`.
- Evidence source: local EOL source artifact `data/external/exam_sources/eol/2022_xgkii_english_eol.txt`, line 1 reference answer table.
- Questions 41-55 use draft stable key `cloze_fill_in_blanks`; questions 56-65 use `grammar_fill`.
- Did not create a writing-prompt decision because the draft row has an empty `observed_question_number`, which would violate the current official decision key contract.
- Residual scope: 2021 listening rows remain unkeyed; 2022 writing prompt needs a stable-key/rescope contract; 2022 official decisions still need coverage/backlog/import-readiness validation.
- Validation status: not run by design; no materializer, coverage, backlog, import-readiness, M0 gate, or DuckDB write executed.

## 2026-06-12 Week65bo / 2022 writing prompt rescope decision

- Added `key_field_fallbacks.observed_question_number.writing_prompt_unanswered = writing_prompt` to `backend/config/eol_review_decisions.yaml`.
- Updated `backend/services/contracts/eol_review_decisions.py` so `decision_key()` can use configured fallback values for missing draft key fields and validates fallback configuration.
- Updated `backend/config/eol_review_rules.yaml` so `review_decision_needs_followup` and `review_decision_rejected` remain blockers while `review_decision_rescope` can clear out-of-current-scope rows when other required fields are present.
- Appended one 2022 writing prompt `rescope` decision to `data/external/exam_sources/eol/review_decisions/2022_xgkii_english_eol_review_decisions.jsonl`.
- Reason: writing prompts are source-linked but outside the current objective-question/import-ready answer overlay; they should not be assigned fake answers or invalid empty stable keys.
- Validation status: not run by design; no source-contract consistency, coverage, backlog, import-readiness, M0 gate, or DuckDB write executed.

## 2026-06-12 Week65bp / 2021 EOL official review decisions batch 1

- Created `data/external/exam_sources/eol/review_decisions/2021_xgkii_english_eol_review_decisions.jsonl`.
- Added 45 `import_ready` decisions for 2021 observed questions 21-65 using local EOL source artifact `data/external/exam_sources/eol/2021_xgkii_english_eol.txt`, line 1 reference answer table.
- Added fallback stable keys for `applied_writing` and `narrative_writing` in `backend/config/eol_review_decisions.yaml`.
- Added 2 `rescope` decisions for 2021 writing sample-answer rows because they are source-linked but outside the current objective-question/import-ready answer overlay scope.
- Critical mapping note: the source table's `reading 1-20` entries map to observed questions 21-40 and must not be used as listening answers for observed questions 1-20.
- Residual scope: 2021 listening questions 1-20 remain unkeyed until an explicit listening answer truth source is found; 2021 decisions still need coverage/backlog/import-readiness validation.
- Validation status: not run by design; no materializer, coverage, backlog, import-readiness, M0 gate, or DuckDB write executed.

## 2026-06-12 Week65bq / 2021 listening candidate source acquisition and decisions

- Added `sohu_shared_new_gaokao_listening_2021_candidate` to `backend/config/sources.yaml` as an acquired candidate shared-listening source.
- Acquired source through `scripts/tools/data_sources/acquire_external_source.py --source sohu_shared_new_gaokao_listening_2021_candidate --output data/reports/external_source_acquisition_2021_sohu_listening.json --strict`.
- Local artifact: `data/external/exam_sources/listening/2021_new_gaokao_listening_sohu.html`, sha256 `6089470a8e3ac4ba7fe2694c13333016af74486ca516a8662b3bd6c9b36021b0`, bytes 35820.
- Appended 20 listening `import_ready` decisions for observed questions 1-20 to `data/external/exam_sources/eol/review_decisions/2021_xgkii_english_eol_review_decisions.jsonl`.
- Answer key used: `1-5 CCBAC`, `6-10 ABABA`, `11-15 CBCAB`, `16-20 ACBCC`, from acquired Sohu candidate page.
- Residual risk: source remains candidate/crosscheck-needed rather than official EOL answer source; later gates or review must confirm prompt match, source status, stable-key coverage, and backlog clearance.
- Validation status: no source-contract consistency, coverage, backlog, import-readiness, Moth, CodeGraph, M0 gate, or DuckDB write executed.

## 2026-06-12 Week65br / Review decision source registry guard

- Updated `backend/config/eol_review_decisions.yaml` with `allowed_decision_source_families` and materializer priority codes for source lookup/family findings.
- Updated `backend/services/contracts/eol_review_decisions.py` so `validate_decisions()` reuses `backend.services.data_sources.registry.load_registry()` and validates any non-empty `source_id` against `backend/config/sources.yaml`.
- New findings: `review_decision_source_unknown` and `review_decision_source_family_disallowed`.
- Reason: official review overlays must not cite ad-hoc or unregistered evidence sources.
- Validation status: not run by design; no source-contract consistency, materializer, coverage, backlog, M0 gate, Moth, CodeGraph, or DuckDB write executed.

## 2026-06-12 Week65bs / M0 closure checkpoint

- Added `docs/M0_CLOSURE_CHECKPOINT_2026-06-12.md` as the durable closure handoff for the current M0 EOL review overlay work.
- The checkpoint lists implemented artifacts, source facts, review decision files, acquisition evidence, required but unrun gates, and residual risks.
- Verdict: partial closure only. The implementation/data overlay phase is substantially closed, but acceptance remains unproven until source-contract, coverage, backlog, import-readiness, Moth/CodeGraph, and relevant M0 gates are authorized and run.
- Validation status: not run by design in this checkpoint; no gate, Moth, CodeGraph, or DuckDB write executed.

## 2026-06-15 / Module-data-config architecture control plane

- Added `AGENTS.md` as the standard Codex entrypoint pointing to `agent.md`, so current Codex policy no longer depends on legacy `CLAUDE.md` discovery.
- Added `docs/README.md` as the current/spec/evidence/legacy document authority index.
- Added machine-readable ownership contract `backend/config/project_architecture.yaml` for instruction sources, truth sources, sibling-project boundaries, module contracts, data zones, config contracts, gate contracts, legacy policy lints, and architecture rules.
- Added loader/audit/CLI chain: `backend/services/contracts/project_architecture.py`, `backend/services/audit/project_architecture.py`, and `scripts/tools/audit/project_architecture_audit.py`.
- Added top-level design note `docs/top_level_module_data_config_architecture_20260615.md` and linked it from `docs/architecture.md`.
- Updated `goal.md`, `.moth/profile.yaml`, and `backend/config/m0_gates.yaml` so new sessions and M0 planning see the architecture control plane first.
- Scope: borrowed reusable patterns from gaokao, LifeHack, and ChunkyMonkey without importing their domain truth or modules; no DuckDB write performed.

---

## 2026-06-15 / 数据诚实性整改 (6 commits)

接手发现"理解→深度整改"链条, 6 commit 闭环真题真值 + 工程纪律:
- `18c01f6` 真题 province/paper_type provenance-aware(假辽宁降级)+ check_21 防回归 + 学情写死改派生(对抗审查 4/4 真修复)
- `4f32fad` 回滚 Phase 7 生成层(删 enriched 讲义40/合成题275/生成练习67/week演练65; question_bank 仅真题; course_handouts 0)— 教材基石不完整不该有生成范文 §1.1
- `fafd3d7` EOL 真题入库: 2021/2022 辽宁新高考全国II卷走 review gate 入 exam_questions(替换 GAOKAO 混合卷占位); exam_questions 376→454
- `4bd83d8` autotag/tests_word 去停用词(config/stopwords.yaml); tests_word 28430→16540
- `d250543` 注册 .moth/assertions/claims.yaml(12 条 claims-vs-reality 弹仓)
- `ea8fd98` 拆 4 个 god-module(verification_protocol/truth_baseline_audit/exam_eol/project_architecture)到 <400; 行为等价证明; run_all 可复现 44 OK(解决 L-S 陈旧快照)

三门: data_accuracy_check exit 0 / moth assert PASS 12 / stop_gate exit 0。
沉淀: gaozhong-ops skill(坑库8) + feedback-tool-first-discovery 记忆 + lessons L-R..V。
下一前沿: 教材基石完整提取(外研选必4 零单元/覆盖46%)→ 趋势模型在干净数据上重建。
