# RESUME — 断点续传 (新 session 先读这个)

> 配 goal.md + CLAUDE.md + docs/architecture.md 用。本文件 = 最近进度 + 下一步, 更新于每个大节点。
> 🏛️ **平台级最高设计 = `docs/k12_platform_master_design.md`** (第一性原理顶层, 统一高中八铁律+初中子系统+核心竞争力)。新方向先读它。

## 最近 session (2026-06-22 最新): 命题趋势驾驶舱 v1→v3 — "怎么考"第二轴跨era演变 (核心竞争力)

> 主题: 用户纠偏"课标/真题命题趋势是可感知的真值, 万变不离其宗, 你的作用是总结分析" → 顶层设计 `docs/exam_trend_design.md`
> (改造优先非新建)。三轮递进, **全程三门绿 + commit**(起点接上一 session 真值体系)。

**v1 (题型presence)**: `trend/raw.py::question_type_era_presence` — 题型×卷制era presence矩阵(provenance=structural_truth,
  **粒度无关**避2021/22子题坑)。骨架(阅读/完形/七选五/语法填空两era皆在) + 退场(短文改错末2020) + 登场(听力2021/续写2024)。
  内容门 question_type_era_structural_truth + 前端 beike C面板(题型×year presence热力)。

**v3 (跨era设问演变, c048e5f) = 本 session 主交付**: 第二轴 `cognitive_skill` 从单年(2023 15子题)扩到**跨两卷制era 100边**,
  解锁核心竞争力"命题哲学迁移"真值: **推断 28.2%(旧课标全国II 2015-20) → 46.7%(新高考全国II 2021+)**, 细节 54.1%→40% 下行
  = 新高考重高阶推断。
  - **改造优先零新表**: `cognitive_skill.py` 加 `_legacy_reading_rows` 第二真值源(2015-20 reading 子题前导题型, 两格式
    `_FA`/`_FB`); 抽 `_emit_subq` 公共入图(load CC↓)。真值门 = exam_questions **refine后 province**(辽宁新课标II,
    坑3 provenance-aware 单点真值 — 区别 subq jsonl 误标风险故不另设anchor)。变体题型只映射明确同义, 模糊3子题诚实skip 防臆造。
  - **诚实护栏**: `cognitive_skill_distribution` 加 reliability 每-era标记(复用 scope.MIN_DISTRIBUTION_SAMPLE 不hardcode):
    旧era 85≥30分布可靠 / 新era仅2023 n=15<30 **方向性非精确**。前端 D面板双era分组条形 + caveat。
  - **门**: D0 `d0_cognitive_skill_check` 重写(100/85/15/源年集/迁移真值/explicit_label/血缘) + content gate
    `cognitive_skill_era_shift_truth`(交叉相乘锁推断新>旧, 对抗验证非假绿) + moth 跨era改写 + d0_baselines 3基线。
  - 验证: init_db 全量重建 100边复现; 三门全绿(D0 exit0 / moth PASS 74-0-0 / stop_gate exit0); preview D面板渲染正确0 error。

**v3后续 (同session, 勘测workflow驱动)**: 5路并行验真相源 + 架构师裁决 → 选最高价值增量, 改造优先落地:
- **#1 设问技能×题材/主题 交叉 view** (048d996): 复用跨era cognitive_skill(explicit_label真值)×genre/theme(passage级)
  → **应用文100%找信息(0推断)/文学艺术100%找信息 vs 说明文42%推断** = 老师"哪类语篇考哪种思维"分流决策。
  `cognitive_skill_by_content(con,by)` 单一计算点; **最小验证抓到关键对齐**(passage_label裸qid vs genre边'question:'前缀,
  字面join 0/85→规范化后74/85)。异质provenance诚实分层(技能=真值/题材=模型推断, 非真值交叉); era锁2015-20(2021+桥缺失);
  粒度=子题数+thin格<10护栏。D0项31 + moth + 前端F区(100%堆叠条+genre/主题切换)。**诚实不建**: 干扰项(辽宁仅1篇)/跨era交叉/信息位置。
- **#3 raw_question 页中水印清洗** (bae72b7, 坑18续): local_pdf 2024-25 锦宏/学科网 mock-PDF 每页页脚(公众号/客服/页码)
  mid-passage注入污染15行(4下游)。`extract/pdf.py::_strip_watermark` 按行剥(正文0丢失, 仅删水印微信号'jh') + D0 + moth; rebuild自动清。

**v2 题型presence提取完整性掩码** (51778ed, 坑12诚实修正, backlog#2): v1 把听力/续写"提取年"误当"登场年"(artifact)。
v2 加卷改结构真相源 `backend/config/exam_structure_eras.yaml`(canonical题型+extraction_gap掩码 by era, §3.5数据化),
signal 改由**卷面结构**(非数据presence)定: 短改=真退场/听力=skeleton+缺源(≠登场2021)/续写应用文=真登场+缺源(登场年不可信)。
`raw.py::_era_structure`单点+`_qt_signal`; D0项23 + moth + C面板缺源格淡色虚线。

**待办 backlog(按顺序)**: cog×genre 跨era版(给2023子题node补passage_label桥) → 2022/24/25真辽宁设问标注 → structural-share占比 → 旧口径收口。

### 三路并行推进 (2026-06-22, 6-agent勘测workflow + verify-the-verifier 驱动)
> 用户"都推进": 防御性内容核验 + 交付收口 + 采集可行性 三路并行验后 inline 执行。**全程 verify-the-verifier**(agent输出=证据非定论)。

- **采集 (C1) — 诚实天花板**: 2024 cog "可本地采"是**坑3陷阱**(gaokao_bench_2024="Harvard"=全国I卷, 非辽宁II"Carlow"; smoking-gun救场, 我原判断对); 2022/25 教研解析确无前导题型。新era cognitive_skill 数据封顶2023, 扩量需外部辽宁II卷教研解析采集(授权)。
- **防御核验 A1 (2e5b44d)**: phrases.sentence_pattern 32%污染(进lesson_plan老师可见) — regex .*+DOTALL跨段 + such as/形式主语/so that误命中。修: 去DOTALL+负向断言+evidence=匹配span+'强调句'据实改'It is…that句型'(229→65, 0误命中); D0 `d0_phrases_check`(项32, **phrases此前零D0=坑17盲区补**) + moth。
- **防御核验 A4 (20fccdb)**: renjiao变体拼写词丢失(organise等12词) — 纠agent误诊("加列裁剪"已有), 真因=**变体标注'(NAmE -ize)'夹词与IPA间** `_ENTRY_HEAD_RE`失配。修: 允许可选变体标注(2206→2214 +8词, 0回归); content gate `renjiao_variant_words_present`。**诚实残留**: gloss bleed 194→187(短语'X high school'+页眉吸入未修, 需per-unit dry-compare careful, 精确flag).
- **交付收口 B1 (f29ccec)**: exam_vocabulary金矿(4186词)有API无前端→ 新建 `frontend/static/dict.js` 考试词典tab(前缀检索+阶段过滤+provenance徽章[教材/中考/COCA]+辽宁高考命中真值), app.html加📕入口。preview验4186词可检索(organise可见).
- **未验**: A2(KG边语义)/A3(答案逐题)agent ECONNRESET挂未出结论, 不算clean, 待补。

全程三门绿(D0 exit0 / moth PASS 78 / stop_gate exit0), 全推 origin/main。

---

## 最近 session (2026-06-21): 真值校验体系 + 内容门框架 + 5大交付数据钉PDF + no-hardcode

> 主题: 根治"为啥每次检查都发现新问题" = 旧三门只验**自洽**(计数==快照)不验**真值**(内容==第一手源),
> 自洽棘轮把内容偏离锁成绿。本 session 建真值校验体系 + 内容门框架, 把"只计数验过"的盲区逐一对第一手源核完。
> **全程三门绿, 全推 origin/main。** 起点接 KG 层(上一 session)。

**① 真值校验体系 (根因根治, 模块化)**:
- `backend/services/truth_baseline/` (CHECKERS dispatch + TruthChecker ABC + self_test 对抗自测) + `truth_anchors.yaml`
  (锚=第一手源指纹, lifecycle active/no_anchor, ≥2源才立锚) + `truth_check` CLI + 接 D0 门 `_check_truth_anchors`。
- 标准文档 `docs/truth_anchor_protocol.md` (方案→标准→验证→持续完善)。释义PUA清洗(保守 _clean_zh_def) + GlossaryTruthChecker。

**② 颠覆性发现: 杜撰课标"第三级"theme_l3 已废** (34c55d9): 亲验课标PDF表2 — 官方主题语境**仅L1(3)+L2(10)可枚举**,
  "第三级"是32条段落式内容要求(非词条)。库内35个theme_l3=杜撰(extract `_reader`不读PDF直接塞 + dual_model贴标签) +
  131条边/35节点。删源重建(6-agent workflow穷尽血缘) + truth_anchors theme域 + ThemeTruthChecker + D0/moth 防回归锁。
  教训: **真相源双用途 — 向下校验对错 AND 向上对标天花板; taxonomy 必锚第一手源最深可枚举层, 不发明子分类追ceiling**。

**③ 内容门数据驱动框架 (回应用户3次"模块化可扩展可复用")**: `backend/config/content_gates.yaml` + `ContentGateChecker`
  单引擎。**加内容门 = 加一行YAML(query+op+expect+源)**, 自动接D0+CLI(单一真相, 不再D0 AND moth各写一遍)。
  ⚠ 对抗救场: 框架初版`_GATES`路径错→`load_gates()`返空→引擎跑0门却报"0偏离"=**框架自己犯绿门假绿**, 对抗注入才暴露 → self_test加"注册表非空"锁。

**④ 5大教学交付数据钉PDF (穷尽内容核验sweep → 逐项修+内容门)**:
| 偏离 | 修 (单一计算点) | 内容门 |
|---|---|---|
| in_curriculum 假源列(硬编码True谎报越纲47%) | run_vocab 从cefr现算 | content_gates |
| cleaned_judged LLM覆盖交付级词典 | word_sense 去覆盖, 退回真值源 | content_gates |
| 13 waiyan标题截断 / 81垃圾义项(`（`碎片) | _scan_scope_page续行join / _clean_zh_def去前导语法括号 | verify_titles_vs_pdf / GlossaryTruthChecker |
| COCA 84专名噪声 / cefr 44级别错 / grammar 4截断 | _strip_coca_pn / 全行捕星 / _merge_continuations | content_gates 3条 |
| **renjiao 1957→2206**(召回88.5%→99.7%) | _PHRASE_HEAD_RE短语词条 + 双栏reflow头前词派生回填 | renjiao_phrase_present |
  途中内容门**当场抓住3个自引入回归**(PUA fallback/框架空路径/污染门假阳性) — 对抗验证不能省。

**⑤ no-hardcode (用户指令)**: renjiao首单元号硬编码`1`→派生回填; **22个D0计数基线**(cefr3052/grammar108/高考466/182/中考90…)
  收进 `backend/config/d0_baselines.yaml` + `B('key')`读取。改基线=改一行yaml。

**坑15流程修**: junior_accuracy_check 锁容错(DRY抽共享 `scripts/lib/db_lock.py`, init_db重建时不假失败)。

---

## ⏭️ 优化后的计划 (2026-06-21, 接手先看这个)

> 大局: "数据100%准"地基这一 session 从"计数自洽"升到"内容钉第一手源"。**核心竞争力地基与时间跨度的结构性矛盾**
> 已识别(能跨11年的genre/theme全是LLM推断) → 核心竞争力对外口径 = "**分卷制分布迁移 + 命题模式识别 + 教材对齐**"
> (样本量逼出的诚实结论, 非逐年微观趋势)。
> ⚠ **2026-06-22 更新**: "唯一真值锚cognitive_skill单年n=15" 已**部分突破** — v3 用 exam_questions refine省份门 把 cognitive_skill
> 扩到跨era 100边(旧课标II 85 + 新高考II 15), **推断28→47%迁移**已是带门真值结论(structural_truth级)。新era仍n=15方向性,
> 但"考查方式跨era演变"不再是纯LLM/单年 — 这是核心竞争力第一个真值跨era信号。

**A. 真值诚实标注 (防"又一个theme_l3")**: genre/theme_context/theme_l2 481边=dual_model推断, 无第一手源 →
   前端/分析层标 `LLM辅助分类·非考纲官方`(不做命中率未知的"交叉验仪式"=过度工程)。

**B. 内容核验下一层 (sweep已列, 有限可枚举, 非黑箱)**: phrases表 / KG边语义 / qbank停用词残留 / weakness派生(真实答题0条) /
   course audits内容 / **raw_question题干**(只核了answer列, 坑18题干可能bleed卷尾) / 2015-2020+2023-2025答案逐题核 /
   其余6册unit_vocab逐册 / renjiao残留污染(（-起首短语/表头噪声)。每项: 对第一手源核 → 内容门(加content_gates一行)。

**C. no-hardcode 续**: extractor 页范围/正则 + 其余阈值(orphan_ratio/CC baseline)增量迁配置。

**D. 交付收口冲刺 (delivery_readiness_assessment.md, 仍是最高杠杆)**: 统一前端入口 + 金矿(词典/word_sense)接前端 +
   学情空态引导 + Docker+最小鉴权 + **1名辽宁老师30分钟真试用**(唯一独立真相源, 别让"还能建更多"无限延迟它)。

**E. 真实答题入口 (战略, 压后)**: 全平台0条真实学生作答(student_answers全md5合成) → 学情/弱点/热力/推荐全demo空壳(已诚实标)。
   要真交付学情需 答题卡OCR / 在线作答 / 成绩单导入。

---

## 最近 session (2026-06-20 最新): KG 层大建 (设计→P0→词典→word_sense→关联性) + 交付就绪度评估

> ⚠️ **下一步 = 收口冲刺 (operational sprint), 不是继续建 KG 维度**。详 `docs/delivery_readiness_assessment.md`。

**KG 层从设计到落地** (11 commit, 全推 origin/main, 全程三门绿; `docs/kg_layer_design.md` 设计定稿):
- **设计** (cf5a421): 3 轮 workflow → amend master design。用户 2 决策: 两腿并行 + 消费产物。
- **P0 横切地基** (13c0d0b): `source_versions` PIT 注册表(键=kind,variant) + `effective_version` 单一PIT点 + **`stamp` 写边即带血缘**(不回填) + 数据驱动 dispatch (D0 407→358)。
- **A1 设问类型金矿** (1529b4f + 前端 82b5e7a): cognitive_skill 子题级"怎么想", **推断50%** 对账教研解析(驳 inference 错估15%, 坑16); 上备课驾驶舱 D 区。
- **B轨 verify-the-verifier** (1d5d2de): 红队"DB粗分阶红线"误读 — at_stage 边早已细(3095词0错指), 否决错误回填, 锁 correctness 门。
- **考试词典** (3198cb7+b0763f1): `exam_vocabulary` **4186词99%释义**, 课标∪教材真超纲(最小无注水), 三源溯源, 释义=教材生词表→中考词汇表→COCA兜底交叉引用。
- **word_sense 本体** (bb09878, master A1): 404候选→21-agent workflow(锚定释义判断+对抗验证过度检测305→142)→ **142真多义** word_sense节点+has_sense+expands_sense (ceiling→上限/china→瓷器)。修词典OCR污染142词。
- **关联性** (50fa9c5+c9d8cd3): co_occurs 考点共现(记叙文×人与社会46) + characterizes_theme 主题特征词(plastic→环境49)。
- D0 28→36项, moth 61→70。

**交付就绪度评估** (8-agent workflow): 距交付**一个收口冲刺**。4 项门 2 绿(数据/三门)2 缺(**Docker完全无 + 真老师试用从未发生**)。最高杠杆=动员1名辽宁老师30分钟试用(Rule10, 也是范围裁决器)。收口路径: 用户拍板形态+范围 → 统一前端入口 → **金矿(词典/word_sense)接前端** → 学情空态引导 → Docker+最小鉴权 → 真老师试用 → 按反馈再建。**别让"还能建更多KG维度"无限延迟真老师校验。**

---

## 最近 session (2026-06-20 续): 全面审计 (13-agent workflow) + 20 真问题整改 19/20 闭环

**全面审计** (架构师/moth/sherpa + 13-agent workflow 7 维度): 验证-验证器, 抓 20 真问题 (三绿门盲区, 坑1/坑21 复发), 6 假警报正确排除。**整改 6 commit 全程三门绿** (932dddc→acc885f):
- **P0 多租户 BLOCK (5项, 用户硬约束)**: inc6 只 scope 1/7 端点, live curl 实证 t-li 可读 t-wang 学生全档案/弱点/列表 = 越权。修: `_tenant.py` 归属判定单一执行点 (owns_student/owns_class 经 classes 链) + 全 7 端点强制 teacher_id + IDOR 防护 (import_csv 拒跨租户接管) + D0 `_check_28` **行为级门** (真调路由跨租户必拒, 非仅结构) + moth 行为断言。教训 L-ZE/坑24 (隔离声明≠全端点隔离)。
- **P1 HIGH (5项)**: ① 答案保真门 (中考MCQ按题型∈{A-D}/{A-E}, 2024 answer-key全非空) ② 高考计数正向锁 466/182 (B1去重后非陈旧472/188) + 改全部陈旧文档 + moth 17→60 ③ deepens 衔接补全 (label精确漏12时态/非谓语/定从 → grammar_stage_aliases.yaml 数据化, 59→71 全初中语法无衔接孤儿) ④ 中考90题空心诚实标记 (zhongkao_questions.content_status 派生列 + 前端banner: 2024全walled/2025答案待补) ⑤ beike命题迁移做差下沉 exam_point_shift service (Rule1)。
- **P2 MEDIUM (7项)**: sherpa fail_regex 假阳性收紧 (坑21坏门) / phrases 双定义删死代码 / class_weakness agg下沉service / stage未分阶1234词披露 (校本超纲1094+课标变形140, 防静默截断) / JSONL↔DB答案对账moth / beike .catch / **ECharts 本地 vendoring** (用户选; 下载 5.5.0 到 frontend/static/vendor/ 去 cdnjs CDN 供应链风险, moth锁无CDN)。
- **20/20 全闭环** (7 commit: 932dddc→2459a0f); moth 17→61。
- 前端全部浏览器实测 (2 诚实banner + 命题迁移 + 本地echarts v5.5.0 + 0 console error + 截图存证); fresh schema in-memory 加载验证 init_db 可复现。

## 最近 session (2026-06-20): K12 入库 inc1-6 全完成 + 前端4页 + 强验证修复

**A. 强验证 (独立重推导)**: 8切片并行从第一手源重推导→比对→对抗确认 (`docs/data_validation_design.md`); 抓6区真错全修 (高考2024辽宁双源去重/2025中考parser/课标三级清洗按官方口径/沪教截断/五选四/grammar label); ocr_image 可复用裁决模块。**关键**: 三门测自洽不测源保真度, 强验证补盲区。

**B. 数据可视化+前端**: understand+design 工作流(3提案收敛=教师驾驶舱) → 4页落地 (app.html SPA 扩展, 全 vanilla JS + ECharts 单算点不重算):
- 🎯 备课驾驶舱: 考点分布(era分层)/命题迁移/趋势(reliable护栏灰显)/词汇热力
- 📖 讲课调取: 概念浮窗4路追溯(复用graph_popup) + 考点关联力导图
- 🔗 K12衔接: stage阶梯 + 10维语法蓝图59对 + 中考题型
- 👥 分析学生: 多租户(teacher_id隔离) + 班级学情热力 + demo banner

**C. K12 入库 inc1-6 全完成** (`docs/junior_db_integration_design.md`, architect 设计+approve): 单库三判别维(node_type/stage/exam_type) + 两大域(共享知识图谱/多租户学情):
- inc1 中考90题入库 (schema模块化7域文件 + exam_questions_all物理表 + **高考视图隔离零回归** + 修cross_verify回归)
- inc2 初中112词+71grammar:jr节点 + stage节点 + at_stage边防孤儿
- inc3 stage回填(3095高中词at_stage) + **10维蓝图59 deepens边**(中考∩高考)
- inc4 K12 API (services/k12.py单算点) / inc5 K12前端页 / inc6 多租户(2老师隔离+析生页)
- 全程三门绿; 每增量独立commit; 9个commit (656c448→9e658d2 已push)

## 最近 session (2026-06-19): 中考 2024+2025 结构化 + N=2 语篇填空"10维语法蓝图"发现

**C 阶段中考真题按高考标准做完** (2024+2025 两年, junior D0 F9 守门, 对抗验证)。
- **结构化双路径** (`scripts/extract_zhongkao.py`, 高考 schema):
  - **2025 题面驱动**: Scribd 页图 OCR×视觉 → 45题 (题干+选项, 22 MCQ options, 10 语篇填空考点)。
  - **2024 答案key驱动**: 中考网官方答案图 11.png(637x673) **paddleocr×视觉裁决**(裁3块放大4x精读, 与 PaddleOCR 1-40 全一致, 初次扫读误差纠正; 19.E 确认 17-20 五选四) → 45题全官方答案 + 10 语篇填空考点。题干各免费源全门控(Scribd学科网水印空白/kaosheng登录/中考网仅答案/教习网滑块/学科网付费), 标 `stem_status=walled` **不伪造**(mio 失败先承认)。
- **D0 门** (坑17/坑21): junior_accuracy_check 加 **F9/F9b 中考校验**(每年45题/id唯一/辽宁§7/题型分段不变量/语篇填空考点全; 2024 全45官方答案+MCQ∈{A-E})。已接 stop_gate 1c, 对抗验证(污染Q19→exit1, 还原→exit0)。全函数 CC≤10。
- **发现 (N=2 实证, `docs/zhongkao_gaokao_alignment.md`)**: 中考语篇填空 = **固定 10 维语法蓝图** — 2024+2025 逐空覆盖**完全相同的 10 个语法维度**(连词/被动/名复/冠词/非谓语/时态/比较级/介词/副词/代词), 仅词例不同(非随机出题); 且这 10 维 = **高考语法填空考点全集**。→ 这 10 点 = 平台最高优先级地基 + 跨阶段 `deepens` 边已验证种子(真卷实证非 LLM 臆测)。诚实边界: N=2 是蓝图快照非趋势(坑12)。

## 最近 session (2026-06-17): 高中地基重审根治 + 初中子系统立项

### A. 高中数据地基重审 — 18 项数据正确性问题全清 (已 push)
前轮 14-问题审计 + 本轮对抗复核新发现 4 项, 全部根治。**三门全程绿** (D0 exit0 / moth PASS46 / stop_gate exit0)。
6 个 commit (e2dfc59→80e930c, 已 push origin/main):
1. **renjiao/waiyan 词表单一区段重写**: 跨单元重复 331+96→0 (字母总表/glossary 砸进尾单元污染); bixiu_2 U1 56→66; cefr 3055→3052(截国家表误纳)。
2. **exam-status 单一计算点** (#12/#13/#14): province-blind(§7违反) + 3处各算 + attrs整段覆盖 → 收口。grammar_4q 孪生同修。
3. **「考过」判定收口到 tests_word 边** (Rule1): core-无边 347→0 (你指出 token-bag vs 边不一致); build_tests_word 改 lemmatize+覆盖 cefr∪教材词。
4. **section 边界+截断** (#7/#9): 过宽 section 8→0(末单元吞 workbook/glossary, waiyan锚点cap + renjiao unit_overrides); section_text 20000截断 28→0。
5. **EOL 真题截断** (#8): raw_question 900硬截 11→0 + 空白13→0; 辽宁阅读 AVG 361→637。
6. **代码债**: data_accuracy_check<400 + _from_outline CC11→10。

教训沉淀: 每条修复都加 D0断言+moth(坑17双门); 门会假绿(坑1)——前轮审计漏 331/96 重复且其提议反是根源, 再审 Workflow 也误火过, **直接查 live DB 才靠谱**。moth coupling 验证: 单一真相拓扑健康(tests_word fan-in26=canonical读, 0孤儿引用)。

### B. 初中 + 中考 子系统 — 立项 + 顶层设计 (Phase 0 进行中)
用户立项: 拉沈阳中考+初中教材/课标, 像高中一样标注, 将来打通成"初中+高中统一平台"。
核心洞察: **stage 标注**(with/the 是小学词非高中词, 标 stage 后处理方便)。
- **顶层设计**: `docs/junior_high_subsystem_design.md` (architect-controller: genesis层 + stage原语 + separate-build-merge-later)。
- **已有资产**: 义务教育课标2022 PDF(三级体系,词汇表p94-152/语法p116,145) + 初中教材人教5册+外研6册 + renjiao_vocab.txt(4578)。
- **缺/待核**: 沈阳中考真题(命题方/卷型/源) + 沈阳初中教材版本(§1.4≥2源)。研究 Workflow wq9lacnsp 核验中。

### C. K12 分阶段 — 主业即时步 S3 落地 + 设计深化 (2026-06-17)
- **S3 stage 标注 (主业)**: 高中 word 节点加 `attrs_json.stage` (cefr_level 派生)。**with/the/and=义务教育**(修用户指出"非高中词处理不便", **tag-not-exclude 不删**)。分布: 义务教育1580/校本超纲1134/高中选修985/高中必修487/课标变形143。D0 加2断言(每分类词带stage + 义务教育==cefr义教1580)。单一writer exam_coverage 写。三门绿(moth PASS46)。
- **设计深化**: junior_high_subsystem_design.md §10 加**双向贯通+跨阶段语义扩展5维**(词义扩展/搭配/语法deepens/语篇/思维品质/主题spiral + 回溯补救+受控渗透+评估轨迹)。删重复 k12_staged_platform_design.md。
- ⚠️ power 案例: 当前 stage=高中必修(仅高中cefr口径); 用户举 power=初中力量 → 待 S1 初中三级加载后 S4 reconcile 重标。

### D. 定位已决「服务沈阳本市」+ 沪教牛津已获取 + Phase1 课标落地 (2026-06-17)
- **定位拍板 = 服务沈阳本市** → 主用版锚定**沪教牛津(广深沈通用,上海教育出版社)**; 中考=沈阳省统一卷(2024起)。
- **沪教牛津6册已下** `data/junior_high/textbooks/hujiao/{7a,7b,8a,8b,9a,9b}.pdf` (gitignore同高中, manifest track): 源 TapXWorld/ChinaTextbook(同高中渠道), §1.4 双源核验(版权页**辽宁批文[2018]3** + Oxford原作者 + 六三制7-9 ≠上海五四制 + 美英桥)。⚠️ 文本层 InDesign 乱码**待 OCR**(同高中坑)。⚠️ 别混同目录沪外教版。
- **Phase1 课标抽取**: 义务课标2022 → curriculum_vocab.jsonl(1647: 小学502+初中1145, 三级1593/1600 CMap漏~7不凑) + grammar(66)。stage切分用集合交(不靠损坏星标)。S4桥接: 义务∩高中义教=1333(84%)。
- **sherpa init**: `.sherpa/takeover.yaml` 定制为本仓3门+真相源(D0/stop/moth/map/junior), `sherpa takeover --repo .` 可用。

### E. Phase 2.5 — OCR 全局持久化 + 沪教词表 + S4 双向 stage reconcile (2026-06-17)
- **OCR 工具链全局持久**: PaddleOCR 官方装 `~/.venvs/ocr` (paddle3.3.1+paddleocr3.7.0), 全局入口 `ocr-python`/`paddleocr` (PATH 已含, **跨项目可用**), 模型缓存 `~/.paddlex`。docs/junior_high_ocr_setup.md。
- **纠正"文本层乱码"**: 沪教文本层**大体可读**(7a 122/138页), agent 的"全乱码"错(它用pymupdf)。**CID 只污染中文释义, 英文 word 可读** → stage 词表文本层全抽, OCR 仅补释义。交叉验证: 可读页文本层抽词 **171/171=100% 被OCR确证**。
- **沪教6册词表 926 distinct** (extract_hujiao_vocab.py): 首现去重 per-grade(七上159...九下127); 9b 29页累积总表回填 CID 卷释义 → **仅26释义待OCR**。∩课标三级=648(70%)。
- **S4 stage reconcile** (junior_stage_reconcile.py): 初中源(课标二级=小学/课标三级∪沪教=初中)细分高中 4329词 → **1763(40%)更精细**(义务教育1580→小学499+初中1264); **298 语义扩展候选**(power✓: 初中力量→高中power plant, design§10 边种子)。emit stage_refined.jsonl。

## 当前真相源 (live, 不引旧数字)
- 高中主门 (exit0/PASS): `data_accuracy_check.py` + `stop_gate.sh` + `moth assert` + `map doctor`
- 初中产物: `data/junior_high/structured/{curriculum_vocab,grammar_items,hujiao_vocab,stage_refined}.jsonl` (**尚无独立 D0 门** — 审计待补)
- 接手对账: `sherpa takeover --repo .`

### F. gaozhong 完全独立 + 主架构 v2 + Phase2.6 初中地基修复 (2026-06-17)
- **gaozhong↔gaokao 完全独立**: 切断 2 处运行时跨项目读(gaokao_bench/truth_baseline → 本地镜像);
  init_db 自包含复现 466/182 (B1双源去重后, 原472/188 含6个2024辽宁重复); moth gaozhong-self-contained 守门。"不ATTACH"=跨项目非初中↔高中。
- **主架构 v2** (`docs/k12_platform_master_design.md`): 第一性原理 + 3视角对抗评审定稿(REVISE);
  sense级stage(power自反驳word单标签) + 单库node_type(弃双库三态) + 补学习者/语篇/思维节点 + tutorial契约。
- **Phase2.6 初中地基修复 — 初中 D0 全绿**: 建 junior_accuracy_check(8不变量, 坑17) + 接 stop_gate
  阻断路径(坑21, 对抗验证污染→exit2)。OCR 交叉验证(master§3)洗净课标: F1垃圾51→0 + goal恢复(glyph误解码)
  + F4沪教cid 176→0 + F6语法66→71 + 契约注册。词典门已证不净, OCR=视觉真值。

## 下一步 (Phase2.6 完成, 地基达标解锁 A/B/C)
- **✅ C. 沈阳中考真题** (2026-06-19 done): 2024+2025 省统一卷结构化(junior D0 F9) + 中考×高考对接发现(题型全对齐 + 语篇填空10维语法蓝图=高考语法填空考点全集)。**余**: 2024 题面 stem 待用户提供 doc 补全(各免费源门控); 第三年真卷可得后验蓝图稳定性。
- **A. Phase3 集成 (单库)**: stage_refined 回填高中 word 节点 stage + word_sense 节点(义项级) + 跨阶段 edges。**中考语篇填空10维 = `deepens` 边已验证种子**(可优先落)。
- **B. 语义扩展边** (依赖 A+C): 298候选→跨stage语料 NLP pipeline → expands_sense/collocates_into。
- 余: F7 二级补转写3词(502→505, 低优先); F3 沪教*超纲词召回(926→~1200, 门现800-1400放行)。

## 真相源/门 (live, 不引文档旧数字)
- D0: `python3 scripts/data_accuracy_check.py` (exit0)
- 门: `bash scripts/stop_gate.sh` (exit0) + `moth assert --repo .` (PASS) + `moth coupling --repo .` (孤儿引用)
- 全库重建: `python3 scripts/init_db.py`; 重建后必重生成 `python3 scripts/build_vocab_classification.py`
- 状态总览: `python3 -m scripts.tools.map doctor`
