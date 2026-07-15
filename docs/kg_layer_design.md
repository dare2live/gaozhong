# KG 层设计 — 知识图谱分析维度扩展层 (master design amend)

> 状态: 设计定稿 + **已落地大半** (2026-06-20). 经 3 轮 workflow + 控制器综合 + 事实校正.
>
> ## 🏗️ 建设状态 (2026-06-20)
> | 件 | 状态 |
> |---|---|
> | P0 横切地基 (source_versions PIT + stamp 血缘 + effective_version) | ✅ 13c0d0b |
> | A1 设问类型 cognitive_skill (金矿, 推断50%) + 前端 | ✅ 1529b4f/82b5e7a |
> | 考试词典 exam_vocabulary (4186词99.8%释义: 教材→中考→COCA→变体规范形继承; 7词无释义全登记unglossable白名单) + 释义词典 word_glosses | ✅ b0763f1/3198cb7/+变体 |
> | word_sense 本体 (142跨阶段多义, master A1) | ✅ bb09878 |
> | 关联性: co_occurs 考点共现 + characterizes_theme 主题特征词 | ✅ 50fa9c5/c9d8cd3 |
> | B轨 跨年级分阶 (at_stage 边已细, verify-the-verifier) | ✅ 1d5d2de |
> | **⚠ 矿口缺口**: 考试词典/word_sense **有API无前端** (teacher 页未接) | ❌ 收口冲刺第3步 |
> | A2 语法考点 | **SUPERSEDED (2026-07-15)**: 禁平行 `tests_grammar_point`/dim=grammar_point 考查边; 改只读 `grammar_point_rollup`←`tests_grammar` |
> | A3 句型 / A4 表达 | ⏸ 真相源未成熟·候选池, 需标注 workflow, **真老师校验前别预建** |
> | "怎么考"第二轴 = cognitive_skill(设问类型) | ✅ 已落地+跨era(explicit_label最强, **115边 2015-20旧课标II 86 + 新高考II 29[2023:15+2024:14]**, 推断28→41%迁移; 原"exam_method待建"系误判, 见§6) |
> | A6 立体透视 stereo_query (stage×dim×era) | ⏸ 待 word_sense.stage 跨年级 + 真老师校验后再建 |
>
> **2026-06-27 产品重置后**: 本文是 **L2 解析关联层 (KG)** 的工程设计参考, 产品方向以北极星 `docs/product_master_plan.md` 为准 (L3 课程层是产品心脏)。下方"A2/A3/A6 待建"诸件按北极星就绪门推进, 不在数据未就绪时预建。
>
> 关系: 本文继承的地基法 (三真相源 / stage 统一原语 / word_sense 带 stage / 八铁律) 仍有效, 见 `docs/architecture.md`。

---

## 0. 立法层 (Legislator — 本层为何存在 / 死亡线)

**为何存在**: 把"考什么(内容)×怎么考(命题方式)×哪年×哪阶段×哪版"做成可在一张图上立体查询的分析层, 供命题趋势分析(核心竞争力)与课程/教学层主动消费. 不是新物理层, 是既有 nodes/edges 上的**维度扩展 + 横切版本/血缘骨架**.

**死亡线 (≤3, stranger-testable)**:
1. **不在空心/错地基上渲染伪关联**: 中考 0 道 complete → 不挂边; 初中粗分阶未细化(refined_stage 未回填) → 不建跨年级边. 违 = D0 红线.
2. **血缘写边即带, 绝不事后回填**: 每条派生边写入那一刻带 `{source_year, version_ids, provenance}`; 回填会取到换版后的错版 = 信息已丢.
3. **派生只算一次**: PIT 对齐/分布/趋势/迁移/共现/覆盖只在 services 算一次入表/view, 前端/课程层/脚本只读 (Rule1).

**判断法典继承 master §1** + 新增: provenance 分档(explicit_label > dual_model_agree > dual_model_avg > keyword_weak > pattern_inductive_unverified > unverified_from_exam); 维度宁可"少而真"不要"全而空心"(真相源不成熟先标 unknown/候选池).

---

## 1. KG 层定义 (不新建物理层)

KG 层 = 既有一张图 `nodes(concept_id,node_type,label,attrs_json)+edges(src,dst,relation,weight,evidence_json)` 上的**逻辑分析视图**:
- (a) 新增"考什么"内容维(复用 exam_point 节点 + `tests_exam_point` 边, `evidence_json.dimension` 区分)与"怎么考"命题维(唯一新 node_type `exam_method`);
- (b) 桥接到课标/教材已有节点做 4 路追溯(`theme_aligns`/`aligns_to`);
- (c) 经 graph service `stereo_query` 单一计算点出立体分布(stage × dimension × era × qtype).

**论证不新建层**: nodes/edges generic schema 已是图本体; "维度"= exam_point 节点的 `dimension` + 边语义; "KG层"是逻辑视图非新表. 多一层物理表 = 多一个出 bug 的地方 (奥卡姆/CLAUDE §3.5).

---

## 2. 维度建模决策 (8 维, 经评审+红队+事实校正)

| 维度 | 建模 | 真相源 / provenance | 状态 | 复用/新建 |
|---|---|---|---|---|
| 单词 | node_type=word + 富 attrs(stage/cefr/exam_status) | 课标3500+中考1600 / exam_coverage 单writer | mature | 复用 |
| 题材 genre | exam_point dim=genre (6类) | dual_model_agree | mature | 复用 |
| 主题 theme | exam_point dim=theme_context/theme_l2 | 课标官方3大主题语境/10主题群 (亲验PDF表2: 无可枚举第三级; 杜撰theme_l3已废2026-06-21) | mature(锁L1/L2官方层) | 复用 |
| 题型 qtype | node_type=qtype + question_type 边(结构性: 阅读/完形/语法填空/续写/应用文/听力) | 卷型结构 | mature | 复用不动 |
| **设问类型 cognitive_skill** | exam_point dim=cognitive_skill, **passage级聚合**(先不建子题node) | **真题教研解析显式标签(explicit_label, 高于dual_model)**; 实测 **38 题有 analysis** | **absent→金矿首建** | 复用 |
| **语法考点 grammar_point** | **SUPERSEDED**: 九桶只读 rollup(`grammar_point_rollup`)←`tests_grammar→grammar_items`; **禁止**平行 `tests_exam_point` dim=grammar_point / `tests_grammar_point` | 考查真值=`tests_grammar`; 九桶=empirical 高频面派生 | derived_rollup | 只读服务不写边 |
| **句型 syntax_pattern** | exam_point dim=syntax_pattern, **真题归纳**(非教材词典) | 辽宁真题双模型归纳; 教材 phrases.phrase_type=候选种子非真相源(phrase→question 实测0边) | absent(真相源未成熟→v1诚实标候选池) | 复用 |
| **表达方式 function_expression** | exam_point dim=function_expression | 应用文/续写真题归纳 + 课标功能意念表(S全集锚) | absent(同句型 v1候选池) | 复用 |
| **命题方式 exam_method「怎么考」第二轴** | **唯一新 node_type** + `tested_by_method` 边 | 设问解析实证 + evidence.cue(586边); **unclaimed land, 真相源最弱** | absent | **新建(待业主拍板, §6)** |
| 词→主题 word_in_theme | 新 relation, **word_sense→theme**(非word, 守master A1) | 真相源不足→末位低优先标unknown | absent | 延后 |

**Rule3 判据统一 (红队 concern 收口)**: cognitive_skill/grammar_point/syntax_pattern/function_expression 走 `tests_exam_point` + `dimension` 区分 = **既有机制**(genre/theme 已4次验证), 合法不算"塞JSON". 唯 `exam_method` 因"怎么考"与"考什么"语义**正交** + 需独立画趋势 → 才升 node_type. 判据: **同一内容轴的子维寄生 dimension; 正交新轴才建 node_type**.

---

## 3. 横切机制: 时间演化 + PIT版本 + 血缘 + 松耦合

> 解决: 逐年新中高考卷 + 课标/教材/课程换版 + 任意分层不过度依赖 + 数据血缘. 奥卡姆: 单一轻表 + 单一函数, 砍 SCD2/bitemporal/run-as-node.

### 3.1 PIT 版本注册表 (单一新表)
`source_versions(version_id PK, kind∈{curriculum,textbook,course,exam_paper}, label, effective_from_year, effective_to_year NULL=至今, manifest_ref, supersedes NULL, notes)` — `backend/db/schema/00b_versions.sql`, 种子从 `backend/config/source_versions.yaml`(判断数据化). 只落已真实存在版本不预填空版.

**单一 PIT 计算点**: `services/lineage/versions.py:effective_version(con, kind, year) → version_id` (from≤year≤COALESCE(to,9999), 同kind同年UNIQUE). 所有"按年对齐哪版"统一调它, 不在各处写 year 比较.
**⚠必修(a)**: 锚点区分 — `exam_paper` 按**真题年(exam_year)**; `textbook/course` 按**考生入学年(enroll_year/cohort)**(真题年≠考生用的教材年).
**收编**: `trend/scope.py` 的 2021 卷制断点 → 收为 exam_paper 两行 (P2 迁移, 先并存内部转调, 不为统一而统一).

### 3.2 血缘 (骑 evidence_json, 不另起宽表)
写边那一刻强制带 `evidence_json.lineage = {source_year, source_qid, version_ids:{curriculum,textbook,course}, provenance, derived_by, built_at}`. 节点补 `attrs_json.lineage.version_id`.
**单一注入入口**: `services/lineage/stamp.py:stamp(con, year, qid, prov, derived_by)` → 内调 effective_version 当场固化 version_ids. 5 处写边点(derive/links/links_extra/exam_point.loader/import_recent_exams)收口到 stamp.
**⚠必修(c)**: stamp 必须在大批写桥接边**之前**落地, 防无 lineage 存量(回填取错版).
4 路溯源每跳带 version_ids; manifest 经 version_id.manifest_ref → 原始 PDF URL+sha256 不重存.

### 3.3 逐年追加 + 幂等重推导
新卷 = INSERT `exam_questions_all` 新行(PK question_id 天然幂等, 存量不动) + `services/lineage/rebuild.py:rebuild_for_years(con, years|None)`(None=全量基线; 依赖序 真题→tests_exam_point→分布/趋势/共现/越纲/覆盖).
`links.py:_replace_relation` 增可选 `years` 参 → 有 source_year 概念的边按年 `DELETE ... WHERE relation=? AND json_extract(evidence_json,'$.lineage.source_year')::INT IN (?)` delete-by-source, 只重算受影响年(默认 None 全删向后兼容; 纯主表边 cefr/cat_of 保持全删). 幂等靠 UNIQUE(src,dst,relation) 不靠快照.

### 3.4 松耦合 (换版不 cascade)
1. **只认 version_id 不认内容**: 边 lineage.version_ids 存语义ID; concept_id 版本无关.
2. **换版 = append 不 UPDATE**: 换课标 = source_versions append `curriculum:2022` + 老行 effective_to=2021 + rebuild 受影响年; 老版 2017 边 version_ids 锁 2017 不动. 上层(40节课程/前端)引 concept_id 跨版稳定零感知.
3. **唯一耦合点 = effective_version 一个函数**. 验证: 除 scope/versions 外无 services/前端 hardcode 年份比较或跨层 JOIN 某版物理表.
**⚠必修(b)**: version_ids 在 stamp 写边算一次入 evidence_json, 下游分布/趋势只 json_extract **读不重算**; moth 锁"除 stamp/scope 外无模块调 effective_version" (防 PIT 多处各算违 Rule1).

---

## 4. graph service + 立体视图 + 消费契约

- **stereo_query(con, stage?, dimension?, era?, qtype?)** (`backend/services/graph.py`, 单点): 复用 exam_point_distribution + scope.era + cooccur, 不重算. 返回 `{stage,era,dimension,qtype, points:[{label,n,pct,provenance,sample_n}]}`. 样本量护栏内置(sample_n<10 标 trend_unreliable, 复用 scope distribution/trend 二分门, 坑12).
- **立体前端视图**: 三轴透视表(grade阶段 × dimension维度 × era卷制), 复用 heatmap/trend 组件不新建渲染层. 行=stage(初中行无数据=诚实空态"已采未消化"不渲染伪关联), 列=维度(含"怎么考"第二轴并排), 格=占比+迁移箭头(shift delta)+provenance徽章+sample_n. 全经 stereo_query 单点出.
- **消费产物契约(非指导链)**: 课程/教学层主动查 KG 做约束+溯源 — `course/kg_compliance.py:check_lesson_against_kg` 只读 KG 派生(越纲率 via word_sense.stage / 词量 / 真题覆盖 via桥接边反查 / 设问分布 / 命题方式提示). 越纲标红/覆盖低提示. **KG 只读无运行时反向写图; 课程骨架保留人编 YAML, KG 做合规验证不盲目自动化**.

---

## 5. 两轨并行建设 DAG (门锁校正后真数字)

> TrackA(高中KG加厚)与 TrackB(初中地基)写不同 node/数据目录/D0 check, 物理不冲突. **跨年级立体(A 依赖 B 干净 word_sense.stage)是 join 点非并行点** — 排在两轨各自地基绿之后.

### P0 横切地基 (现在就建, 随增量不大爆炸; 不可回填信息)
- source_versions 表 + source_versions.yaml 种子(各2行起步) + effective_version 收口 + stamp.py lineage 子契约. **理由: KG 层正要写 tests_exam_point/桥接边, version_ids 必须写边时带.**

### TrackA 高中侧 KG 加厚
- **A0** 接线存量(零重标, 坑8): question_intent/grammar_point/外省标注已结构化的孤儿 JSON 直接喂 loader; 外省题标 province=外省不入辽宁分布(§7).
- **A1 设问类型金矿(首建, 红队确认安全第一步)**: loader._DIMENSIONS 加 dim=cognitive_skill, provenance=explicit_label, passage级聚合不建子题node. **门锁真数: 可建边对账 38 题有analysis(非"~29"); 推断占比≈50%对账真相源(防回退inference的15%, 坑16); 辽宁覆盖率(命中数非边数)+provenance纯度.** D0 用 `_check_29+`(避开已占的 _check_23) + 3 条 moth.
- **A2 SUPERSEDED (2026-07-15 颗粒度残留整改)**: 原「dim=grammar_point + tests_grammar_point 写边」与 `irreducible_blockers.grammar_point_taxonomy_dimension` / Rule1 双真相源冲突 → **废止写边**。现行: `grammar_point_buckets.yaml` + `grammar_point_rollup` 只读聚合 `tests_grammar`, taxonomy status=`derived_rollup`, D0 锁考查边=0.
- **A3/A4** 句型/表达: 真题归纳 artifact → loader 加维; 教材 phrase=候选. 门: 真题来源非教材冒充 + 空心率(真题证据边vs候选节点). **真相源未成熟 → v1 大概率诚实停候选池**.
- **A5** 命题方式 exam_method 第二轴(**待业主 §6 决策**): 若建, facet 冻≤8 + taxonomy_self_derived + 只上分析面不上教学面.
- **A6** stereo_query service + A7 立体前端视图 + A8 消费产物接线(kg_compliance).

### TrackB 初中地基 (解 master REVISE)
- **B0** 现状盘点(已有 curriculum_vocab 505/1600 + grammar_items + stage_refined.jsonl **4329行**).
- **B1** 解 6 BLOCK(垃圾词 fuit/gif 清理 / 丢真词补 / cid 释义修).
- **B2/B3** **分阶细化** — ⚠ **verify-the-verifier 修正 (2026-06-20)**: 红队"DB粗分阶红线"是**误读**。实测 `at_stage` **边**早已是细分阶(`stage_backfill` 读 refined_stage; 3095词 0错指/0缺边, 精确匹配), 真跨年级消费(`k12.stage_distribution`)**只读 at_stage 边**(铁律1), 已细已对。粗的只是 `node attrs.stage`, 且**几乎无消费方**(仅 课标变形 披露读它)。更关键: refined=初中 的词 attrs 有标"高中必修"= **word 多义项跨阶段**(master A1 word_sense), **非错标 — 回填 attrs=refined 会抹掉合法高中义项, 是错的方向**。
  - 已做: D0 `_check`(at_stage 精确匹配 refined_stage, 0错指, 坑1 测 correctness 非仅计数) + moth `cross-stage-at-stage-refined` 锁死 + 对抗验证非假绿。
  - 真问题 = word_sense(master A1, attrs.stage 单值消灭跨阶段义项), 大改, 独立增量; 非 refined_stage 回填.
- **B4** 中考解墙补答案 → complete 后才挂边(中考已在 exam_questions_all 带 exam_type=中考).

### 门 (每新维度 D0 AND moth 双门, 坑17; 锁辽宁覆盖率+provenance 非只计边数, 坑1)
血缘完整(100%派生边 version_ids齐无悬挂) / 幂等(rebuild两遍diff空+加新年!=y边不变) / PIT(∀year/kind effective_version唯一+换版旧边不变) / 无裸 INSERT 绕 stamp / gate_contract 真接 stop_gate(坑21) + 触发器认 .yaml.

---

## 6. "怎么考"第二轴 — 已落地 = cognitive_skill (2026-06-21 勘测纠偏, 原"exam_method待拍板"作废)

> ⚠️ **2026-06-21 重大纠偏 (3-agent 勘测 + DB实测)**: 原设计把"怎么考"第二轴当成 unclaimed land(待建
> exam_method node_type, "真相源最弱/evidence.cue 586边")。**全错**:
> - **第二轴早已落地 = `cognitive_skill` 维度**(设问类型: 推断/理解具体信息/理解主旨/理解词汇), `exam_point:cognitive_skill:*`
>   节点 + tests_exam_point 边, 单一计算点 `exam_point/cognitive_skill.py`。框成"exam_method=0行"只因节点叫 cognitive_skill。
>   **不要再建平行 exam_method node_type**(改造优先: 认定 cognitive_skill = 第二轴)。
> - **真相源最强非最弱**: provenance=**explicit_label**(教研解析显式题型前导标签 ^([一-鿿]+题) → 《中国高考评价体系》
>   7理解性技能, _SKILL_MAP), 强于双模型。坑16红线: 禁用设问句 dual_model inference 补第二轴。
> - **evidence.cue(481条, 非586) 是"考什么/题材"(genre/theme passage描述), NOT"怎么考"** — 与第二轴正交, 别动它。
>
> **✅ v5 已落地(2026-07-06): 首填"理解目的"官方桶 + 清重复行)**。cognitive_skill 现 **115 边跨两卷制era**(2024-07-03 从本地已有但未接入的 GAOKAO-Bench-Updates `2024_English_Reading_Comp.json` 补 15 阅读子题, Trost+Shakespeare 双marker过真值锚; 2026-07-06 方法论调研发现2024阅读理解15条旧空analysis行是与上述新行的重复条目, 已清理[纯数据卫生非D0数值变更]; 同批补"写作意图题"[legacy 2017]+"目的意图题"[subq 2024]→理解目的各1边; 详见 `scripts/lib/d0_cognitive_skill_check.py` 头注):
> - **2015-20 旧课标全国II = 86子题(六年全覆盖)**: 从 `exam_questions.analysis` 抽 reading 子题前导题型(两格式 `_FA` 答案后可全角句号/`_FB` 【N题详解】)。真值门 = **refine后 province**(辽宁新课标II, 坑3 provenance-aware 单点真值 — 区别 subq jsonl 误标风险, 故不另设 anchor); 六年 ≥30 **分布可靠**。
> - **2021+ 新高考全国II = 29子题**: 2023(15) + 2024(14); 2022/25/26 无本地/免费可核验逐题解析(2021甲卷剔§7; 2026-07-03 网络检索~15次确认: zhihu 403/学科网付费墙/新闻站宏观评析非逐题, 诚实标未补非流程缺陷); n=29 **<30 方向性非精确**(reliability 每-era标记, 复用 scope.MIN_DISTRIBUTION_SAMPLE)。
> - **命题哲学迁移真值**(显式标签拼出, 万变不离其宗): **推断 27.9%→41.4%**, 细节 53.5%→44.8% — 新高考重高阶推断(方向不变, 样本扩大后幅度更保守可信)。变体题型只映射明确同义(词义推测/标题概括/写作意图/目的意图), 模糊子题(细节推理/代词指代/词义指代)诚实skip防臆造。官方7技能仍剩"理解观点态度""理解文章结构类型"2桶0样本(taxonomy已就绪, 待更多真题解析数据出现)。
> - **门**: D0 `d0_cognitive_skill_check`(115/86/29/源年集/迁移/explicit_label/血缘) + content gate `cognitive_skill_era_shift_truth` + moth `cognitive-skill-goldmine`(跨era改写)。前端 D面板 = 双era分组条形 + reliability诚实标注。

其余建模决策(子题=passage级可逆升级 / provenance底层细分+前端3档 / 句型表达诚实候选池)控制器已定, 不占决策位。
