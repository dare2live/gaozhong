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

## Must-Know Files
- `goal.md` for active objective, blockers, and plan.
- `CLAUDE.md` for history/reference (treat as secondary unless user explicitly requests migration).
- `docs/architecture.md` for layering and request flow.
- `docs/data_accuracy_audit.md` for quality gates.
- `docs/RESUME.md` for current open problems.
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

## Known Hotspots
- `backend/services/graph.py`, `backend/services/links.py`, `backend/services/canonical.py`
- API router registry in `backend/api/routes/__init__.py`
- Frontend integration points in `frontend/static/app.js` and `frontend/static/app_router.js`

## Next Action
- 将课程/题库链路修复与前端兼容性修复提交并推送；若仍有缺项则同步更新 `goal.md` 与 `analysis/project_state_ledger.md`。
