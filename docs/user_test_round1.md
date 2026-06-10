# user_test_round1

- run_id: `20260610T074134Z`
- 当前状态：`代补口（待真人补录）` 
- M3 当前阶段结论：`M3.1 审计闭环已完成；M3.2 人工反馈待排期`
- 追踪同步：`data/reports/m3_closure_20260610T074134Z_evidence.jsonl`
- 执行目标：用 1 名高一/高二/高三学生完成一次真实教学流程闭环（登录→选课节→课件/作业→答题→弱点回推），确认关键路径可用。


## M3.2 统一映射（V1~V8）

- 目标 run_id：`20260610T074134Z`
- 触发源：`data/reports/verification_protocol.json`（V1~V8 全部 `deferred`）
- 约束：在本文件中每项都需给出 `复核动作 + 结果 + 复验计划 + 责任人 + 时间窗`
- 交叉对齐证据：`data/reports/m3_closure_20260610T074134Z.md|json`、`data/reports/m3_closure_20260610T074134Z_evidence.jsonl`、`data/reports/verification_protocol.json`、`docs/data_accuracy_audit.md`、`goal.md`

| V# | 对应验收项 | 当前状态 | 责任人 | 代补证据 | 下一步闭环动作 | Evidence File |
|---|---|---|---|---|---|---|
| V1 | 学生摸底测验与推荐匹配 | deferred（待真人） | 项目用户侧 | `frontend/static/app_router.js`（学生入口）/ `docs/app_smoke_round1.md` | 安排 1 名学生完成一次流程并记录 10 题推荐复现 | data/reports/verification_protocol.json |
| V2 | 查看推荐课节 | deferred（待真人） | 项目用户侧（教师） | `frontend/static/app_router.js`（`#/teaching`） | 安排教师演示 1 次课节选取与讲义打开 | data/reports/verification_protocol.json |
| V3 | 上课（讲义可读性） | deferred（待真人） | 项目用户侧 | `course/handout.py` + `frontend/static/app_router.js` | 真人跟读 1 节，录入“中断点/不理解点” | data/reports/verification_protocol.json |
| V4 | 课后测验提交批改 | deferred（待真人） | 项目用户侧 | `frontend/static/app_router.js`（quiz 流程） / `frontend/app.js` | 安排 10 题提交路径并导出提交/纠错截图 | data/reports/verification_protocol.json |
| V5 | 听力闭环 | deferred（待真人） | 项目用户侧 | `frontend/static/app_router.js`（qbank/听力） | 1 条听力从播放、逐段作答到结果回填 | data/reports/verification_protocol.json |
| V6 | 弱点 drill | deferred（待真人） | 项目用户侧 | `students` tab + `scripts/tools/audit/homework_alignment` | 触发一次弱点 drill，抽查推荐课节与标签一致性 | data/reports/verification_protocol.json |
| V7 | 知识图谱弹窗 | deferred（待真人） | 项目用户侧 | `frontend/static/graph_popup.js` | 点击 ≥2 个 conceptLink，核验弹窗返回与真题联动 | data/reports/verification_protocol.json |
| V8 | 打印讲义 | deferred（待真人） | 项目用户侧 | `frontend/static/app_router.js:117-123` | 真人点击打印并确认 PDF/打印行为正常 | data/reports/verification_protocol.json |

### 本轮执行约束

- 目标关闭窗口：`2026-06-17 18:00`（延期需更新 `goal.md` + `docs/data_accuracy_audit.md` 风险条目）。
- 人工复核完成后，需在对应文件内更新 V1~V8 的 `当前状态`：`done / blocked`，并补齐每项闭环证据文件路径。
- 任何一项未闭环，不得推进 `M3.3`。


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
