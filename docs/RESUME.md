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
- **✅ PhaseB-3 基础库真题库+课标库 (commit f874b38)**: 真题库 `/api/exam/liaoning_browse`(province 前缀坑7-safe, 按年/题型, 每题溯源 source_file#index) + 课标库(复用 theme_contexts/grammar_items + 新 `/api/curriculum/summary`) + 基础库hub四库全通; 新 `jichu_pages.js`; moth liaoning-browse-prefix-safe。
- **✅ PhaseB-2 真题特点 迁移+套路 (commit 468ef8c)**: zhenti 两卡 → 命题迁移(shift delta 蒸馏 题材+主题群)+ 题材×思维套路(cognitive_by_content); 学习者向结论框架, 复用 endpoint。
- **✅ PhaseB-4 命题研判 结论先行 (commit 67321da)**: beike 顶部 renderVerdict banner — live 蒸馏 3 结论(考查词75.7%小初阶/设问思维推断(2026-07-03 补2024数据后为42.9%, 详见 kg_layer_design.md)/最大迁移生活与学习降23.6pt), 样本量诚实。
- **🎉 Phase B 全完成** (B-1/2/3/4)。四门全绿。
- **✅ PhaseC-1 覆盖模型 (commit 23fc3e8)**: `course.coverage_model` + `/api/course/coverage` — 考点全集可教轴(题材6/主题群8/高频考词1166/语法22)+ 命题频次权重 + 覆盖曲线(题材90%需3/主题群需7/词需903但小初高filter后高中仅~18%delta/语法需17); 设问思维正确排除(套路非可教覆盖). 双门(D0 check33 跨源 + moth l3-coverage-model-sound)。
- **✅ PhaseC-2 教学提纲+段级schema+作业+④前端 (commit b7da84c)**: `course.syllabus`(40节按主题群频次比例分配, 段级 course_segment schema content=null) + `homework_for_point`(考点→辽宁真题溯源 非生成) + `/api/course/syllabus` + 前端 ④40节课程重建(覆盖banner+考点焦点+作业真题友好溯源, **替裸题号 gb/...44 用户痛点**)。双门(D0 check34 + moth l3-syllabus)。
- **✅ PhaseC-3 收尾: 对抗复核修复 (commit 6210614+6ffe45c)**: ultracode 5维度对抗复核(wf)抓到门测不到的真问题, 全修: _alloc 名实不符(贪心→真最大余数法, 生活与学习12→8) · trend_weight 坑12(重复计权→份额/节数) · theme_weight_covered_pct 误导→诚实标 · §3.2 schema 补 segment_id/course_id+coverage_proof · D0 强化(段考点必有 tests_exam_point 边+分配比例+份额防回归)。CC=16 拆 3 子helper 回门绿。
- **🎉🎉 Phase B + Phase C 全完成 (autonomous goal#29 达成, 经对抗复核验证)**: 产品三层贯通 L1 数据→L2 解析→L3 课程框架。前端学习者产品: ①命题研判(结论先行)/②真题特点(小初高词占比75.7%基础阶+迁移+套路)/③基础库(教材/词典/真题190溯源/课标)/④40节课程(L3框架: 覆盖模型+教学提纲最大余数法+段级可溯源+作业真题, content待Phase D)。
- **✅ 用户反馈 N1-N4 + 死代码清理 (commit c61e007/7613a32/9ea32ae)**: 
  - 死代码清理: 删 _renderSegments 死簇(57行)+死CSS(59行); verify-the-verifier 厘清 _openHandout 等非死(off-nav teacher tab 活链), 仅删确认死簇; off-nav 教师子系统全移除是单独产品决策(尤 graph 宜恢复)留用户。
  - N1 义务教育档改标"义务·未细分(小初)"(残档非重叠, 诚实)。
  - N2 语法/搭配统计扩展 (exam_grammar_stats): 语法考查(课标第二级子类 辽宁频次真值: 从句28%/被动17.5%/非谓语14%/时态7%) + 教材搭配/句型/表达库(phrases, 出现非考查诚实标); /api/grammar/stats + 双门; 真题特点页加2卡。
  - N3 设问思维讲解(套路卡可展开: 4认知技能定义+设问信号词, 教学可懂)。
  - N4 教材 DB 直出渲染(/api/unit/content 词表+课文段; textbook.js 去PDF链改"查内容"展开; 修 unit=0 WELCOME UNIT 合法)。
- **✅ 全面项目审计 (8维度对抗验证, commit d70e293/d3e0b72)**: 25-agent 并行审计 + 逐条对抗验证。修: 路径穿越 BLOCKER(`_resolve_under` 收口 /static 与教材 PDF 服务) · 真值锚年份全覆盖(坑1, 2015-2020+2026 补 no_anchor, 系统性 moth 门锁"每辽宁年份必有锚") · aria-label 口径修(出现≠考查) · CLAUDE.md 阶段命名对齐北极星。
- **✅ 教师子系统清理 + KG转正 (用户 2026-07-02 拍板, commit 8fffd70)**: off-nav 教师 tab(workbench/data/students/scan) 与教学无关部分全删(前端4 tab+8死文件+独占后端路由+2死表[course_sessions/scan_uploads], -2349行); **知识图谱(graph)保留并转正为正式导航项**(此前"审计待决定"的悬而未决点已裁决)。改前对抗验证盘影响面(qbank/k12/lesson/placement 被 moth/D0/北极星钉住的部分保留, 只删 UI 层)。
- **✅ 整体前端设计方案 P0+P1+P2 (用户 2026-07-02 要求; commit 7dff8fb/bf9a130/0ced647)**: judge panel(4提案对抗→3评审→综合) 出方案书, 分批落地: **P0** design read 学习者版重写 + 蓝色数据阶令牌(--down-2/-3/-4/--data-gray) + 页头统一(GZ.pageHead 单渲染点, 根治蓝hero三连=style.css遗留裸header选择器泄漏) + 王牌视觉锤(75.7%巨号+纯CSS学段带) + 工程噪声清零(?debug=1才显API徽章/审计脚注双态人话/Phase徽章→页级横幅) + 端点契约门(75端点数据化+双向覆盖率自检, 挂D0+moth双门) + 坑17补齐(k12 as-served/grammar_stats口径 11条断言)。**P1** 五页重构: ①命题研判三问分区+B卡echarts dumbbell迁移图 ②真题特点套路2×2常显卡 ③基础库检索台+四书架活取 ④40节课程8章分组+课程地图条+timeline。**P2** dict A-Z索引/popup深链/PNG导出自包含/语法轴人话映射(coverage service查表)/C卡presence时间带重写/微缩DNA带三处回响(GZ.stageMiniBand单点)。用户反馈追加修复: N6考点关联页"没看懂关联性"→结论先行重排(top3共现句子化+可见降序列表) / N7教材正文PDF硬换行→渲染层合并段落流。
- **✅ 设问思维(cognitive_skill) 2024 真值补齐 (commit 45fd866)**: 排查"新高考II仅2023单年n=15"是数据缺口非前端问题; 系统性核查2021/22/24/25/26 五年本地+网络可得性(网络~15次尝试确认 zhihu 403/学科网付费墙/新闻站宏观评析非逐题, 2022/25/26 仍无可得源); **2024 意外发现本地已有但未接入流水线的解析数据**(GAOKAO-Bench-Updates Reading_Comp.json, 15阅读子题带显式题型标签, Trost marker过真值锚), 接入+D0/moth基线随之更新(坑1三件套: 改数据+改baseline+对抗验证); n=15→28, 推断迁移28.2%→42.9%(样本翻倍更保守可信, 方向不变)。
- **✅ 设问思维方法论调研+首批落地 (2026-07-06)**: 5-agent workflow(数据取证+官方7技能查证+母语迁移理论+2路对抗核查) 查实官方阅读理解7理解性技能(来源: 陈康等《中国考试》2019年第12期, 教育部考试中心命题团队解读)只覆盖4项(理解具体信息/推断/理解主旨要义/理解词汇), "理解观点态度/理解目的/理解文章结构类型"3项此前0数据。落地: ①清理2024阅读理解15条重复行(GAOKAO-Bench-Updates原始空analysis旧行, 与07-03已补数据同题重复, 纯数据卫生非D0数值变更) ②首次填充"理解目的"桶(写作意图题[legacy 2017]+目的意图题[subq 2024]各1边, 均单样本诚实标注) ③taxonomy引用来源精确化(不再笼统写"白皮书"); n=113→115(86+29), 推断迁移28.2%→27.9%/42.9%→41.4%(方向不变)。"态度推断/目的推断"等五维细分假说查无权威依据, 不采用。母语思维迁移(Cummins CUP/BICS-CALP+语言门槛假说)理论支持"诊断层增设语言/策略双归因分支", 不支持"先脱离英语补思维课"(违反不偏离学校方向硬约束), 该项待用户拍板未落地。
- **✅ 工程债清偿 + moth 工具链 (2026-07-06/07)**: CC>15 硬阈债务全清(Rule8) + CC 11-14 软警 25 函数系统性重构(commit 8f40868) + moth 全局审计发现的本项目 complexity-optimizer 62 条 heuristic 发现逐条核查(61 ACCEPT 有据 + 1 真修 `lexicon_filter.allowed_words_for` 加 `@lru_cache`, commit 8462e16) + `tests/test_course_smoke.py` 修复 Phase7 回滚遗留的 `handout` 死 import(commit 6d62dd3)。moth 现完全整合 codegraph(npm 依赖, 已更新至 1.2.0)/sherpa(`takeover.py`)/complexity-optimizer(vendored), 具备 `moth cycles` 循环引用审计。
- **✅ 知识点颗粒度/关联性三缺口整改 (2026-07-06/07)**: 用户追问"颗粒度/关联性/正确性到什么程度"后自评估→制定方案→执行。**缺口1** cognitive_skill 官方7技能诚实披露(理解目的补齐, 理解观点态度/理解文章结构类型仍0样本诚实标 missing, commit e33261c)。**缺口2a** grammar_point 维度(9类聚合)0代码实现的假声明诚实标 `status: pending`(同缺口2a commit)。**缺口2b** `grammar_4q.py TERM_TO_LABEL_KEYWORD` 26→36词(逐条核实真解析文本+grammar_items精确匹配), tests_grammar 边 18→84(4.7x), 覆盖官方语法项 8→22(commit ae7da2d)。**缺口3** 考纲(考试大纲)调研+对抗核查: 确认"考纲未独立成库"是**预期状态非缺口**(国办发〔2019〕29号2020年起新高考省份不再制定考纲, 辽宁2021首考明确适用, 命题范围已并入课标本身), 已更新北极星该条描述, 真缺口改指向"课标→学业质量标准→真题考查范围"解析链未建模(独立STEP2/3待办)。
- **✅ 完形填空得分点词学段分布 (2026-07-07)**: 用户追问"75%词汇是初中及以前, 但得分点是不是靠高中词汇"的字面版本(得分点=每空唯一正确答案词本身难度, 非整篇混合词汇难度)。新增 `attribution.py::cloze_answer_word_stage`(+API+D0 check33+moth), 精确解析 10 篇"选项文本完整内联"完形填空(2015-2020旧课标II 6篇+2023-2026新高考II 4篇; eol/2021,2022/xgkii 因逐空拆行存储结构性排除, 非遗漏)。**实测**: 旧课标II 得分点词高中占比12.4% ≈ 同批全篇基线12.3%(几乎无差, 不支持"得分点更难"假设); 新高考II 得分点词高中占比25.0% vs 全篇基线15.2%(高出9.8pp, 但n=4篇仅方向性非定论)。
- **✅ 高中知识点(语法/短语/句式)占比 + 前端展示 (2026-07-07)**: 用户质疑上条只测词汇难度不够本质, 追加"考查的高中知识点占比"; workflow并行调研(短语基线可行性/空格知识类型可分类性/语法高中独有占比复算)+对抗设计评审后落地 `senior_knowledge.py` 三函数(+API+D0 check44-46+moth): ①`grammar_structural_coverage` 语法填空+短文改错(题型定义排除语义辨析, 零主观判断成本)108课标语法点精确印证24个, 只报绝对数量不报占比; ②`phrase_pattern_exam_relevance` 93个高中教材短语37个能在真题文本共现, 明确不做初高中对比(STEP1数据缺口: phrases表100%高中来源, 义务教育课标2022版无可提取短语枚举, 已诚实记录不造假替代); ③`cloze_collocation_structural_subset` 完形填空180空里7个(3.9%)结构规则确认"像固定搭配", 明确标"下限非真实占比"。**副产品**: 调研过程独立复算发现 `grammar_4q.py::_collect_core_ids` 子串跨枝/跨层误配真bug(坑31, 影响"必教"教学提示), 已修复(core 43→25, 精确匹配+3类白名单例外), 单独commit。真题特点页新增对应展示卡片(浏览器实测数据正确/无console错误/四门验证全绿), 两项分析(cloze_answer_word_stage+joint_attribution_by_passage)首次上前端。
- **下一步 (待用户决策, 非 loop 自动)**: Phase D (L3 内容生成) 需 **就绪门**(北极星§5)绿 + 用户拍板; 或 Phase E (初中板块)。**不自动进 Phase D**(决策C)。已知待办(非阻塞): 坑16 genre/theme 显式真相源交叉验证(GenreTruthChecker, Phase D 前置, 现维持方向性标注); 固定搭配/表达的短语级真题考查标注(现 phrases 是教材库出现非考查); DesignSync 同步设计系统组件到 claude.ai/design 需用户先跑 `/design-login`(本环境无交互终端拿不到 OAuth); cognitive_skill 2022/2025/2026 仍无可得解析源(诚实标待补, 见 `scripts/lib/d0_cognitive_skill_check.py` 头注); "理解观点态度/理解文章结构类型"2官方桶仍0样本(待有更多真题解析数据出现); 语言/策略诊断分支需用户拍板(可行性存疑, 已知瓶颈=无法区分"单词不认识"vs"认识但推不出", 现有样本量下不建议做); 课标→学业质量标准→真题考查范围解析链未建模(STEP2/3新待办, 非考纲缺口)。
- **铁律**: 四门每步绿; 改 services/db/api 前 codegraph + complexity≤10(高fan-in换内聚归属勿绕过); 新数据/schema moth AND D0 双门; 数据真值不估算; **不生成 L3 内容**(Phase D 需就绪门)。

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
