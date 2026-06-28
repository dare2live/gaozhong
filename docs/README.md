# gaozhong 文档权威索引

更新：2026-06-27（产品方向重置 + 文档大清理）

本文件是当前文档入口。接手顺序：**先读 `docs/product_master_plan.md`(🧭 北极星·产品方向)** -> **invoke `gaozhong-ops` skill** -> `docs/RESUME.md`(断点续传) -> `moth assert --repo .` + `python3 -m scripts.tools.map doctor`(看 live 数字真值) -> `AGENTS.md` -> `agent.md` -> `goal.md` -> 本文件。

> 🧭 **2026-06-27 产品方向重置**: 面向学习者的三层产品(L1 数据 / L2 解析关联 / **L3 课程=心脏**), 教师工具下线, 高中先跑通, L3 先建框架不生成内容。**最高产品设计 = `docs/product_master_plan.md`**。任何"建什么/先做什么"以北极星为准。
>
> **文档原则 (用户 2026-06-27 重申"该删就删, 过时内容只会误导")**: ① 易腐的**计数/状态**一律不固化进文档, live 数字以 `moth assert` + DB 实测 + `backend/config/d0_baselines.yaml` 为准; ② 一次性快照/被取代的设计/旧方向规划**及时删除**(历史留 git log), 不在仓里留过时文档; ③ 同一事实单一真相源, 不双写。本次清理 docs 从 ~45 → ~12 份。

## Current law

| 文件 | 用途 |
|---|---|
| `docs/product_master_plan.md` | **🧭 北极星·产品总纲(现行最高设计)**: 三层架构 + 学习者产品 IA + L3 框架/覆盖模型/就绪门/诚实护栏 + 盲点扩展 + 阶段路线图 |
| `docs/RESUME.md` | **断点续传(现行)**: 当前方向 + 门状态 + 数据诚实分层 + 最近 L2 口径正确性 + 下一步; 数字引真相源不 hardcode |
| `AGENTS.md` | Codex 标准入口，指向 `agent.md` |
| `agent.md` | 当前项目规则、controller 模式、架构审计规则 |
| `goal.md` | D0 铁律 + 总目标 + 架构控制面 + 红线 + 治理 |
| `docs/architecture.md` | 系统分层与八条铁律(代码怎么写) |
| `docs/toplevel_architecture_design.md` | 工程层架构: 模块+数据+配置三层范式 + 每类扩展 playbook |
| `docs/kg_layer_design.md` | L2 知识图谱维度扩展层设计 |
| `docs/knowledge_graph.md` | nodes/edges schema 规范(L2 地基) |
| `backend/config/d0_baselines.yaml` | **数字真相源(锚)**: 文档计数一律引此, 不另写裸数 |
| `backend/config/project_architecture.yaml` | 模块 / 数据 / 配置 / gate 所有权机器契约 |

## Current verdict / gate evidence

| 文件 | 用途 |
|---|---|
| `docs/data_accuracy_audit.md` | D0 数据准确率审计总表 |
| `.moth/assertions/claims.yaml` | claims-vs-reality 弹仓(以 `moth assert` verdict 为准) |
| `backend/config/m0_gates.yaml` | M0 真题真值 gate 顺序和期望状态 |
| `scripts/tools/audit/project_architecture_audit.py` | 模块 / 数据 / 配置架构只读 gate(BLOCK) |

## Spec / design notes

| 文件 | 用途 |
|---|---|
| `docs/lessons_learned.md` | 项目历史教训(L-A..) |
| `docs/cross_version_check.md` | 跨版本对照算法证据(D0) |
| `docs/truth_anchor_protocol.md` | truth_baseline 校验体系规范 |

## Legacy / compatibility

| 文件 | 状态 |
|---|---|
| `CLAUDE.md` | 历史 Claude 规则。Codex 不默认作为当前规则源，除非用户要求迁移/对比 |

## Gate order

```bash
python3 scripts/tools/audit/project_architecture_audit.py --strict --output data/reports/project_architecture_audit_20260615.json
```

M0 数据 gate 以 `backend/config/m0_gates.yaml` 为权威，不用文档口头宣布完成。
