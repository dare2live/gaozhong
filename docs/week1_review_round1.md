# Week1 Review Round1（运营试运行演练）

- run_id（如有）：`20260610T135344Z`
- 负责人：`项目用户侧（Codex）`
- 时间窗：`2026-06-11 09:45~09:50（UTC+8）`

## 1. 演练场景

- 场景：教师端演练 / 学生端演练 / 联合演练
- 参与人：`项目用户侧（Codex）`
- 课程与学员：`课程 #11/#21/#31 + 学生班级`
- 实施时间：`2026-06-11T09:45:59+08:00 ~ 2026-06-11T09:50:18+08:00`
- 结果：通过

## 2. 功能核验清单

- `/app` 启动与路由可达
- `#/teaching` 课程列表与讲义
- `#/students` 弱点推送
- `#/graph` 概念弹窗
- `#/scan` 扫描上传与列表刷新
- `course/service smoke`（`tests/test_course_smoke.py`）
- `data_accuracy_check.py` + `stop_gate.sh`

## 3. 记录

- 问题项：`无`
- 复盘结论：`第一轮运营试运行演练通过：核心链路与接口审计全部通过`
- 处理与复盘动作：`更新 m5_ready，补齐演练记录`
- 证据（日志/截图/录屏）：`logs/gaozhong-weekly-healthcheck-20260611-094559.log`，`logs/m4_m5_smoke_20260611-094618.log`，`docs/ops_runbook.md`，`data/reports/m5_ready_20260610T135344Z.json`

## 4. 结论

- 本周是否进入下一步：`是`
- 阻塞原因（如有）：`无`
- 下一步决定：`进入 M5 持续演练周循环（Week 1/Week 2）`
