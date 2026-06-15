# gaozhong 文档权威索引

日期：2026-06-15

本文件是当前文档入口。Codex 接手顺序：`AGENTS.md` -> `agent.md` -> `goal.md` -> 本文件。

## Current law

| 文件 | 用途 |
|---|---|
| `AGENTS.md` | Codex 标准入口，指向 `agent.md`，避免回退到 legacy `CLAUDE.md` |
| `agent.md` | 当前项目规则、controller 模式、Mythos/架构审计规则 |
| `goal.md` | 当前目标、铁律、阶段控制板 |
| `backend/config/project_architecture.yaml` | 模块 / 数据 / 配置 / gate 所有权机器契约 |
| `docs/architecture.md` | 系统分层与八条铁律 |
| `docs/top_level_module_data_config_architecture_20260615.md` | 2026-06-15 模块 + 数据 + 配置收口设计 |

## Current verdict / gate evidence

| 文件 | 用途 |
|---|---|
| `docs/data_accuracy_audit.md` | D0 数据准确率审计总表 |
| `docs/M0_CLOSURE_CHECKPOINT_2026-06-12.md` | M0 EOL overlay partial closure checkpoint |
| `analysis/project_state_ledger.md` | 历史工作与证据 ledger |
| `backend/config/m0_gates.yaml` | M0 gate 顺序和期望状态 |
| `scripts/tools/audit/project_architecture_audit.py` | 模块 / 数据 / 配置架构只读 gate |

## Spec / design notes

| 文件 | 用途 |
|---|---|
| `docs/lessons_learned.md` | 项目历史教训 |
| `docs/cross_version_check.md` | 跨版本对照算法证据 |

## Legacy / compatibility

| 文件 | 状态 |
|---|---|
| `CLAUDE.md` | 历史 Claude 规则。Codex 不默认作为当前规则源，除非用户要求迁移/对比 |
| `docs/RESUME.md` | 历史恢复文档。若与本索引、`goal.md` 或 `project_architecture.yaml` 冲突，以当前索引为准 |

## Gate order

最小架构 gate：

```bash
python3 scripts/tools/audit/project_architecture_audit.py --strict --output data/reports/project_architecture_audit_20260615.json
```

M0 数据 gate 仍以 `backend/config/m0_gates.yaml` 为权威，不用文档口头宣布完成。
