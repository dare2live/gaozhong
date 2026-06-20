# KG 层设计 — 知识图谱分析维度扩展层 (master design amend)

> 状态: 设计定稿待开建 (2026-06-20). 经 3 轮 workflow (理解现状 → 维度建模 3角度+评审+红队 → 时间演化/血缘机制 2角度+红队) + 控制器综合 + 事实校正.
> 关系: 本文 amend `docs/k12_platform_master_design.md` 的 §2(Canonical)/§6(分析层)/§7(建设DAG), 新增 KG 维度扩展层 + 横切时间/血缘机制. master 已立的法(三真相源/stage统一原语/word_sense带stage/八铁律)全继承不改.

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
| 主题 theme | exam_point dim=theme_context/theme_l2/theme_l3 | 课标官方3范畴/10群/35子主题 | mature(L3补缺口20→35, 辽宁46%→提) | 复用 |
| 题型 qtype | node_type=qtype + question_type 边(结构性: 阅读/完形/语法填空/续写/应用文/听力) | 卷型结构 | mature | 复用不动 |
| **设问类型 cognitive_skill** | exam_point dim=cognitive_skill, **passage级聚合**(先不建子题node) | **真题教研解析显式标签(explicit_label, 高于dual_model)**; 实测 **38 题有 analysis** | **absent→金矿首建** | 复用 |
| **语法考点 grammar_point** | exam_point dim=grammar_point + 新 `tests_grammar_point` 边 → grammar课标节点 `aligns_to` | 辽宁语法填空真题 + grammar_point_distribution.json(dual_model_avg分歧0.04); **旧弱 tests_grammar(84%非辽宁旧MCQ)降级 legacy_mcq_keyword 不进辽宁分布** | absent(节点全/边弱) | 复用grammar节点+新边 |
| **句型 syntax_pattern** | exam_point dim=syntax_pattern, **真题归纳**(非教材词典) | 辽宁真题双模型归纳; 教材 phrases.phrase_type=候选种子非真相源(phrase→question 实测0边) | absent(真相源未成熟→v1诚实标候选池) | 复用 |
| **表达方式 function_expression** | exam_point dim=function_expression | 应用文/续写真题归纳 + 课标功能意念表(S全集锚) | absent(同句型 v1候选池) | 复用 |
| **命题方式 exam_method「怎么考」第二轴** | **唯一新 node_type** + `tested_by_method` 边 | exam_scenario_patterns.md(284行已实证)+evidence.cue(586边); **unclaimed land, 真相源最弱** | absent | **新建(待业主拍板, §6)** |
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
- **A2** 语法考点升格: dim=grammar_point + tests_grammar_point 边 + aligns_to 桥接; 旧 tests_grammar 降级 legacy_mcq_keyword. 门: 全辽宁+provenance+caveat诚实(9类不覆盖名词数).
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

## 6. 唯一待业主拍板的战略选择

**命题方式"怎么考"第二轴 (exam_method)** 是 master 零立法的 unclaimed land + 真相源最弱(自归纳, 双模型可能像坑16一起错):
- **(a) v1 正式建 exam_method 节点上分析面**: 立刻补全核心竞争力第二轴("命题方式升温/转变"), 但 facet 边界模糊需冻≤8 + 严格 quarantine.
- **(b) 先 docs 沉淀 taxonomy, 暂不入图**: 等真题归纳样本更足再建, 更稳但第二轴短期缺位.

其余建模决策(子题=passage级可逆升级 / provenance底层细分+前端3档 / 句型表达诚实候选池)控制器已定, 不占决策位.
