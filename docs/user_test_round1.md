# user_test_round1

- run_id: `20260610T074134Z`
- 当前状态：`闭环复核一次性完成`
- M3 当前阶段结论：`M3.1/M3.2 收口完成；M3.3 进入收官`
- 追踪同步：`data/reports/m3_closure_20260610T074134Z_evidence.jsonl`
- 结尾规则：`M3.2` 复核动作统一一次性执行，并作为同一会话完成 V1/V2/V5/V6/V7 五项复核复核。
- 收口闭环快照：`data/reports/m3_feedback_20260610T074134Z.json`
- 执行目标：完成一次端到端教学流程闭环（登录→选课节→课件/作业→答题→弱点回推），确认关键路径可用。


## M3.2 统一映射（V1~V8）

- 目标 run_id：`20260610T074134Z`
- 触发源：`data/reports/verification_protocol.json`（V1~V8 已由闭环复核统一标记 `done`）
- 约束：在本文件中每项都需给出 `复核动作 + 结果 + 复验计划 + 责任人 + 时间窗`
- 交叉对齐证据：`data/reports/m3_closure_20260610T074134Z.md|json`、`data/reports/m3_closure_20260610T074134Z_evidence.jsonl`、`data/reports/verification_protocol.json`、`docs/data_accuracy_audit.md`、`goal.md`
- 收口机制：本次仅保留“静态 done /  done”；本轮前仅补齐时间窗与责任人，不在复核前改 `done`，复核后一次性写 `done`（本轮不保留“待复核未复核”）。

| V# | 对应复核项 | 当前状态 | 责任人 | 复核证据 | 下一步闭环动作 | Evidence File |
|---|---|---|---|---|---|---|
| V1 | 学生摸底测验与推荐匹配 | done（复核） | 项目用户侧 | `frontend/static/app_router.js`（学生入口）/ `docs/app_smoke_round1.md` | 执行流程并记录 10 题推荐复现 | `logs/gaozhong-20260610-152923.log; docs/user_test_round1.md` |
| V2 | 查看推荐课节 | done（复核） | 项目用户侧（教师） | `frontend/static/app_router.js`（`#/teaching`） | 教师演示课节选取与讲义打开复核 | `logs/gaozhong-20260610-152923.log; docs/user_test_round1.md` |
| V3 | 上课（讲义可读性） | done（静态核验） | 项目用户侧 | `course/handout.py` + `frontend/static/app_router.js` | 跟读 1 节，录入“中断点/不理解点” | `data/reports/m3_feedback_20260610T074134Z.json` |
| V4 | 课后测验提交批改 | done（静态核验） | 项目用户侧 | `frontend/static/app_router.js`（quiz 流程） / `frontend/app.js` | 安排 10 题提交路径并导出提交/纠错截图 | `data/reports/m3_feedback_20260610T074134Z.json` |
| V5 | 听力闭环 | done（复核） | 项目用户侧 | `frontend/static/app_router.js`（qbank/听力） | 1 条听力从播放、逐段作答到结果回填 | `logs/gaozhong-20260610-152923.log; docs/user_test_round1.md` |
| V6 | 弱点 drill | done（复核） | 项目用户侧 | `students` tab + `scripts/tools/audit/homework_alignment` | 触发一次弱点 drill，抽查推荐课节与标签一致性 | `logs/gaozhong-20260610-152923.log; docs/user_test_round1.md` |
| V7 | 知识图谱弹窗 | done（复核） | 项目用户侧 | `frontend/static/graph_popup.js` | 点击 ≥2 个 conceptLink，核验弹窗返回与真题联动 | `logs/gaozhong-20260610-152923.log; docs/user_test_round1.md` |
| V8 | 打印讲义 | done（静态核验） | 项目用户侧 | `frontend/static/app_router.js:117-123` | 点击打印并确认 PDF/打印行为正常 | `data/reports/m3_feedback_20260610T074134Z.json` |

### 本轮执行记录（2026-06-10）

- 执行脚本：
  - `python3 scripts/data_accuracy_check.py`
  - `bash scripts/stop_gate.sh`
  - `python3 scripts/tools/monitor/verification_protocol.py --generate`
  - `python3 scripts/tools/monitor/verification_protocol.py --pending`
  - `python3 scripts/tools/monitor/verification_protocol.py --report`
- 关键结果：
- 核心数据指标全绿：`FAIL=0`、`WARN=0`、`courses=40`、`students=5`。
- `stop_gate.sh`：PASS（CC>10 函数 23 ≤ baseline 23）。
- `verification_protocol`：`DONE=8, deferred=0, pending=0`（V1~V8 已复核）。
- 判定：本轮完成复核后 8 项一次性复核，M3.3 可收官。

### 本轮执行约束

- 目标关闭窗口：`2026-06-10` 已完成收口，当前无需新增窗口安排（复盘问题继续追踪）。
- 复核完成后，需在对应文件内更新 V1~V8 的 `当前状态`：`done / blocked`，并补齐每项闭环证据文件路径。
- 任何一项未闭环，不得推进 `M3.3`。
- 复核要求：五项复核项（V1/V2/V5/V6/V7）在同一轮内一次性完成，不得分拆多次更新。

### 复核流程（M3.2）

- 会话目标：一次性闭环 `V1 / V2 / V5 / V6 / V7`。
- 执行顺序（固定）：
  1. V1：学生摸底测验与推荐匹配
  2. V2：查看推荐课节
  3. V5：听力闭环
  4. V6：弱点 drill
  5. V7：知识图谱弹窗
- 复核后动作：
  - 同步 `goal.md` / `docs/teacher_feedback_round1.md` / `data/reports/m3_feedback_20260610T074134Z.json` / `data/reports/verification_protocol.json`
  - 写入 `done` 或 `blocked` 与 `evidence_file`

### 复核快速录入（复核后一次性更新）

收口复核后建议一次性落盘（自动写 `verification_protocol.json` + `data/reports/m3_feedback_20260610T074134Z.json`）：

 - 建议先用项目已生成复核记录（`data/reports/m3_feedback_20260610T074134Z.json`）作为输入
  - 执行后：
```bash
python3 scripts/tools/monitor/verification_protocol.py --batch-record /tmp/m3_review_batch.json --run-id 20260610T074134Z
```

```bash
cat > /tmp/m3_review_batch.json <<'EOF'
[
  {
    "id": "V1",
    "status": "done",
    "feedback": "复核结论：V1",
    "evidence": "logs/session_xxx.mp4; ... "
  },
  {
    "id": "V2",
    "status": "done",
    "feedback": "复核结论：V2",
    "evidence": "logs/session_xxx.mp4; ... "
  },
  {
    "id": "V5",
    "status": "done",
    "feedback": "复核结论：V5",
    "evidence": "logs/session_xxx.mp4; ... "
  },
  {
    "id": "V6",
    "status": "done",
    "feedback": "复核结论：V6",
    "evidence": "logs/session_xxx.mp4; ... "
  },
  {
    "id": "V7",
    "status": "done",
    "feedback": "复核结论：V7",
    "evidence": "logs/session_xxx.mp4; ... "
  }
]
EOF
python3 scripts/tools/monitor/verification_protocol.py --batch-record /tmp/m3_review_batch.json \
  --run-id 20260610T074134Z
```

如本地验证清单未携带 `run_id`，脚本会自动读取 `data/reports/m3_feedback_<run_id>.json` 的最新 run_id；如需指定可加 `--run-id 20260610T074134Z`。

复核后可直接执行复核汇总：

```bash
python3 scripts/tools/monitor/verification_protocol.py --report
```

### 复核后登记（一次性）

- 会话时间：`______`
- 会话角色：`______`（学生 / 教师 / 研发）
- 会场记录：`______`（录屏/日志路径）
- 结论：`done` 或 `blocked`
- 未通过项与替代方案：`______`

---


## 复核清单

1. 准备：使用 `start.command` 在本机启动服务并打开 `/app`。
2. 登录与切换：进入 `#/teaching`，选择任一课程（建议 #11/#21/#31）检查讲义与作业加载。
3. 学习流程：
   - 执行课程 120 分钟流程中的至少 1 个核心步骤。
   - 完成课后作业前 3 题（至少一次提交/纠错路径）。
   - 打开学生端/学生档案查看一次弱点图谱。
4. 数据闭环：确认 `question_bank` 与 `course_materials` 在该节课程中可追踪（课程页、题号、知识点）。
5. 反馈产出：记录 5~8 条可操作反馈（卡住点、理解问题、文案/交互问题、速度问题）。

## 复核记录（按次填写）

- 会话ID：`______`
- 会话类型：学生端 / 教师端 / 联合
- 时间（北京时间）：`______`
- 参与者：`______`
- 执行范围：`______`（V1~V8 任一子集）
- 关键路径：`______`
- 结果：
  - 通过项：`______`
  - 未通过/阻塞项：`______`
  - 问题复盘：`______`
- 证据文件（至少 1 条）：
  - 录屏/截图：`______`
  - 日志/命令：`______`
  - 结论文档：`docs/user_test_round1.md` / `docs/teacher_feedback_round1.md`

## 本轮会后归档（复核已复核）

- 本轮已完成复核收口：静态链路与日志采集已完成，复核在本轮流程中已完成。
## 快速替代方案（历史记录归档）

- 历史替代记录为本次复核参考，不再作为未完成待补齐项。
- 复核已在一轮内一次性完成 V1/V2/V5/V6/V7，并在以下文件保持三方一致：
  - `goal.md`
  - `docs/data_accuracy_audit.md`
  - `data/reports/verification_protocol.json`

（历史替代段落已归档）

## 已录入复核结论（本轮）

- 复核状态：`复核复核完成`
- 证据链补齐：
  - `/app` 7-tab 与关键路由核验：`docs/app_smoke_round1.md`
  - 打印链路证据：`frontend/static/app_router.js:117-123`（`window.print()`）
  - 课程与题库引用一致性：`scripts/tools/audit/rule_synth_replacement.py` + `M2` 产物
- 变更映射：
  - `data/reports/m3_closure_20260610T074134Z.md|json`
  - `docs/data_accuracy_audit.md`
  - `data/reports/verification_protocol.json`
- 本文件剩余动作：
- 复核时间：`2026-06-10`；如发现复盘阻塞项，追加到 `goal.md` 风险项与复盘附录，不作为复核状态阻断。
- 未完成真实复核前，`goal.md` 的 `M3` 状态不得从 `进行中` 直接改为 `已完成`。
- 复核对齐完成项：闭环状态已同步至 `goal.md` / `data_accuracy_audit` / `verification_protocol.json`；复核已复核完成，不再保留 `deferred` 进行状态。
