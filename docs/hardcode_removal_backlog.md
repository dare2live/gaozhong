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
- **P2 后端阈值**: scope.py 30/10/5 → thresholds.yaml `trend:` · slope±50(model.py + predicted.py 两份)→ `trend.vocab_slope_significant` · alignment评分阈值 · PDF抽取页范围(curriculum_vocab/grammar/junior 等)→ sources.yaml 各PDF条目加 `extract_pages` · build_manifest URL→读 sources.yaml。
- **P3 D0计数门补 B()**: junior_accuracy_check 1600/505/沪教 · d0_*_check 散落计数(d0_cognitive_skill_check:78 cog_cross_theme_l2 yaml已注册没读) · truth_baseline_common TARGET_MIN_COUNT。
- **P4 route分类/默认入config**: exercise.py province默认'辽宁'/year_min · graph_popup `_REL_RANK` · listening section→题型名 map · cooccur min_co (2 vs 3 不一致=bug)。
- **P0 余**: question_bank/loader._difficulty 100/400 → 需先把 get_threshold 移到中立 util(避 question_bank→course 耦合) · api_payload_check courses<40。

## R1-R4 重构 (动单一计算点拓扑, 走 codegraph + 对抗 + 三门)
- R1 G3 卷型标签4处统一 · R2 G4 _SKILL_MAP→yaml(坑16真值验) · R3 lexicon_filter 分层映射→`layer_curriculum_map.yaml` · R4 constitution year_weights→G1。
- **R5/R6 已核实**: nav 已config化(误报); app_router.js layerMeta ~1200词 两处重复 → 若纯展示只去重不入config。

## 别动 (合法常量, 防过度配置化)
CSS像素/颜色令牌(design-system.css本就配置层) · HTTP状态码 · 数组下标 · 音频倍速[0.75,1,1.25,1.5] · 力导向物理参数 · 解析正则 · 路径常量 · LIMIT防滥用 · scope.py(era单点结构正确) · EOL YEARS(真值就2021/22) · 已config化的真相源(exam_structure_eras/question_types/sources/d0_baselines)。
