# RESUME — 断点续传 (新 session 先读这个)

> 配北极星 `docs/product_master_plan.md` + goal.md + docs/architecture.md 用。本文件 = 最近进度 + 下一步, 更新于每个大节点。
> 🧭 **北极星·产品方向 = `docs/product_master_plan.md`** (2026-06-27 重置, 现行最高产品设计)。新 session 先读它再读本文件。
> 🏛️ **工程层架构 = `docs/architecture.md`(八铁律) + `docs/toplevel_architecture_design.md`(三层范式) + `docs/kg_layer_design.md`(L2/KG 设计)**。
> ⚖️ **本地立法: 禁固化会漂的计数/状态** —— 真题数/图谱规模/moth断言数/词典量等一律只写"见 `moth assert` + `python3 -m scripts.tools.map doctor` + `backend/config/d0_baselines.yaml`", 不在叙事里 hardcode 裸数(否则下个 sprint 必陈旧 = 坑1/坑2)。
> 📜 **更早 session 历史**(地基重审/K12入库/KG建设/真值校验/交付冲刺/RC1前端/口径审计) 已随 2026-06-27 产品重置归档到 **git log**; 设计现行真相 = 北极星 + architecture + kg_layer_design + data_accuracy_audit, 不再在本文件堆历史日志。

---

## 🧭 当前方向 (2026-06-27 产品重置 + 北极星立法): 面向学习者的三层产品, 教师工具下线, L3=心脏

用户判定多轮迭代把项目磨成了"教研工具+数据正确性", **真正要的产品(L3 课程层)一直没建且早被回滚(坑6)**。截图实证: 课程弹窗甩原始题号 `gb/...44`、前端"完全看不出意思"。**全量方案见北极星**(本段只记决策+下一步)。

- **三层架构(依赖严格偏序)**: L1 基础数据(教材/课标/考纲/中高考真题→库) → L2 解析关联(真题↔课标/考纲/教材 对应 + 命题趋势/考查方式变化) → **L3 课程层(产品心脏: 最少课程覆盖最大考点 + 可背诵段 + 学完掌握高频考点与命题套路)**。
- **用户 2026-06-27 拍板**: **A** 教师工具下线(后端服务保留), 但课程设计必须含作业(流程 教学提纲→每节备课/课程/作业→整体↔每节匹配); **B** 高中先跑通, 初中同结构镜像放第二步; **C** 建 L3 框架但**内容先不生成**(依赖 L1/L2 数据正确, 先搭骨架+补就绪门)。消费者 = 学习者(学生)。
- **产品 IA(高中, 初中镜像)**: ① 命题研判首页(结论先行) · ② 真题特点(统计/热力 + **小初高词在高考卷占比** = "最少覆盖最大"王牌实证) · ③ 基础库(教材/真题/课标可查可溯源) · ④ 40节课程(L3, 每段↔考点↔真题↔趋势权重, 替掉裸题号)。
- **阶段路线图**: Phase A 前端 IA 重构(两板块+四页骨架, 教师 tab 下线) → Phase B 现可建产品页(真题特点含小初高词占比 + 基础库 + 研判结论首页) → Phase C L3 框架(教学提纲+覆盖模型+可溯源 schema+作业挂真题, **零内容生成**+补就绪门) → Phase D L3 内容(就绪门绿才做) → Phase E 初中板块。

### ⏭️ 进度 + 下一步 (autonomous /loop 推进中, goal-app 已设会话目标)
- **✅ 文档重置 (commit bc70716)**: 北极星 `docs/product_master_plan.md` + 删 37 份过时文档 + goal.md 2600→95 / RESUME 457→70 瘦身。
- **✅ Phase A 前端 IA 重构 (commit 22c1e9d)**: 初中/高中两板块切换器 + 高中四页 + 教师工具下线(后端保留) + 初中 Phase E 占位 + `scaffold.js`。
- **✅ PhaseB-1 小初高词占比王牌图 (commit 108cccb)**: `k12.tested_word_stage_distribution` + `/api/k12/tested_word_stage` + 真题特点页 结论先行 banner + echarts 图。**实证: 辽宁高考考查词 小初阶 75.7% / 高中新增仅 18.1% / 未分类 6.2%**。双门。
- **✅ PhaseB-3 基础库真题库+课标库 (commit f874b38)**: 真题库 `/api/exam/liaoning_browse`(province 前缀坑7-safe, 按年/题型, 每题溯源 source_file#index) + 课标库(复用 theme_contexts/grammar_items + 新 `/api/curriculum/summary` 计数: 主题13/语法108/词汇3052) + 基础库hub四库全通; 新 `jichu_pages.js`(tiku/kebiao); moth liaoning-browse-prefix-safe。四门绿。
- **下一步 (autonomous loop 续)**: **PhaseB-2** 真题特点 分布迁移/套路热力(复用 exam_point distribution/shift/cognitive, 分卷制era, 填 zhenti 页两个 Phase B 占位卡)→ **PhaseB-4** 命题研判首页 结论先行 banner(beike 顶部加一句话研判结论)→ **Phase C** L3 框架(教学提纲+覆盖模型+段级schema+作业挂真题, 不生成内容)。
- **铁律**: 四门每步绿; 改 services/db/api 前 codegraph + complexity≤10; 新数据 moth AND D0 双门; 数据真值不估算; 不生成 L3 内容(Phase D 需就绪门)。

---

## 门状态 + 数据诚实分层 (接手必看)

- **三门全绿**: `data_accuracy_check.py` exit0 (D0) + `stop_gate.sh` exit0 + `moth assert` PASS。计数以脚本 verdict / `d0_baselines.yaml` 为准, 不在此 hardcode。
- **数据诚实分层 (防 over-claim, L3 就绪门依赖)**:
  - **真值可卖**: 题型 presence 结构迁移 · 词汇热力四象限 · cognitive_skill 技能侧(explicit_label 第一手解析) · 考试词典(教材→中考→COCA 三源溯源, 第一手源最值钱)。
  - **LLM 方向性参考(必标, 非真值)**: genre/theme 题材分布 = dual_model 推断, **零第一手核验**(坑16, 维持"模型推断"标注; **不可用 tests_exam_point 真值边数顶替这条 caveat**)。
  - **demo 壳(必空态)**: 学情整条 = 合成 seed(student_answers 全 demo); 真实学生作答 = 0 条 → 弱点/热力/推荐全 demo。
- **样本量诚实**: 辽宁逐年 <10 标"趋势样本不足"不画 slope(坑12); 分布(同卷制 era ≥30)可报。cognitive "推断迁移"引数必同句带"n=方向性", 别 narrate 成 era 迁移真值。

## L2 口径正确性 (2026-06-27 审计已收口, 是 L3 就绪门的前提)

> "数据每条真但聚合口径错→分析无效"(坑12) 透镜扫 7 子系统: 23 条确认, 收敛 4 根因, **已全修**(commit 4245827→c1a66f3, 三门绿)。
- **根因A 出现≠考查**: tests_word 收口辽宁离散考点题型(完形/语法填空/短改/单选); lesson/course/recommend/dict命中/必教★/placement 弱点 全改 ln_tested 三源一致。
- **根因B 子题/篇章粒度未归一**: 班级薄弱率(全班分母) + 蓝图按考纲 canonical 结构(非 grain 混合 avg) + difficulty→篇幅 全修。
- **根因C 样本量**: sufficiency per-(era,维度) 篇章级。
- **根因D 门重言式**: 新增门均跨第一手源/as-served 公式(非同源自证) + moth AND D0 双门。
- **判 over-engineering 不建**(mio 质疑需求+verify-the-verifier): exam_questions_norm view(各 grain 消费方语义正交, 无统一消费方) + placement 阅读 cognitive 弱点(qb 篇章级 JOIN 子题节点 0 命中, grain 不匹配)。仅当未来有"需 grain 归一计数"的新消费方才值得建。

## 初中 / 中考子系统 (Phase E, 现状)
- 产物: `data/junior_high/structured/{curriculum_vocab,grammar_items,hujiao_vocab,stage_refined}.jsonl`; 中考 2024+2025 省统一卷已结构化。**尚无独立 D0 门接 stop_gate**(待补)。
- 实证发现: 中考语篇填空 = 10 维语法蓝图 ≈ 高考语法填空考点全集(N=2, 2024/2025); 跨阶段 `deepens` 边已验证种子。
- 定位: 沈阳本市, 沪教牛津版 + 义务课标 2022。北极星 Phase E 同结构镜像高中后再深建。

## 真相源 / 门 (live, 不引文档旧数字)
- D0: `python3 scripts/data_accuracy_check.py` (exit0)
- 门: `bash scripts/stop_gate.sh` (exit0) + `moth assert --repo .` (PASS) + `moth coupling --repo .` (孤儿引用)
- 全库重建: `python3 scripts/init_db.py`; 重建后必重生成 `python3 scripts/build_vocab_classification.py`
- 状态总览: `python3 -m scripts.tools.map doctor` · 接手对账: `sherpa takeover --repo .`
- gaozhong↔gaokao **完全独立**(运行时不读 gaokao; 真值已镜像本地, moth `gaozhong-self-contained` 守门)。
