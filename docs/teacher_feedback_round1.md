# teacher_feedback_round1

- run_id: `20260610T074134Z`
- 当前状态：`代补口（待真人补录）`
- 追踪同步：`data/reports/m3_closure_20260610T074134Z_evidence.jsonl`
- 执行目标：由 1 位英语教师完成至少一轮课程演示（10-20 分钟）并形成书面反馈，确认课程链路是否可直接教学。

## 复核维度（映射到 M3/M4 的可验收项）

- 课程内容可用性（课程 40 节是否可直接用于课堂）→ `goal.md` 的 M4 目标与 R1~R6
- `/app` 与 3 端兼容体验 → 关键验收（V1~V8）与 7-tab 可达性
- 作业和讲义映射正确性 → `audit_homework_alignment` / `course_materials` 一致性
- 弱点 drill 与题目推荐逻辑 → 学生档案 tab 实用性
- 性能与交互 → 5 分钟内切 Tab 无阻塞、页面无阻断性报错

## 教师反馈记录模板（实际收录）

1. 时间与版本：`20260610T074134Z` / 演示场景
2. 参与课程 ID（建议 #11 / #21 / #31）与班级
3. 使用流程：讲解顺序、作业流程、学生互动
4. 发现问题（按严重度：阻塞 / 中高 / 建议）
5. 建议动作（需改动的文案、题目、讲义结构、流程）

## 时间窗与补齐要求

- 建议窗口：本周内完成 1 次真人复核并补齐本文件。
- 若无法按时安排：在 `docs/user_test_round1.md` 写明替代收口原因并提交重排窗口，`data_accuracy_audit.md` 标注延期原因与新窗口，不得直接闭环 `M3`。
- `goal.md` 与 `data/reports/m3_closure_20260610T074134Z.*` 的 `risk/next_action` 必须同步真实补录状态。
- 目标截止：`2026-06-17 18:00` 前完成；超时则改为 `代补口（延期待补）` 并更新三方证据。

## 待完成真实复核清单（本轮未达）

- 课程讲解链路：至少 1 节（建议 #11/#21/#31）完整演示一遍
- 学生体验链路：至少1次课后作业提交与批改
- 弱点闭环：至少一次 `students` tab 的 drill 推送并解释动作
- 图谱联动：至少 1 次 concept 点击触发 popup + 真题展开
- 输出要求：每一项给出「通过/阻塞」判定与一句建议

## 缺口缓解动作（代补）

- 真实教师复核前，以静态链路证据作为代补：
  - `/app` 7-tab 与关键 API 路由在 `docs/app_smoke_round1.md` 中可复核；
  - 讲义/题库/题目索引链路在 `frontend/static/app_router.js` + `course/handout.py` 已映射；
  - `course_materials` 与 `nodes.question` 映射已在 `M2` 产物中闭环。

## 代补记录（本轮）

- `docs/data_accuracy_audit.md` 与 `goal.md` 已声明：`M3` 当前仅支持代补闭环，不得直接完成，待教师复核补录。
- 代补依据（本轮无需等待教师）：  
  - 7-tab 入口与主要路由链路已静态核验：`docs/app_smoke_round1.md`
  - 作业/讲义/图谱等组件已具备可复算入口：`/app` 相关 tab 与后端 API
  - 课程材料映射风险（已在 `M2` 闭环处理）：
    - `course_materials` 与 `nodes.question` 命中率已达 156/156
    - `rule_synth` 与 `analysis` 缺失问题已清零（见 `rule_synth_replacement`）
- 真实验证后续动作：
  - 首选：本周内安排 1 位教师做最小回访（1 轮）
  - 截止窗：`2026-06-17 18:00` 前补齐后方可推进 `M4`


## M3.2 统一映射（V1~V8）

- 目标 run_id：`20260610T074134Z`
- 触发源：`data/reports/verification_protocol.json`（V1~V8 全部 `deferred`）
- 约束：在本文件中每项都需给出 `复核动作 + 结果 + 复验计划 + 责任人 + 时间窗`

| V# | 对应验收项 | 当前状态 | 责任人 | 代补证据 | 下一步闭环动作 |
|---|---|---|---|---|---|
| V1 | 学生摸底测验与推荐匹配 | pending（待真人） | 项目用户侧 | `frontend/static/app_router.js`（学生入口）/ `docs/app_smoke_round1.md` | 安排 1 名学生完成一次流程并记录 10 题推荐复现 |
| V2 | 查看推荐课节 | pending（待真人） | 项目用户侧（教师） | `frontend/static/app_router.js`（`#/teaching`） | 安排教师演示 1 次课节选取与讲义打开 |
| V3 | 上课（讲义可读性） | pending（待真人） | 项目用户侧 | `course/handout.py` + `frontend/static/app_router.js` | 真人跟读 1 节，录入“中断点/不理解点” |
| V4 | 课后测验提交批改 | pending（待真人） | 项目用户侧 | `frontend/static/app_router.js`（quiz 流程） / `frontend/app.js` | 安排 10 题提交路径并导出提交/纠错截图 |
| V5 | 听力闭环 | pending（待真人） | 项目用户侧 | `frontend/static/app_router.js`（qbank/听力） | 1 条听力从播放、逐段作答到结果回填 |
| V6 | 弱点 drill | pending（待真人） | 项目用户侧 | `students` tab + `scripts/tools/audit/homework_alignment` | 触发一次弱点 drill，抽查推荐课节与标签一致性 |
| V7 | 知识图谱弹窗 | pending（待真人） | 项目用户侧 | `frontend/static/graph_popup.js` | 点击 ≥2 个 conceptLink，核验弹窗返回与真题联动 |
| V8 | 打印讲义 | pending（待真人） | 项目用户侧 | `frontend/static/app_router.js:117-123` | 真人点击打印并确认 PDF/打印行为正常 |

### 本轮执行约束

- 目标关闭窗口：`2026-06-17 18:00`（延期需更新 `goal.md` + `docs/data_accuracy_audit.md` 风险条目）。
- 人工复核完成后，需在对应文件内更新 V1~V8 的 `当前状态`：`done / blocked`，并补齐每项闭环证据文件路径。
- 任何一项未闭环，不得推进 `M3.3`。
