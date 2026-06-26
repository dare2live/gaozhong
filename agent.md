# AGENT Guide: gaozhong

## Mission
- Primary product: backend+frontend bilingual/English education platform for curriculum materials, question banks, exams, placements, recommendations, concept-graph exploration, and usage analytics.
- Primary outcome: correctness of data pipeline, API stability, and explicit auditability.
- Delivery rule: 优先做可验证成果（正确结果 > 代码外观），先把真实问题和数据链条闭环，再做结构优化。

## Scope & Boundaries
- Core runtime is in `backend/` and `frontend/static/`.
- Data lifecycle is orchestrated by scripts and services under `scripts/`, `backend/orchestrator/`, `backend/services/`, and persisted in DuckDB (`backend/db/schema.sql`, `data/db/gaozhong.duckdb`).
- 变更优先级：先满足真实用户可见行为与数据完整，再做重构；同一文件/同一数据通路尽量避免并行写入。

## Core Working Rules
- Keep edits minimal and reversible.
- Prefer truth-source-first reasoning before shortcut fixes.
- Any API change should trace to an entrypoint in `backend/api/routes/*` and the affected service in `backend/services/*`.
- Maintain D0 checks from `scripts/data_accuracy_check.py` and related gates at release boundary.
- Use `codegraph` for impact tracing before touching non-trivial service/api paths.
- 不把“已修改代码”当作结束：每一项行为变更都要在可观察结果闭环中验证。
- 根因优先：修复第一处坏掉的数据路径或 join，再补 UI/容错。
- 业务规则优先入配置：阈值、来源优先级、流程开关优先到 `backend/config/*.yaml`；避免在代码里硬编码。
- 并发执行是默认策略：独立只读扫描可并行；同一文件编辑、DB 写入、提交与发布保持串行。

## Controller Mode & Post-Change Audit
- 本项目默认采用 **Codex 总指挥模式**：主对话负责 truth source 选择、目标拆解、风险分类、agent scope 分配、最终 verdict、证据归档和 `goal.md` 状态更新；子代理和工具输出只作为 evidence，不直接替代最终判断。
- 触发架构设计、跨模块整改、多 agent 编排、模糊需求拆解、第一性原理/奥卡姆审查、上线/迁移/长任务前，先使用 `$architect-controller` 思路明确：truth source、边界契约、证伪 gate、注意力分配、最小可逆下一步。
- 改动前：非平凡代码、配置、数据链路、API、前端集成或报告路径变更，先用 `codegraph context "<任务>"` / `codegraph query "<符号>"` 或等效 grep 明确入口、依赖和验证边界；长任务先做 grill gate，确认产出、消费者、前提和成本。
- 改动后：不得只凭“已编辑文件”结束。根据变更面执行最窄真实业务门禁，并补充结构审计：`codegraph affected <changed_files>`（适用时）和 `moth doctor --repo . --format markdown`。若发生 commit/push，则先 `moth sync --repo . --format json` 刷新快照，再跑 `moth doctor --repo . --format markdown`。
- Moth / CodeGraph / Complexity 的角色分工：Moth 是项目级状态总览和 evidence locator；CodeGraph 用于定位依赖与受影响测试；Complexity 是维护风险线索，不替代 D0、API、DB、前端 smoke 或人工业务复核。
- Moth 或复杂度结果与直觉冲突时，先 verify the verifier：检查 repo scope、缓存/stale、未跟踪文件、baseline 是否过时、命令是否扫到正确路径，再决定是否修代码或更新基线。
- 每个自然停顿点都要留下可追溯证据：命令、退出码、关键日志路径、Moth/CodeGraph 结论、剩余风险和下一步写入 `goal.md`、`docs/data_accuracy_audit.md` 或 `analysis/project_state_ledger.md`。
- `agent.md`、`goal.md`、核心 docs、Moth profile、数据审计记录属于共享状态；同一时间只允许一个 controller 负责编辑与验收，避免多个 agent 抢写。

## Borrowed constraints from `chunkymonkey/AGENTS.md`
- 先读 `goal.md`，确认当前目标与优先级，再执行；目标有冲突先更新目标。
- `goal.md` 是 controller board，不要用会话临时日志替代。
- 对非平凡改动先跑 `codegraph status .` 与 `codegraph context / query`；
  结合复杂度评估做变更边界判断。
- 通过前置问题（跑前 grill）确认执行性：
  1) 跑完会产出什么？谁消费？不跑是否可行？
  2) 前提条件（数据、参数、依赖）是否满足？
  3) 成本/收益合理吗？是否有更便宜验证路径？
- 严禁“隐式降级掩盖问题”，优先修复真实源头，不依赖 `try/except: pass`。
- 代码提交与复核要可审计、可回滚，避免无约束 `git add .`。

## Borrowed constraints from `bestchoice/agent.md`
- 实现目标允许调整，但必须留存原因与收益，不允许为了保留旧方案而继续错配用户目标。
- 外部算力默认不默认启用；长作业/高成本动作需用户明确授权与回滚方案。
- 并发可提升前提下要有汇总闭环：不能只看最先完成项，任何失败必须回归修复闭环。
- 必要风险清单要在 `goal.md` 或 `analysis/` 中更新：已验证行为、剩余风险、下一步。

## Borrowed constraints from `lifehack/AGENTS.md`（通用能力）
- 先读项目真相源与规则（`goal.md`、关键架构文档）后再动手；单次改动要有可追溯证据和完成标准。
- 约定先问与后验：
  - Think Before Coding：先确认假设与边界。
  - Simplicity First：优先最小实现，避免未闭环抽象。
  - Surgical Changes：只改必要文件/行，减少副作用面。
  - Goal-Driven Execution：以 requirement-by-requirement 完整闭环为准。
- **Codex 总指挥模式（默认）**：
  - controller/architect/reviewer 由主对话承担；agent 输出只作证据，不直接作最终 verdict。
  - 需要架构设计、模糊需求拆解、多模块编排时，先给出 truth source、边界契约、证伪 gate、行动次序，再分配子任务。
  - 不委托的事项：goal 更新、`goal.md`/`AGENTS` 调整、关键验证结论、最终上线结论、不可逆动作。
- 多 agent 并发必须有清晰边界：互不依赖、互不写同一文件/同一产物；避免关键阻塞项交给后台等待。
- 验证纪律是强制：
  - 测试/审计工具先验真：确认它覆盖当前架构与失败传播；`[PASS]` 不等于完成。
  - 探活（smoke）必须触达真实字段/内容，不以端口、HTTP 200 为充分证据。
  - 每次提交前关注 `git status -sb` 和 evidence 清单，保留可回溯日志与报告。
- 工具总览与使用边界（与本项目工作流一致）：
  - 改造/验收前后跑 `moth doctor --repo . --format markdown` 获取项目级状态。
  - 配套 `moth sync --repo .` 刷新快照与 codegraph 链接，必要时保存 `moth snapshot --repo . --format json` 证据。
  - 非平凡代码/数据路径改动前，用 `codegraph context/query` 识别受影响边界；改后用 `codegraph affected <files>` 做影响确认。
  - `Complexity` 输出是线索，不替代业务真相门禁；冲突时优先 verify verifier（scope/stale/baseline/命令范围）。
- 未知值不能伪装为 0/空值：保留 `unknown` + 待复查动作，避免掩盖缺口。
- 交付与复核：
  - 文档/`goal.md` 更新要有 owner、时间窗、证据路径、复算入口与下一步动作。
  - 允许历史 `deferred`，但当前阶段不得用 `deferred` 代替已闭环项。

## Borrowed constraints from `~/.claude/skills/mythos`（通用能力）
- 探活必须触达真实内容：端口可连、HTTP 200、`ls`/`stat` 成功都不是充分证据；需要读取实际 payload、校验 schema、关键字段、行数和错误分类。
- 空响应和 0 行默认按失败处理：除非业务契约明确允许空集，否则要记录为 `empty/zero-row` 类失败并进入重试、告警或人工复核路径。
- 告警链路必须验收：定时任务、同步任务、监控脚本和 healthcheck 只有在“故意制造失败能看到告警，恢复成功能清理告警”后才算闭环。
- 消灭双真相源：常量、阈值、字段别名、来源清单、数据口径和 UI 文案来源优先收敛到单一配置、schema registry、数据表或服务；复制不可避免时必须有 runtime assert、diff 或审计脚本证明一致。
- 默认值要谨慎：历史默认值、兜底枚举和 `COALESCE` 容易制造第二真相源；未知值用 `NULL/unknown` 和显式待复查状态，不用 0、空数组或演示 fallback 伪装成正常结果。
- DB 审计默认只读：分析和复核用 `read_only=True`，大表先聚合、采样或 `LIMIT`；任何写窗口由 controller 串行管理，并先确认没有后台 writer。
- 测试 fixture 要像真实数据：字段形态、主键样式、时间戳、空值和边界值要能暴露方向性错误；过度抽象的 `A/B/C` fixture 容易让实现和测试一致地错。
- 多 agent 修复要防组间缝隙：并行 scope 必须正交，每组返回 residual/越界项；controller 负责跨组 `rg`、关键 diff、日志和业务门禁复核，不把组内 verifier 当全局 verdict。
- Hook 或 gate 失败先查根因：读取 hook/脚本源码，确认精确关键词、检查范围和退出码；不使用 `--no-verify` 绕过，也不靠反复试提交碰运气。
- 测量优先：性能、数据口径、推荐质量、复杂度风险和“更好方案”的判断先用最小 SQL、抽样、A/B、日志或真实案例量化；阴性结果也要归档为有效产出。
- 数据同步优先 registry 驱动：一个配置条目描述一个数据域的来源、grain、批处理方式、最低行数、SLA、可得性和验收规则；新增数据域优先加配置，不新增漂移的专用脚本。
- 缺口重放用应有集合减实有集合：用课程目录、任务计划、日期清单、manifest 或 schema registry 对照实际表/文件/产物，找漏跑、空洞和截断；失败队列不能替代完整性检查。
- 降级不是普通警告：如果系统继续运行但数据、告警、同步或报告质量 degraded，必须有可见 flag、ledger 记录和下一步 owner，不能只写日志。
- 实验和长任务先预注册判据：跑批前写清成功标准、失败解释、成本上限、消费者和停止条件；结果不支持原假设时同步降级相关方案。
- 时间线证据先核时区与写入机制：引用 DB 状态表、日志、队列或 resolved 行前，先确认时间戳口径和当时写入路径确实执行；状态表是中间证据，不是真相源本身。
- 派生地图/索引/报告只描述可追溯对象：机器生成产物默认只扫描 tracked 或明确输入清单，剔除时间戳等必然波动行，声明动态扫描盲区；机器版负责事实，人工版负责判断，避免两份地图漂移成双真相源。
- 生成型审计产物必须对抗复核：脚本跑通不等于产物正确，至少抽查样例对照真实系统，确认统计口径、依赖边、动态盲区和 WARN/FAIL 分级没有误导。

### Mythos 追加吸收（2026-06-12）
- **macOS / 调度 / TCC 证据要读真内容**：`ls`/`stat`/退出码不等于有权限；涉及系统目录、CloudStorage、LaunchAgent、通知、Cron 时，必须读取实际文件内容或真实 payload。`launchd` 的 TCC 身份跟 `ProgramArguments[0]` 相关；`PATH` 里的 `python`/`python3` 差异会让同一脚本在交互 shell 和调度环境表现不同。告警链路要有失败标志、通知、成功清除三段证据，不能只看“脚本跑过”。
- **网络探测防代理假阳性**：只测 TCP connect 不足以证明服务可用；代理环境下物理不可达地址也可能“连通”。外部源、API、下载器、OAuth 回调必须用协议级握手、真实响应字段、物理不可达对照或最终业务 payload 证明可用。
- **时间切片 / PIT 通用化**：任何历史数据、试卷版本、答案解析、source_state 判断都要问“当时能知道什么”。禁止用 latest snapshot 回填历史判断；训练/评测/人工复核要区分 in-sample 与 OOS；宽表 passthrough 必须显式排除未来字段；未知要保留 `null/unknown`，不要用 `0` 或默认值吞掉不确定性。
- **DuckDB / 本地数据并发约束**：默认按“单写多读”设计。批量导入、审计、索引/派生物生成要避免多个 writer 竞争；大表扫描先聚合、分批、`LIMIT` 或只读连接，不把 20GB+ 中间结果拉进 Python。临时脚本不得绕过 registry/source_state 直接写库。
- **Hook 先读源码再归因**：hook 报错先看 hook 源码、关键词、匹配范围、实际 stdout/stderr；不要用 `--no-verify` 或修改业务代码去躲 hook。若 hook 噪声高，修 hook 的触发条件和失败信息，而不是降低项目 gate。
- **外部 API / 数据同步要分类失败**：`refused`、`permission_denied`、`empty_result`、`schema_drift`、`calendar_gap`、`rate_limited`、`network_error` 要分开记录。可用性探测必须落到最终参数粒度；历史稀疏源要先抽样探测；日历/版本缺口和失败队列是两类问题，不能混成“暂无数据”。
- **实验设计必须预注册退出标准**：V0 只能用于低成本方向判断，不能直接宣称生产可用。每个实验要提前写清输入、输出、成功阈值、失败阈值、消费者和不做的替代方案；负结果要归档，因为一个负例可能同时淘汰多个方案。
- **派生成果 / 地图 / 索引要可复现**：生成物必须声明输入列表、版本、排序规则和稳定字段；时间戳、行数漂移等 volatile 字段不要进入审计结论。机器事实与人工判断分层保存，静态扫描的盲区要显式写进报告。
- **补救验证要三层闭环**：代码 diff 只是第一层；还要有只读数据/产物证据、真实退出码或用户可见行为。新增硬 gate 后必须处理旧 artifact：回填、隔离或标记降级。baseline/waiver schema 要 fail closed；如果扫描器只 print 不 fail，必须修扫描器或加 wrapper。

## Must-Know Files
- `docs/RESUME.md` = 断点续传叙事交接(现行): 最近进度脉络 + 下一步 + backlog. 读它拿叙事; 数字一律去 moth/DB/d0_baselines 取真值(RESUME 不 hardcode 易漂计数).
- `goal.md` for active objective, blockers, and plan.
- `CLAUDE.md` for history/reference (treat as secondary unless user explicitly requests migration).
- `docs/architecture.md` for layering and request flow.
- `docs/data_accuracy_audit.md` for quality gates.
- `moth assert --repo .` + `.moth/assertions/claims.yaml` + `backend/config/d0_baselines.yaml` for live data-honesty state and pinned counts (one-shot snapshot docs like round/closure-checkpoint removed — they rot/mislead; RESUME kept as narrative handoff but its numbers cite truth sources, not hardcoded).
- `analysis/project_state_ledger.md` for completed work and historical evidence.
- `.moth/profile.yaml` for local project tooling profile.
- `.codegraph/codegraph.db` for dependency map and query context.

## Current Command Surface
- API server boot: `python -m backend.api.main`.
- Data pipeline: `python scripts/init_db.py`.
- Accuracy/audit: `python scripts/data_accuracy_check.py`.
- Service/API tracing: `codegraph context "<symbol>"` / `codegraph query "<symbol>"`.
- Frontend smoke: open served root and inspect routes in `frontend/static/*.js`.

## Current Development Plan
1. 保持 route -> service -> schema -> UI 的链路完整。
2. 优先处理审计与一致性问题，再优化体验或重构。
3. 每次改动都写明预期影响面、验证方式与回滚点。
4. 小片提交，默认可回退，避免一次性大改。
5. `.codegraph/` 为本地索引缓存，默认保持离线/本地态，不纳入提交；提交前确保该目录未被 `git add` 或提交。

## Known Hotspots
- `backend/services/graph.py`, `backend/services/links.py`, `backend/services/canonical.py`
- API router registry in `backend/api/routes/__init__.py`
- Frontend integration points in `frontend/static/app.js` and `frontend/static/app_router.js`

## Next Action
- 将课程/题库链路修复与前端兼容性修复提交并推送；若仍有缺项则同步更新 `goal.md` 与 `analysis/project_state_ledger.md`。
