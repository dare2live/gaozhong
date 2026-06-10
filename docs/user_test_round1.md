# user_test_round1

- run_id: `20260610T074134Z`
- 当前状态：`代补口（待真人补录）`
- 执行目标：用 1 名高一/高二/高三学生完成一次真实教学流程闭环（登录→选课节→课件/作业→答题→弱点回推），确认关键路径可用。

## 真实验收清单

1. 准备：使用 `start.command` 在本机启动服务并打开 `/app`。
2. 登录与切换：进入 `#/teaching`，选择任一课程（建议 #11/#21/#31）检查讲义与作业加载。
3. 学习流程：
   - 执行课程 120 分钟流程中的至少 1 个核心步骤。
   - 完成课后作业前 3 题（至少一次提交/纠错路径）。
   - 打开学生端/学生档案查看一次弱点图谱。
4. 数据闭环：确认 `question_bank` 与 `course_materials` 在该节课程中可追踪（课程页、题号、知识点）。
5. 反馈产出：记录 5~8 条可操作反馈（卡住点、理解问题、文案/交互问题、速度问题）。

## 本轮计划（待安排）

- 本轮已固定为“代补闭环”：静态链路与日志采集已完成。
- 待补录（真人）：需在 `2026-06-17 18:00` 前完成 1 次 30~45 分钟复核会：
  - 责任人：项目用户侧（教学对口人）统筹，研发侧提供会前环境确认。
  - 时间窗：每周内优先 2 个备选时段（任选一）
    - 周内 14:00–17:00
    - 周内 19:00–22:00
  - 补录要求：记录 `session_id / 参与者角色 / 出现阻塞点 / 真实反馈摘要 / 修订建议`。

## 快速替代方案（本轮不安排真人时的收口）

 - 代补期间必须补齐的替代记录（`/app` 仍未真人复核时）：
  - `docs/teacher_feedback_round1.md` 录入系统内测记录：
    - `/app` 入口、7 tab 切换日志
    - 关键组件加载耗时与错误日志片段
    - 自动打分失败/空反馈与改进动作
  - 本文件、`docs/teacher_feedback_round1.md`、`data/reports/verification_protocol.json` 必须三方一致：
    - 负责人
    - 真实复核窗口
    - 未完成项与下次动作
- 必须写入：`goal.md`、`docs/data_accuracy_audit.md`、`data/reports/m3_closure_20260610T074134Z.*`

> 目标：`M3` 允许在真实反馈未完成时先做闭环代录，但最终进入 `M4` 前必须补齐真实验收。

## 已录入代补结论（本轮）

- 实体验收状态：`代补闭环完成（真实用户验收待安排）`
- 证据链补齐：
  - `/app` 7-tab 与关键路由核验：`docs/app_smoke_round1.md`
  - 打印链路证据：`frontend/static/app_router.js:117-123`（`window.print()`）
  - 课程与题库引用一致性：`scripts/tools/audit/rule_synth_replacement.py` + `M2` 产物
- 变更映射：
  - `data/reports/m3_closure_20260610T074134Z.md|json`
  - `docs/data_accuracy_audit.md`
  - `data/reports/verification_protocol.json`
- 本文件剩余动作：
- 预排真人复核窗口：`2026-06-17 18:00` 前需补齐；超期必须在 `goal.md` 与 `docs/data_accuracy_audit.md` 写清延期原因和新窗口。
- 未完成真实复核前，`goal.md` 的 `M3` 状态不得从 `进行中` 直接改为 `已完成`。
