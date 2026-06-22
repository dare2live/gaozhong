# 全局去硬编码 backlog (2026-06-22, 5-agent审计 + 总指挥裁决)

> 用户硬约束: "硬编码应从全局移除, 都用模块+数据+配置文件实现。"
> 原则: 真硬编码(派生量/判断规则/卷型省份年/分类映射)搬走; 合法常量(像素/状态码/结构常量/设计目标描述)**不动**(防过度配置化=反奥卡姆)。
> 现有 config 文化: `backend/config/*.yaml`(thresholds/d0_baselines/exam_structure_eras/exam_point_taxonomy/sources/...) + `get_threshold('a.b',default)`(course/loader.py) + `B('key')`(d0_baselines.py)。

## ✅ 已完成
- **前端 nav/IA 配置化** (94ed17d): `nav-config.js` (window.GZ_NAV) 数据驱动 + renderSidebar; 加/排 tab = 改配置一处。
- **前端派生计数写死** (本批): dict.js 4186→fetch 返回 total · xisheng.js 790→去数字 · workbench/teaching 40节→stats.courses(513eb70)。
- **beike n>=30 重算** (本批): 改读 service 透传 `sufficiency.distribution_eligible` (Rule1, teacher.js 已是正解)。
- **P0 孤儿config接线** (本批, config键已存在却没读): course.py homework LIMIT→`get_threshold('course.homework_questions')` · placement.py followup clamp→`get_threshold('placement.followup_min/max')`。
- 三门全绿 (D0/moth79/stop_gate)。

## 归并簇 (先建/扩 config 单点, 再让副本读 — 否则改读取点重复劳动)
- **G1 年份权重** `{2025:5,...,2021:1.5}` 散 5 份(constitution.py:139 / trend_engine.py:61 / milestone_b_rebuild.py:30 / model_capability_audit.py:23 / exam_pattern_extractor.py:27) → **新建 `year_weights.yaml`**(每年6月滚动, 最该数据化)。
- **G2 卷制 era 边界** 2021断点/2015-2020区间/2015辽宁采用年: scope.py 是单点但被旁路 — exam_paper.py:64-65 · cognitive_skill.py BETWEEN 2015 AND 2020 ×3 → 改 `import scope` 复用; scope 加 `LIAONING_NATIONAL_PAPER_SINCE=2015`。
- **G3 卷型省份标签** `辽宁 (新课标 II 卷, 2021+)` ×4模块(exam_province/eol_import/pdf/extract) → exam_paper.py 的 LN_II_* 设唯一来源, 其余 import。
- **G4 _SKILL_MAP** (cognitive_skill.py:27-37) ↔ 已有 exam_point_taxonomy.yaml `question_intent.aliases` → 补 yaml 缺的变体 + 读 yaml 删 .py 第二份 (坑16: 改后对真值交叉验证)。
- **G5 stage/category→颜色映射** 前端散 3 份**且已漂移**(STAGE_C: k12.js/dict.js/beike.js, dict有"高中"键 k12无) → design-system.css 加 `--color-stage-*` 令牌 + 共享 `category-config.js`。**已漂移=真bug, 优先**。
- **G6 卷面结构** exam_alignment_checker.py:21-28 `GAOKAO_STRUCTURE` ↔ 已有 question_types.yaml(分值重复) → 读 yaml 删字面。

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
