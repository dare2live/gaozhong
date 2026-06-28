# gaozhong Codex entrypoint

本项目 Codex 规则主文件是 `agent.md`。

本文件只作为 Codex / Moth / 全局 `AGENTS.md` 发现入口，避免项目因为缺少标准
`AGENTS.md` 而回退到 legacy `CLAUDE.md`。不要在这里复制完整规则，避免双真相源。

接手顺序：

1. `docs/product_master_plan.md`（北极星·产品方向）
2. `agent.md`
3. `goal.md`
4. `docs/README.md`
5. `docs/architecture.md` + `docs/toplevel_architecture_design.md`（工程层）

`CLAUDE.md` 是历史兼容资料；除非用户明确要求迁移或对比，不作为 Codex 当前规则源。
