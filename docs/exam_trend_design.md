# 命题趋势 / 考查方式演变 — 顶层设计 (2026-06-21)

> 核心竞争力产品。用户纠偏(2026-06-21): **结构层真值(题型/卷面/课标/设问)足以撑命题趋势**("万变不离其宗"
> + 可感知迁移); 不做辽宁逐年微观斜率(n小)。**改造优先, 不新建; 必要才建; 删旧的不适用新方向的。**
> 勘测: 5-agent workflow(服务/前端/文档/题型数据/真值边界 + codegraph fan-in)。架构师裁决 PROCEED。

## 真值地基(4档 provenance,已对 live DB 核实)

| 档 | 维度 | 可做 / 不可做 |
|---|---|---|
| **真值·权威** | 题型/卷面结构(真题原卷) · 课标演变(课标PDF/source_versions) · 设问类型cognitive_skill(教研解析,**跨era: 旧课标II 85 + 新高考II 15**) | 断言骨架连续+迁移 + **跨era设问演变(推断28→47%)**; 新era n=15方向性, 不做辽宁逐年微观斜率 |
| **LLM·方向性**(必标prov) | genre/theme_l2 分布迁移 + co_occurs | 方向性观察, 不包装成精确趋势 |
| **不做** | 微观考点/词频逐年slope; 题型跨年绝对count比(2021/22子题级粒度坑) | scope.py trend_reliable 门已编码 |

## 改造优先(拱心石 + 复用)

1. **题型升格为 tests_exam_point 第4维**(`exam_point/loader.py`): loader 已 for-loop `_DIMENSIONS`、distribution 已按 dimension 分era分层、shift 已两era做差 → 加 `dimension='question_type'`(provenance=structural_truth)**复用现成单一计算点**, 零新 service。⚠ 入边前必须**粒度归一**(2021/22子题→section / presence)。**[v2]**
2. **`trend/scope.py` reuse_asis**(卷制分段+省份锚+分布vs趋势双门, 7处依赖单点; 禁再造第二个2021常量)。
3. **`cognitive_skill`/`cooccur` reuse_asis**(框架对, 缺口是数据非代码)。
4. **`beike.js` C面板改造**(单文件): 当前喂混粒度slope(辽宁灰显空壳)→改喂题型era分布 + provenance角标。**[v2]**

## 必须新建(最小集)

1. **题型粒度归一层**(loader入边前helper): 唯一数据正确性阻断点(2021/22阅读子题n=15 vs 余年passage n=4, 直接count跨年比=把存储粒度抖动当命题变化, 违D0/坑12)。归一成 presence/structural-share by era。数据全在库, 不新建表。**[v1 用 presence 已规避; structural-share v2]**
2. **卷改结构事实 config**(yaml): 题型 introduced/retired年 + 分值 + 板块共用(只在docs, §3.5数据化)。**[v2]**

## 删除/降级(旧的不适用新方向; 用户决策已调整)

- `trend/model.py` 词频逐年斜率(vocab_year_growth/top_rising_words): ~~删~~ → **用户决策: 保留为辅助, 标"词频非考点"**(不删, 加provenance标注)。
- `question_type_year_trend` slope(混粒度artifact) → 题型演变改走升格distribution(**[v2]** 收口)。
- `trend/raw.py type_distribution_by_era` 平行口径 → 题型canonical化后收口(**[v2]**)。
- 前端重复入口(`app_router #/graph`文本块 + 旧teacher.js exam_point tab)→ 收敛beike单一入口(**[v2]** deprecate)。

## honesty 口径(前端必 provenance 角标区隔)

题型/卷面/课标/设问=真值权威结论 · genre/theme=LLM方向性参考(标dual_model_agree) · 微观slope/词频=不做或标"非考点"。
**分布(distribution_reliable,140题充足)报占比/迁移; 趋势(trend_reliable,辽宁不足)不画跨era斜率。**

## 用户决策 (v1 范围)

- **v1 = 只做最小派生验证先看效果** (✅ 已完成, 见下)。exam_method第二轴 + 旧era采集 = **v2/待定**。
- **旧era(2015-20)教研解析: 先不采, 只比快照** (cognitive_skill 诚实标"仅新高考era")。
- **词频/词云: 保留为辅助, 标"词频非考点"** (不下线)。

## ✅ v1 已落地 (最小可逆, 纯派生)

`trend/raw.py::question_type_era_presence` — 题型×卷制era **presence 矩阵**(provenance=structural_truth,
**粒度无关**避2021/22子题坑, 复用scope.segment)。实测真值:
- **骨架(两era皆在, 万变不离其宗)**: 阅读理解 / 完形填空 / 七选五 / 语法填空。
- **退场**: 短文改错(末2020)。 **登场**: 听力(2021) / 续写·应用文(2024) = 2017课标核心素养驱动。
- 内容门 `question_type_era_structural_truth`(content_gates.yaml): 锁短文改错仅旧era/续写仅新era/阅读两era皆在。
- ⚠ v1 缺陷(已v2修): 登场年受提取gap影响(听力/写作部分年未抽) — v1 signal 由**数据presence**定, 误把"提取年"当"登场年"。

## ✅ v2 已落地 (2026-06-22) — 题型 presence 提取完整性掩码 (坑12 诚实修正)

signal 改由**卷面结构真相源**(非数据 presence)定 → 区分真退场/真登场 vs 缺源(extraction_gap):
- **数据化真相源**: 新建 `backend/config/exam_structure_eras.yaml`(各 era canonical 题型 + extraction_gap 掩码;
  ≥2源=教育部新高考改革+历年真题卷结构, 结构性真值)。`raw.py::_era_structure`(lru_cache单点)+`_qt_signal`(config驱动)。
- **诚实修正**: 短文改错=**真退场**(新高考取消) · 听力=**skeleton+缺源**(两卷制常驻本项目未抽全, **≠v1误标登场2021**) ·
  续写/应用文=**真登场+缺源**(新高考新增但登场年=提取artifact不可信) · 书面表达=真退场(旧课标作文改制, config-only诚实暴露)。
- 门: D0 `_check_qtype_structure`(项23: 听力≠登场/短改真退场/续写应用文真登场缺源/无unregistered) + moth
  `question-type-structure-mask`。前端 C面板: 缺源格淡色虚线+⚠标 + note 区分真退场/真登场/缺源。
- **deferred(子backlog)**: structural-share占比(需 source_repo→粒度collapse, 裁决辅助形态)。

## 下一步 backlog (按顺序)

cog×genre 跨era版(需给2023子题node补passage_label桥) → 2022/24/25 真辽宁设问标注 → structural-share占比 → 旧口径收口。

**"怎么考"第二轴 — 2026-06-21 勘测纠偏(Stream B, 3-agent)**: 第二轴**早已落地 = cognitive_skill**(设问类型,
provenance=explicit_label 最强, `exam_point/cognitive_skill.py`), **不是待建的 exam_method**("exam_method=0行"
只因节点叫 cognitive_skill; 原设计"真相源最弱/cue 586边"系误判 — cue 481条是"考什么/题材"genre/theme, 与第二轴正交)。

## ✅ v3 已落地 (2026-06-22) — 跨era 设问演变 (核心竞争力信号)

**改造优先**(零新表/新service): `cognitive_skill.py` 加 `_legacy_reading_rows` 第二真值源 + `_emit_subq` 抽公共入图, `load_cognitive_skill` 双源拼接。**100 边跨两卷制era**:
- **2015-20 旧课标全国II**: 85 子题(六年全覆盖), 真值门 = exam_questions **refine 后 province**(辽宁新课标II, 坑3 provenance-aware 单点真值 — 区别 subq jsonl 潜在误标, 故不另设 anchor)。题型两格式抽(`_FA` `21．A细节理解题` / `_FB` `【21题详解】题型`)。
- **2021+ 新高考全国II**: 15 子题(仅2023), subq jsonl + 真值锚门(2021甲卷已剔§7)。
- **变体题型**: 只映射**明确同义**(词义推测=词义猜测→理解词汇; 标题概括/大意→理解主旨); 模糊的(细节推理/写作意图/代词指代 共3子题)**诚实不映射 skip**(防 theme_l3 式臆造)。

**命题哲学迁移真值**(教研显式标签拼出, 万变不离其宗): **推断 28.2% → 46.7%**(细节 54.1%→40.0% 下行)= 新高考重高阶推断。
- **诚实护栏**: 旧era 85子题(六年, ≥`scope.MIN_DISTRIBUTION_SAMPLE`=30 分布可靠); 新era仅2023 n=15(<30 **方向性非精确**, `cognitive_skill_distribution` 加 `reliability` 每-era标记, 复用 scope 阈值不 hardcode)。
- **门**: D0 `d0_cognitive_skill_check`(边==100/legacy==85/new==15/源年⊆{15-20,23}/迁移真值/explicit_label/血缘) + content gate `cognitive_skill_era_shift_truth`(交叉相乘锁推断新>旧) + moth `cognitive-skill-goldmine`(改写跨era)。前端 beike D面板 = 双era分组条形 + reliability诚实标注。
- **待补**: 2022/2024/2025 真辽宁设问标注(现 analysis 无前导题型, 诚实空)。

## 历史: 单年→方向锚 (v3 前)
覆盖天花板曾**仅2023辽宁15子题**(2024/25辽宁子题 analysis 0前导题型→无真值源不可硬标=防theme_l3; 2021甲卷已剔)。
v3 经 GAOKAO-Bench 2015-20新课标II reading子题前导题型(同loader+refine省份门)→ **已解锁跨era设问演变**(上)。详 kg_layer_design §6。
