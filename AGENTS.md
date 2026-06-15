# gaozhong Codex entrypoint

本项目 Codex 规则主文件是 `agent.md`。

本文件只作为 Codex / Moth / 全局 `AGENTS.md` 发现入口，避免项目因为缺少标准
`AGENTS.md` 而回退到 legacy `CLAUDE.md`。不要在这里复制完整规则，避免双真相源。

接手顺序：

1. `agent.md`
2. `goal.md`
3. `docs/README.md`
4. `docs/architecture.md`
5. `docs/top_level_module_data_config_architecture_20260615.md`

`CLAUDE.md` 是历史兼容资料；除非用户明确要求迁移或对比，不作为 Codex 当前规则源。
