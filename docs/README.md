# gaozhong 文档权威索引

日期：2026-06-26

本文件是当前文档入口。接手顺序：**invoke `gaozhong-ops` skill** -> `docs/RESUME.md`(断点续传叙事交接: 最近进度脉络 + 下一步 + backlog) -> `moth assert --repo .` + `python3 -m scripts.tools.map doctor`(看 live 数字真值) -> `AGENTS.md` -> `agent.md` -> `goal.md` -> 本文件。

> 2026-06-15: 数据诚实性整改 9 commits 已闭环(真题 provenance / EOL 真题入库 / Phase 7 回滚 / 去停用词 / god-module 拆分 / 趋势模型干净重建)。三门全绿。守护: `moth assert --repo .`(以 `moth assert` verdict 为准, 现 107 条) + `gaozhong-ops` skill(坑库)。详 `goal.md` 数据诚实性整改段 + `lessons_learned.md` L-R..W。
> **文档原则**: 易腐的**计数/状态**一律不固化进文档, live 数字以 `moth assert` + DB 实测 + `backend/config/d0_baselines.yaml` 为准。`RESUME.md` 作为**断点续传叙事交接**保留(记进度脉络/决策/下一步), 但其中的数字同样引真相源、不 hardcode; round/closure-checkpoint 类一次性快照已删。

## Current law

| 文件 | 用途 |
|---|---|
| `AGENTS.md` | Codex 标准入口，指向 `agent.md`，避免回退到 legacy `CLAUDE.md` |
| `agent.md` | 当前项目规则、controller 模式、Mythos/架构审计规则 |
| `goal.md` | 当前目标、铁律、阶段控制板 |
| `docs/RESUME.md` | **断点续传叙事交接(现行)**: 最近 session 进度脉络 + 下一步 + backlog; 数字引 moth/d0_baselines 不 hardcode |
| `backend/config/d0_baselines.yaml` | **数字真相源(锚)**: per-paper eq 计数锚(真题/辽宁/中考/cognitive…); 文档计数一律引此, 不另写裸数 |
| `backend/config/project_architecture.yaml` | 模块 / 数据 / 配置 / gate 所有权机器契约 |
| `docs/architecture.md` | 系统分层与八条铁律 |
| `docs/toplevel_architecture_design.md` | **顶层架构(现行)**: 模块+数据+配置三层范式 + 7类扩展 playbook(≤2处) + 治理/演进路线(2026-06-26) |
| `docs/exam_ingestion_pipeline_design.md` | 真题入库管道架构优化 + 2026经验教训 + KG传导gap + P0/P1/P2(中考forcing) |
| `docs/top_level_module_data_config_architecture_20260615.md` | 三层范式首版立法(2026-06-15, 已被 toplevel_architecture_design 承接演进) |

## Current verdict / gate evidence

| 文件 | 用途 |
|---|---|
| `docs/data_accuracy_audit.md` | D0 数据准确率审计总表 |
| `.moth/assertions/claims.yaml` | claims-vs-reality 弹仓(以 `moth assert` verdict 为准, 现 107 条) |
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

## Gate order

最小架构 gate：

```bash
python3 scripts/tools/audit/project_architecture_audit.py --strict --output data/reports/project_architecture_audit_20260615.json
```

M0 数据 gate 仍以 `backend/config/m0_gates.yaml` 为权威，不用文档口头宣布完成。
