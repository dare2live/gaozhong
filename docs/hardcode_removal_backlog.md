# 全局去硬编码 backlog (2026-06-22, 5-agent审计 + 总指挥裁决)

> 用户硬约束: "硬编码应从全局移除, 都用模块+数据+配置文件实现。"
> 原则: 真硬编码(派生量/判断规则/卷型省份年/分类映射)搬走; 合法常量(像素/状态码/结构常量/设计目标描述)**不动**(防过度配置化=反奥卡姆)。
> 现有 config 文化: `backend/config/*.yaml`(thresholds/d0_baselines/exam_structure_eras/exam_point_taxonomy/sources/...) + `get_threshold('a.b',default)`(course/loader.py) + `B('key')`(d0_baselines.py)。

## ✅ 已完成
- **前端 nav/IA 配置化** (94ed17d): `nav-config.js` (window.GZ_NAV) 数据驱动 + renderSidebar; 加/排 tab = 改配置一处。
- **前端派生计数写死** (本批): dict.js 4186→fetch 返回 total · xisheng.js 790→去数字 · workbench/teaching 40节→stats.courses(513eb70)。
- **beike n>=30 重算** (本批): 改读 service 透传 `sufficiency.distribution_eligible` (Rule1, teacher.js 已是正解)。
- **P0 孤儿config接线** (本批, config键已存在却没读): course.py homework LIMIT→`get_threshold('course.homework_questions')` · placement.py followup clamp→`get_threshold('placement.followup_min/max')`。
- **G2 卷制era边界收口** (31f36c5): scope.py 加 `LIAONING_NATIONAL_PAPER_SINCE=2015`; exam_paper.py + cognitive_skill.py ×3 不再旁路硬编码 2015/2021。**verify-the-verifier**: d0_cognitive_skill_check 的 2015/2020/2021 故意保留独立字面量 (坑1, 加注释锁意图)。
- **G1 年份权重数据化** (本批): 5 副本 `{2025:5..2021:1.5}` → `backend/config/year_weights.yaml` 单点; constitution.py 加 `year_weights()/year_weight_default()` reader; trend_engine/exam_pattern_extractor/milestone_b_rebuild import 读取。**verify-the-verifier**: model_capability_audit `CONSTITUTION_WEIGHTS` 保留独立宪法镜像字面量做 yaml↔宪法对账 (坑1); 该孤儿对账门接进 **moth `year-weights-matches-constitution` 断言** (坑21 装饰门→门2强制)。对抗验证: 污染 yaml 2025→99 门必 FAIL, 自愈回绿。
- 三门全绿 (D0/moth80/stop_gate)。

## 归并簇 (先建/扩 config 单点, 再让副本读 — 否则改读取点重复劳动)
- ~~**G1 年份权重**~~ ✅ done (见上)。
- ~~**G2 卷制 era 边界**~~ ✅ done (见上)。
- ~~**G3 卷型省份标签**~~ ✅ done (R1; **REVISE backlog**: codegraph 实测 exam_paper fan-in=2 再+4=6 违铁律7 → canonical home 改 **scope** 非 exam_paper; scope 是设计的 PIT/province 常量 leaf hub, 已 fan-in 10, 常量不改行为高 fan-in 是本职)。scope 加 `LIAONING_XGKII_2021/_2015_2020`; 5消费者(exam_paper/exam_province/eol_import/pdf/truth_baseline_load)全 import scope。行为等价: label 字节不变 + 全局无残留字面(cognitive_skill:54 是注释非字面)。moth `liaoning-label-single-point` import-equality 锁。
- ~~**G4 _SKILL_MAP**~~ ✅ done: 9条题型→官方7技能映射收口 `exam_point_taxonomy.yaml question_intent.analysis_label_aliases`; cognitive_skill.py `_load_skill_map()` 读 yaml (lru_cache)。坑16 验证: loaded==原字面 + target⊆官方7 + 读-only复算85边技能分布与DB逐项一致 + 3模糊题型skip保留。新锁: d0 check (yaml target⊆官方7独立字面量) + moth `skill-map-yaml-single-point` 断言。
- **G5 stage/category→颜色映射** 前端散 3 份**且已漂移**(STAGE_C: k12.js/dict.js/beike.js, dict有"高中"键 k12无) → design-system.css 加 `--color-stage-*` 令牌 + 共享 `category-config.js`。**已漂移=真bug, 优先**。
- ~~**G6 卷面结构**~~ ✅ done: exam_alignment_checker.py `GAOKAO_STRUCTURE` → `_load_gaokao_structure()` 读 question_types.yaml (仅 score>0 计分题型, 排除已废单选); **weight 是派生量 score/总分, 现算不存** (单一计算点)。行为等价: 6题型 key集+逐值全一致。moth `gaokao-structure-yaml-single-point` 锁 (总分150/6题型)。

## P2/P3/P4 (批量入 config)
- **P2 后端阈值** (部分done): ✅ **slope±50 真重复修复** → `scope.VOCAB_SLOPE_SIGNIFICANT` 单点 (model._slope_interp + predicted 难度共读; moth `vocab-slope-single-point` 锁)。**决策修正 (Occam + verify-the-verifier)**: scope.py 30/10/5 (MIN_DISTRIBUTION/YEAR_SAMPLE/TREND_YEARS) 经查**已是单点** (cognitive_skill/d0 都读 `scope.MIN_*` 无副本) → **保留模块单点不移 yaml** (无重复可修, 移 yaml = 给重负载 scope leaf 加依赖 + 把 trend 阈值拆两套系统 = 过度配置化, 违 Occam; scope 作 trend 阈值"模块"单点已满足用户"模块/数据/配置"三选一)。get_threshold 移中立 util 仅 slope 不需要 → **defer** 到真有更多跨层阈值时。待办: alignment评分阈值 · PDF抽取页范围→sources.yaml `extract_pages` · build_manifest URL。
- **P3 D0计数门补 B()** (verify-the-verifier 复核后 **多为误判, 不做**): junior_accuracy_check 的 "1600/505" 实为**注释/page-range/描述 f-string**, 真实断言是 `1500<=len(cur)<=1850` **范围 verifier 字面**(独立断言, 有内联依据"官方三级1600+各地可增") → **保留独立**(范围不适配 B() 单值; 验证器钉范围是 verify-the-verifier 本意, 不该耦合 config)。TARGET_MIN_COUNT={2021:55,2022:55} 同理是审计目标 verifier 字面。**待办仅**: d0_cognitive_skill_check cog_cross_theme_l2 yaml已注册没读(真孤儿config, 可接)。
- **P4 route分类/默认入config** (verify-the-verifier 复核后 **多为过度config, 不做**): cooccur min_co **2 vs 3 非bug** (query默认2=API可调探索 / materialize默认3=持久化严格谄媚死防线, docstring明释, 刻意分层, 强制相等会破坏explore-vs-persist设计); graph_popup `_REL_RANK` = **UI显示排序**单点单用(非领域分类, presentation就近合理); exercise `province默认'辽宁'/year_min=2020` = route query 默认(用户可覆盖, '辽宁'是§7语义锚); listening map premise 不存在(pdf:13是注释)。全部移config = 过度配置化(违本表"别动"原则)。
- **P0 余**: question_bank/loader._difficulty 100/400 → 需先把 get_threshold 移到中立 util(避 question_bank→course 耦合) · api_payload_check courses<40。

## R1-R4 重构 (动单一计算点拓扑, 走 codegraph + 对抗 + 三门)
- ✅ R1 (=G3 卷型标签收口 scope, codegraph驱动REVISE home) · ✅ R2 (=G4 _SKILL_MAP→yaml, 坑16真值验) · ✅ R4 (=G1 year_weights→yaml)。
- **R3 lexicon_filter 分层映射** (verify-the-verifier 复核后 **不做**): VOLUME_TO_YEAR/YEAR_TO_LAYERS/CEFR_LEVELS_PER_LAYER **已单点** (vocab_guard 经 import 共用 YEAR_TO_LAYERS 无副本); VERSION_LABEL 看似散落(lexicon"外研"/links"外研版"/recommend反向)但**刻意不同语境形式** (lexicon 是紧凑面包屑"外研·必修1·U1" / links·recommend 用"外研版"全名匹配 DB publisher_short) → 统一会破坏面包屑或 DB 匹配, 非 bug。移 yaml = 过度config(单点)或改行为(强统一标签)。
- **R5/R6 已核实**: nav 已config化(误报); app_router.js layerMeta ~1200词 两处重复 → 若纯展示只去重不入config。

## 收口campaign状态 (2026-06-22)
**第一轮 (backlog 驱动)**: G1/G2/G3/G4/G5/G6 + P2-slope = 7 commits。verify-the-verifier 拦 5 个 backlog 误判(cooccur-min_co非bug/scope-MIN已单点/junior-baselines范围verifier字面/R3核心map已单点/R3 VERSION_LABEL刻意语境形式)。

## 穷尽扫描补漏 (2026-06-22, ultracode: 5-lens Workflow 全新扫 + 对抗式 verify-the-verifier)
**backlog 只是一次审计, 必有漏** → 派 5 类别 lens agent 重扫全仓 + 每候选独立对抗裁决。扫出 13 候选, **全 13 通过对抗 = genuine**(backlog 漏掉的), 分 4 批 (A/B/C/D) commits 三门全绿:
- **批A** (19e4bda): cognitive_skill era_old 裸字面(G2漏的产物侧) + paper_type "新课标 II 卷" ≥5 writer → scope 单点。
- **批B** (deeb15f): 出版社全名→短名(canonical/links 字节副本) + version_key↔短名(links/recommend) → canonical 单点。
- **批C** (c56c39d): 前端 exam_point 维度→课标标签 5处散落 + theme_context **已漂移** → GZ_CAT.dim 单点(归一); 修 teacher.html 缺 category-config.js (preview 验证)。
- **批D** (2cf1800): **6个坑21孤儿config**(thresholds.yaml声明却零消费) + **1个真drift**(vocab容差 YAML 50/200 vs 代码 100/300) + stage标签散落 → get_threshold抽中立leaf + 接线 + stage_labels单点。
**两个真bug价值**: ① thresholds.yaml vocab容差漂移(零消费故长期没人发现, 改YAML无效) ② 前端 theme_context 标签 5文件分叉。这是 backlog 单次审计抓不到、靠穷尽扫描+漂移检测才现形的。

**剩余真待办** (低优, 真值已验): alignment评分阈值 · PDF extract_pages→sources.yaml · build_manifest URL。
**campaign 评判**: 两轮(backlog + 穷尽扫描)共 11 commits, 实质硬编码(派生量/分类映射/标签/卷型省份/阈值/孤儿config/真drift)全清并加 10 条 moth 锁; 剩余是确证的长尾, 按"防过度配置化=反奥卡姆"不强做。

## 别动 (合法常量, 防过度配置化)
CSS像素/颜色令牌(design-system.css本就配置层) · HTTP状态码 · 数组下标 · 音频倍速[0.75,1,1.25,1.5] · 力导向物理参数 · 解析正则 · 路径常量 · LIMIT防滥用 · scope.py(era单点结构正确) · EOL YEARS(真值就2021/22) · 已config化的真相源(exam_structure_eras/question_types/sources/d0_baselines)。
