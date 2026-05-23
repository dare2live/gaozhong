# gaozhong 项目 — 沈阳/辽宁高中英语教学系统

新 session 接手先读 `CLAUDE.md` + 本文件. 全部铁律见 `docs/architecture.md` (单一计算点 / canonical first / edges 一等公民).

**用户身份 (2026-05-23 澄清)**: **持牌教育机构** — 合规非阻塞, 教材/真题入仓 + 公开部署在授权范围内.

## 当前阶段 (2026-05-23 重排)

按用户最新指令路线 (替代旧 M1-M5):
1. **第一阶段 — 数据彻底补全** (当前) — 不留遗漏的"半口径数据" → 见下文 §"数据补全清单"
2. **第二阶段 — 题型扩展** — 听/应用文/读后续写 + 难度梯度 + 合成题 (待数据齐)
3. ~~学生端~~ — 暂不开发
4. ~~合规~~ — 持牌机构, 非阻塞

---

## 项目目标 (用户 2026-05-23 累计要求)

把"枯燥教材" 拆细打碎重组成"符合年轻人习惯的内容", 不偏离学校 (单词/语法/进度), 围绕**辽宁高考特点** (新课标 II 卷, 听 30+笔 120), 兼顾趣味性,
最终产出 **后端 + HTML 前端** 教学+作业系统, 含**知识图谱 + 4 级作业生成 + 数据交叉审计**, 推进到**可交付运营**.

---

## 交付门 (M1-M5 里程碑)

| M | 名称 | 验收 | 状态 |
|---|---|---|---|
## 数据补全清单 (第一阶段, 不留遗漏)

按用户原话"彻底补充完整没有遗漏". 每项都列 (1) 当前缺口 (2) 计划 (3) 完成度.

### A. 教材 unit 召回 (xuanze_4 + 其它残缺)
- 缺: waiyan/xuanze_4 整册 0 unit; renjiao/bixiu_2 缺 2 unit (4/6); xuanze_3 仅 1 unit
- 计划: pdfplumber 兜底 + outline 二次扫描 + 人工 anchor list
- 验收: 14 册 ≥ 5 unit/册 (含 Welcome)

### B. 教材词表 (vocab_intro) 人教版抽
- 缺: 人教版 7 册词表 **0** 行 (4 市 unusable)
- 计划: 人教版 APPENDICES `Words and Expressions in Each Unit` 单独抽器
- 验收: renjiao 7 册各 ≥ 100 词, 总 ≥ 1500 词

### C. 教材 section 二次精化
- 缺: Other 23 个 (anchor 未命中); 多 unit 只 1-2 section
- 计划: 扩 ANCHOR 词典 + 子 section (e.g. Reading and Thinking 内 Activity 1-N)
- 验收: 每 unit 6-9 sections, Other ≤ 5%

### D. 课标语法 4 象限 (类比 vocab)
- 缺: grammar 只有 cefr_level edge, 没 exam_status; 真题用语法点没识别
- 计划: 题面 grep 中文语法术语 (eg "定语从句"/"非谓语动词") 命中 → tests_grammar; 算 4 象限
- 验收: grammar.attrs.exam_status 入 graph, 14 顶级类目 + 子项全有 status

### E. 教材短语 / 句型 / 功能表达 (规则版, 不 LLM)
- 缺: 完全空白. 用户原话"教材的表达方式比单词更重要"
- 计划: 扫教材 reading section 文本, 用预定义模式 (动词短语 "take ... into account", 句型 "It is ... that", 功能表达 "I'd like to"); 双关键词 / 滑窗 + cefr_vocab 过滤
- 验收: 每 unit ≥ 10 短语, 总 ≥ 800

### F. 真题省份精炼
- 缺: 334 题中仅 32 (10%) 启发式标"辽宁"; 实际辽宁卷 (2021+ 新课标 II) 应 ≥ 80
- 计划: 用 gaokao 项目 R2 卷型→省份映射 (year → province 1:N), 镜像到本仓 jsonl
- 验收: province=辽宁 题数 ≥ 60 (5 年 × ~12 题/卷)

### G. 真题考点 mapping (tests_word / tests_grammar / tests_theme)
- 缺: 没建 edge — 4 象限统计只是 token-level grep, 不入 graph
- 计划: 规则版 (token grep cefr_vocab + 题面 grep 主题关键词), 入 edges 表
- 验收: edges.tests_word ≥ 5k, tests_grammar ≥ 500, tests_theme ≥ 300

### H. 课标主题 → 单元主题 mapping (theme_of_unit)
- 缺: theme 13 节点全孤儿 (用 ORPHAN_TOLERATED 暂时容忍)
- 计划: 关键词 grep (eg waiyan/bixiu_1/U1 "TEENAGE LIFE" → 人与自我/生活与学习); 人工预定义 mapping table 兜底
- 验收: 每 unit ≥ 1 theme edge; theme orphan = 0; 移除 ORPHAN_TOLERATED 容忍

### I. 听力 / 应用文 / 读后续写 教材素材抽
- 缺: 这三项辽宁卷 70 分占比, GAOKAO-Bench 不含听力音频, 教材内对应 section 未标识
- 计划:
  - 听力: 标 sections.kind='Listening' 的 page 范围 (已有)
  - 应用文: 教材 Writing section 抽功能模板 (邀请/通知/求职/感谢)
  - 读后续写: 教材 Reading section 抽叙事性语篇标记 narrativity=true
- 验收: 三类素材都有 ≥ 20 个候选/标记

### J. 教材图片 / 听力位置 (pdfplumber, 留 K)
- 延后: 需要 pdfplumber bbox, 引新依赖
- 当前: 不做, 列入"M5+ 题型扩展" 时再补

### K. 教材原文文本入图 (sentence-level)
- 缺: section 只有 page 范围, 没 raw_text
- 计划: 每 section page 范围 pypdf 抽全文, 入新表 section_text
- 验收: 14 册 × ~6 section × ~50 句 ≈ 4000+ sentences

### L. 课标主题群下子主题 (level3)
- 缺: theme 只到 level2 (主题群), 课标 §四(一) 有 level3 子主题
- 计划: 硬编码 (课标 p22-23 列了 9 项子主题 / 主题群)
- 验收: theme_contexts 表 level3 列填充 ≥ 30 个

### M. 词形派生关系 (derive_from / related_to)
- 缺: 派生词 (eg able → ability → enable → unable) 在 graph 里是孤立节点
- 计划: 简单规则: 同前缀 + 同后缀模式 (ed/ing/ly/tion) → 加 `derive_from` edge
- 验收: ≥ 500 derive edges

---

## 数据补全后 (第二阶段)
题型扩展见 `docs/exercise_design.md`. 题型清单 (待数据齐补):
- 完形填空合成 (LLM 抽 reading section 关键词遮蔽)
- 语法填空合成 (规则: 时态/语态/词形派生)
- 应用文模板生成 (从 教材 Writing section 抽功能套句)
- 读后续写素材库 (教材叙事 reading 标记)
- 难度梯度: 简单 logistic 回归 (待 sklearn 装)

---

## 旧里程碑 (M0-M5, 历史标记, 不再驱动开发)

| **M0** | 资料基石 + 框架 + 顶层架构 | DB 多表, API 19+ endpoint, 前端区块, 0 FAIL 审计 | ✅ |
| **M1** | 一城一册全程数据通 (沈阳/外研必修一) | 单元 + section + 词表 + 真题映射 链路完整 | ✅ PoC, 第一阶段重抽 |
| **M2** | L1 课时题生成 (词汇 + 短句) | 任 1 unit 出 5 道单选 + 答案 + 考点 graph | ✅ PoC, 第二阶段扩 |
| **M3** | L2 单元题 + L3 阶段卷 | 单元卷 20+ 题混合 | ✅ L2 PoC; L3 第二阶段 |
| **M4** | L4 模拟卷 (完整 150 分 / 120 min) | 题型分布 = 真卷, 越纲率 < 5% | ✅ L4_replay; 听/写第二阶段 |
| ~~M5~~ | ~~学生交互界面~~ | 用户 2026-05-23: 暂不开发 | — |

**"可交付运营" 定义**: M1+M2+M3 完成, M4 跑通一份模拟卷, M5 有最小教师/学生入口.

---

## STEP 路线 (从 M0 推到 M5)

### STEP 1 ✅ (M0)
- 资料基石: 教材 14 册 + 课标 22 PDF + 14 地市选用 + 8 允许版本 + 真题 334 题
- 框架: stdlib HTTP + DuckDB (与 gaokao 独立) + 原生 HTML
- 知识图谱 v1: 3492 节点 / 3964 边
- 审计 0 FAIL / 1 WARN (xuanze 2 册 unit 空)

### STEP 2 教材结构化 (M1)
**当前进度**: Unit 65/85 = 76% · vocab raw 1842 但 INNER JOIN units 后 156 (extractor 严重 bug, lessons L-A)

**已完成**:
- ✅ Unit 第一刀 (outline + regex_min)
- ✅ vocab 第二刀 (raw 1842, 但抽取有 lesson# 误当 Unit# bug)
- ✅ introduces_word edges 156 (过滤后)
- ✅ 4 象限分类 (core/standard/HV_extra/LV_extra)
- ✅ word.attrs.exam_status + teaching_hint 入图

**剩余子任务**:
- **S2.1** 修 xuanze_3/4 空 unit
- **S2.2** section 二级切 (每 Unit → Reading/Listening/Writing/Project/Vocab 等)
- **S2.3** ⭐ **重写 vocab extractor** (用 "UNIT N" 段头切, 不靠行末数字 — 见 lessons L-A) → 召回从 8% 升到 ≥ 90%
- **S2.4** 人教版词表抽 (APPENDICES 排版不同, 单独写)
- **S2.5** 跨版本主题对齐 → `topic_aligned` edge
- **S2.6** 短语/句型 (LLM, 放 STEP 4 一起)
- **S2.7** 热力图前端 (词重要性多维度可视, 用户 2026-05-23 加)

**验收 M1**: 沈阳学生学到外研必修一 Unit 3 → graph 能查 "已学词 100+ / 已学语法 N / 该 unit 主题 ≈ ?"

### STEP 3 真题考点映射 (支撑 M2-M4)
- **S3.1** 真题省份精炼 — 启发式 (年份+卷型+题面 grep) → 让"辽宁卷" 召回率 > 80% (目前 32/334 = 10%)
- **S3.2** 题→考点抽 — 优先**离线规则版** (题面 grep tokens vs cefr_vocab 词典 / vs grammar_items 模板), 不依赖 LLM
- **S3.3** 升级到 LLM 抽 (Claude API, 用户授权后) — 双模型 cross check
- **S3.4** 题目难度估计 — 由 GAOKAO-Bench 答对率 + 题面长度 + 词频回归

**验收**: 每题 ≥ 3 个 edges, 5 年辽宁真题词频可统计

### STEP 4 趣味化内容 / 短语 / 功能表达 (M5 准备)
- **S4.1** 教材 reading section LLM 抽 phrases / 句型 / 功能表达 — **需 LLM API, 待用户授权**
- **S4.2** 越纲机器判 (基于 cefr_vocab, 已有逻辑) — 抽出的表达 token ⊆ 课标 3000+ 词
- **S4.3** 主题 × 年轻人语境 LLM 生成: 短视频脚本 / 段子 / 类比

### STEP 5 作业生成 (M2/M3/M4)
路线见 `docs/exercise_design.md`. 5 步 pipeline:
1. scope spec → graph 召回知识范围
2. v_questions UNION 真题 + 合成题 召回
3. 难度评估
4. 题型分布约束 + 组合优化
5. 渲染 + 答案分离 + blueprint

### STEP 6 评估闭环 + 运营 (M5)
- 学生答题日志 → 弱点 → 推送 / 推荐路径 (graph 查)
- 教师端: 班级薄弱点 dashboard
- 内容版本控制 (合成题 review / 老师标注)

---

## 流程: 每次改代码必走 (hook 强约束)

1. **改前**: 跑 codegraph (`codegraph query <symbol>` 看上下文) + complexity (`python3 scripts/lib/complexity_check.py <file>`)
2. **改时**: PreToolUse hook 自动提醒 god-module / CC>10 / fan-in>3, 高过阈值则 codegraph hotspot
3. **改后**: 同上, 跑回归 (`python3 scripts/init_db.py` end-to-end + curl 几个 endpoint)
4. **commit 前**: `codegraph sync` (索引同步), 一句 commit 含 "before / after" 关键指标

---

## 当前 hotspot (按 hook 提示, 需重构)

| 文件 | 指标 | 触发 | 待办 |
|---|---|---|---|
| `backend/services/extraction/textbook.py` | `_from_regex` CC=13, `_from_outline` CC=11 | CC>10 | S2.1 抽小函数 / 用 helper |
| `backend/services/audit.py` | 241 L 接近 250 god-module 阈值; `audit_publisher_coverage` CC=10 | size + CC | S2 完成后拆 audit/{file,vocab,grammar,publisher,cross,textbook}.py |
| `scripts/extract_curriculum.py` | 239 L | size | 拆出 vocab / grammar / theme 三模块 |
| `backend/api/main.py` | 130 L (已拆) | OK | — |

---

## 持续发现 (每个 STEP 推进中补)

### 内容侧
- 沈阳实际用 **外研版 2019 新版**, 但少数学校用 **人教版** — `liaoning_city_textbook_choice` 是市级粗粒度, 后续可加学校级别 (重点高中数据)
- 课标 3000 词 + 各地 +200 自由扩展 — 教材实际词量预计 3200-3500, **教材引入 - 课标** 差集就是"地方特色词"
- 课标主题语境 10 个 (3 大语境 + 7 主题群) — 外研 6 unit × 7 册 = 42 unit 主题, 平均 4 unit 对一个主题群, 高频主题 (做人与做事/科学与技术) 可能 6 unit

### 流程侧
- 真题"province=辽宁" 精炼: GAOKAO-Bench 标了 year + question 文本, 没标省, 启发式有局限. 应用 (a) gaokao 项目已有的 R2 卷型映射 → 拉一张 year→province 表; (b) LLM 看题面 + 答案标省
- 教材 PDF 文本中"UNIT 1 TEENAGE LIFE" 与 "UNIT 1 CULTURAL HERITAGE" 混在同一 PDF (主体 + workbook) — 看上去是重复, 实际是不同区块. 需要 page 范围 + region tag (course/workbook), 不该粗暴 dedup

### 考题侧 / 关联
- 词频 + 真题频次 → "高频考词" 排名 → 反向给教学侧建议"这些词复习要狠"
- 主题 × 真题: 哪几个主题语境在真题中高频 → 教学侧排课优先级
- 跨版本同主题 Unit 对齐 → 一个学校用人教版, 但想参考外研版同主题 lesson plan → graph 路径

### 试卷侧
- **L1 课时题** 不只是单选, 应该包括 "听写" / "短答" / "对比" 等小题型 (符合青少年注意力)
- **L4 模拟卷** 听力题用 GAOKAO-Bench (题面 + 音频 URL) 还是自合成 — 目前 GAOKAO-Bench **不含音频**, 听力只能用题面 transcript
- 读后续写 (25 分) 是新高考最大 delta — 教材中"叙事性 Reading section" 高频复用为续写训练源, 应专门抽 Reading section 标 narrativity

### 4 象限词分类 (用户 2026-05-23 加)
- **core** (课标 ∩ 真题): 2226 词 (74% 课标) — 必教必练 ★
- **standard** (课标 ∩ 真题未出): 760 词 — 常规
- **HV_extra** (超纲 ∩ 真题考过): 15 词 (maple/manners/related 等) — 教材超纲但高考印证, 必教
- **LV_extra** (超纲 ∩ 真题未考): 33 词 — 教材装饰, 可降权
- 写入 `nodes.attrs_json.exam_status` + `teaching_hint`, 前端 / 出题 / 教学建议都按此分级
- 同样思路待 STEP 3 推到 grammar 4 象限

### 热力图 (用户 2026-05-23 加 — 待 STEP 2 第三刀)
- 维度: 真题频次 × 课标级别 × 教材引入册早晚 × 主题
- 颜色梯度: HV_extra core > core > standard > LV_extra
- SVG 网格, 词按字母/主题 group, hover 显示 graph 邻居 (出处 unit / 考过题号 / 同主题词)
- 同步给"学生兴趣范围" 加注解 (主题 ⊂ 趣味 mapping, eg "音乐"→K-pop/B 站, "体育"→电竞)

---

## 不做 (排除的事)

- 商用题库爬取 (有道精品/百词斩离线包) — 法律风险
- 听力音频自合成 (要 TTS, 不属核心) — 用真题文本 transcript 替代
- 学籍系统整合 — 学生 ID 用本地 sqlite, 不接学校教务
- 跨学科 (语文/数学) — 仅英语

---

## 与姊妹 gaokao 项目边界

- DuckDB **完全独立**, 不 ATTACH
- 真题数据**单向**从 gaokao 镜像 (jsonl 复制), 已做
- 共享层: 高考评价体系 / 课标 / 教材版本 (复用同套真理)
- gaokao 项目走"真题侧研判", 我们走"教材侧 + 教学侧", 在 graph 上交汇 (question ↔ word/grammar/theme)
