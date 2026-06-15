# 运营试运行运行手册（M5）

> 目标：让系统具备可持续、可复现的运营能力（启动、巡检、异常恢复、周报演练）。
>
> 运行口径基线：`run_id=20260610T135344Z`（M4 课程主链路静态复核产物）

## 1) 标准启动（单机）

1. 进入项目目录：`cd /Users/dp/Documents/M/gaozhong`
2. 一次性启动：

```bash
./start.command
```

3. 观察日志：
- 输出日志：`logs/gaozhong-<时间戳>.log`
- 关键服务地址：`http://127.0.0.1:8765/app`

4. 首屏复核（本地）：
- 能打开 `/app`
- 能点击 `#/teaching`、`#/students`、`#/graph`、`#/scan`
- `/api/stats` 有返回 JSON

## 2) 停止与恢复

- 停止服务（保守）：

```bash
pkill -f "backend/api/main.py" || true
```

- 重启服务（按标准启动重跑第 1 步）

## 3) 每日巡检（脚本化执行）

```bash
bash scripts/weekly_healthcheck_alert_wrapper.sh --port 8765
```

要求（每日通过即为合格）：
- `scripts/data_accuracy_check.py` PASS
- `bash scripts/stop_gate.sh` PASS
- `PYTHONPATH=. python3 tests/test_course_smoke.py` PASS
- `scripts/api_payload_check.py` PASS，关键接口必须返回有效 JSON payload（不是仅 HTTP 200）
- 失败时写 `/tmp/gaozhong_ALERT_weekly_healthcheck.flag`；恢复成功后 wrapper 自动清理该 flag

## 4) 问题分级与回退

- P0（阻断）：服务不可用、`data_accuracy_check` FAIL、接口返回 5xx 连续 2 次
- P1（恢复）：课堂主链路某一 API 空返回或超时、课程讲义加载异常
- P2（待观察）：日志告警、个别样本审计告警（非关键字段）
- P2（并发治理）：学生导入、弱点重算、扫描上传等 DuckDB 写 API 通过 `backend.api.db.db_write()` 串行化；巡检和批量写入不应人为并发执行。

处理原则：
- P0/P1 触发时先执行健康回放：`bash scripts/weekly_healthcheck_alert_wrapper.sh --port 8765`
- 仍失败时按 runbook 记录 incident，形成补丁与闭环：
  - 复现步骤
  - 证据路径（日志/截图）
  - 责任人
  - 预计修复时限

## 5) 代码变更与复核前置（M5 约束）

- 任何变更需按 M5 原则先补齐复核，再进入下一项：
  1. 运行 `bash scripts/weekly_healthcheck_alert_wrapper.sh --port 8765`（包含 smoke + audit + 告警 flag 清理）
  2. 更新 `goal.md` 与 `docs/data_accuracy_audit.md` 的里程碑状态
  3. 记录 `run_id`、命令、快照哈希

## 6) 演练记录模板

- 演练日志：`docs/week1_review_round1.md` ... `docs/week34_review_round1.md`
- 每次演练至少包含：
  - 演练时间窗（周次）
  - 参与人
  - 演练场景（教师/学生）
  - 失败点与根因
  - 复盘动作与下一步

## 7) 注意事项（与复核边界）

- M4 复核收尾仍是里程碑边界，不能在未更新复核记录前将 M4 标为完成。
- `verification_protocol` 的 V1/V2/V5/V6/V7 为环节，必须在会话内一次性复核时一次性补齐。
