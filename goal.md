# gaozhong 项目 — 辽宁 K12 英语学习者产品 (初中+高中)

新 session 接手先读 **`docs/product_master_plan.md`(🧭 北极星·产品方向)** + `AGENTS.md` + `agent.md` + 本文件 + `docs/README.md` + `docs/architecture.md` (八条铁律) + `docs/lessons_learned.md`.
**SessionStart hook 自动注入铁律 + 近期 lessons + 完成自检**, 不靠人提醒.

**用户身份**: 持牌教育机构 — 合规非阻塞.

> 🧭 **2026-06-27 产品方向重置 (北极星 `docs/product_master_plan.md` 立法)**: 本项目是**面向学习者(学生)的三层产品** —— L1 基础数据(教材/课标/考纲/中高考真题→库) → L2 解析关联(真题↔课标/考纲/教材 + 命题趋势/考查方式变化) → **L3 课程层(产品心脏: 最少课程覆盖最大考点 + 可背诵段 + 学完掌握高频考点与命题套路)**。用户拍板: **A** 教师工具下线(但课程必含作业=真题, 流程 教学提纲→备课/课程/作业→整体↔每节匹配); **B** 高中先跑通; **C** 建 L3 框架内容先不生成(依赖 L1/L2 准确, 先搭骨架+补就绪门)。**旧"教研系统/备课工具"定位降级**; 教师面产物按 A 决策下线(后端服务保留)。**任何"建什么/先做什么"以北极星为准。** 现行进度/下一步看 `docs/RESUME.md`。

---

## D0 第一重要铁律 (用户 2026-05-24 硬约束) 🔴

> **"本项目任意数据 + 任意关联性, 准确率必须 100%."**

不是 80%, 不是 95%, 是 **100%**.

| 含义 | 实现 |
|---|---|
| API 返的每条数据正确 | 服务/算法/查询, 真 ground truth 校验 |
| 推荐/对照/弱点推送 100% 准 | 宁缺毋滥 (返空 > 假推) |
| audit 报告真实反映 | 任何 WARN/FAIL 必须列入 `docs/data_accuracy_audit.md` 处置 |
| 不准用"估计/差不多/大概" | 算不出 → 标 unknown, 不假填 |
| 形式 vs 实质 | "完成"必须可验证 (数据查询 + 真模型导入 + 文档 trace) |

**强执行 (live, 不引旧计数)**:
1. `scripts/data_accuracy_check.py` — 全数据集 100% 校验, 0 错才 exit 0 (校验维度以脚本为准, 不在文档 hardcode)。
2. `scripts/stop_gate.sh` — Stop hook: audit FAIL/WARN、D0 失败、CC>10/CC>15 新增、前端 inline 新增 任一 → BLOCK。
3. `moth assert --repo .` — claims-vs-reality 弹仓, PASS 才健康。
4. 实施 trace: 每个推荐/对照/审计在 `docs/data_accuracy_audit.md` 列准确率 + 修复路径。

**D0 边界诚实 (坑1)**: "100% 准" 是对**已登记 D0 维度**的强校验; **未断言的维度永远绿(未必对)**。任何"X% 准"先 grep 门是否覆盖该维度。新 API/算法/数据落地必须: ① 加进 `docs/data_accuracy_audit.md` ② `data_accuracy_check.py` 加校验项 ③ moth 加断言 (坑17: moth AND D0 双门)。

**数据诚实分层 (防 over-claim, 详 RESUME)**: 真值可卖(题型迁移/词汇热力/cognitive_skill explicit_label/考试词典) > LLM 方向性参考必标(genre/theme 零核验, 坑16) > demo 壳必空态(学情全合成, 坑4)。

---

## 总目标

把"枯燥教材"拆细重组成"符合年轻人习惯、可背诵"的最小课程集, **不偏离学校**(单词/语法/进度 ≤ 已学单元+课标), 紧贴**辽宁高考命题特点与趋势**(新课标 II 卷), 让学习者**用最少课程吃透高频考点 + 命题套路**。终态 = 学习者产品(L1 基础库 + L2 真题特点研判 + L3 课程)。教师工具下线(后端服务保留)。

---

## 架构控制面

| 面 | 当前约束 |
|---|---|
| 产品方向 | **北极星 `docs/product_master_plan.md`**(三层架构 + IA + L3 框架/覆盖模型/就绪门/诚实护栏) |
| 工程层架构 | `docs/architecture.md`(八铁律) + `docs/toplevel_architecture_design.md`(模块+数据+配置三层范式) + `backend/config/project_architecture.yaml`(机器契约) |
| L2/KG 设计 | `docs/kg_layer_design.md`(知识图谱维度扩展层) |
| 文档索引 | `docs/README.md`(current law / spec / legacy); `docs/RESUME.md`(断点续传叙事) |
| 数字真相源 | `backend/config/d0_baselines.yaml`(锚) + `moth assert` + `map doctor`; **文档不 hardcode 会漂的计数** |
| 架构 gate | `python3 scripts/tools/audit/project_architecture_audit.py --strict`(BLOCK) |
| sibling 项目 | gaokao / LifeHack / ChunkyMonkey 只作 pattern reference, 不得成为 gaozhong 数据真相源 |
| 奥卡姆约束 | 不新建大平台; 沿用现有 `data_sources`/`contracts`/`audit`/`imports` 模块, 新增机器契约+只读审计防漂移 |
| 数据诚实守护 | `moth assert`(claims-vs-reality 弹仓) + `gaozhong-ops` skill(坑库); 定位用 codegraph 不人肉 grep |

---

## 红线 (命题趋势分析 vs 押题, 2026-06-16 用户立法)

- ✅ **核心竞争力 (做, 优于人工)**: 数据驱动的**命题趋势分析 + 方向性重点指引**(哪些考点/题型/题材/命题方式升温→教学优先级)。好老师本就画重点, 大数据做得更准。
- 🔴 **死亡条款 (banned)**: 声称押中**具体题目/篇章/答案内容**("AI 押中高考精准预测") = fraud, 营销话术。
- 🛡 **四护栏**: ① 样本量诚实(<10 不下趋势结论) ② provenance 溯真相源 ③ 结构≠内容(造题=结构对齐+课标合规, 不复现真题) ④ ML 数据足才上。详 `gaozhong-ops` skill 坑14。

---

## 与姊妹 gaokao 项目边界
- DuckDB 完全独立, 不 ATTACH; 真题数据已单向从 gaokao 镜像本地(运行时不读 gaokao, moth `gaozhong-self-contained` 守门)。
- 分工: gaokao=真题侧研判 / gaozhong=教材+真题+学情完整 K12 学习者产品(自带真题, 不依赖 gaokao 运行)。

## 系统化治理 (持续, 不靠提醒)
详 `docs/architecture.md` §0 八条铁律 + `docs/lessons_learned.md`.

| 时机 | hook | 作用 |
|---|---|---|
| PreToolUse | `precode_review_hook.sh` | god-module>400L / fan-in>5 BLOCK |
| UserPromptSubmit | `user_prompt_continuity_hook.sh` | git uncommitted 提醒 |
| Stop | `stop_gate.sh` | 数据 FAIL/CC/前端 inline 新增 → BLOCK |
| SessionStart | `session_start_hook.sh` | 注入铁律 + lessons + 自检 |

**永不接受** "下次我注意" 类承诺; 重复 ≥2 次失误必须 hook 化。

---

> 📜 **历史**: 第一~七阶段 + Week 里程碑变更日志 + 交付门历次复评 已随 2026-06-27 产品重置归档到 **git log**(本文件不再堆历史阶段计划/逐 commit 日志, 避免过时内容误导)。现行进度 = `docs/RESUME.md`; 设计真相 = 北极星 + architecture。
