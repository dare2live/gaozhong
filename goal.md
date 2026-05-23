# gaozhong 项目 — 沈阳/辽宁高中英语教学系统

新 session 接手先读 `CLAUDE.md` + 本文件. 全部铁律见 `docs/architecture.md` (单一计算点 / canonical first / edges 一等公民).

---

## 项目目标 (用户 2026-05-23 累计要求)

把"枯燥教材" 拆细打碎重组成"符合年轻人习惯的内容", 不偏离学校 (单词/语法/进度), 围绕**辽宁高考特点** (新课标 II 卷, 听 30+笔 120), 兼顾趣味性,
最终产出 **后端 + HTML 前端** 教学+作业系统, 含**知识图谱 + 4 级作业生成 + 数据交叉审计**, 推进到**可交付运营**.

---

## 交付门 (M1-M5 里程碑)

| M | 名称 | 验收 | 状态 |
|---|---|---|---|
| **M0** | 资料基石 + 框架 + 顶层架构 | DB 多表, API 19+ endpoint, 前端区块, 0 FAIL 审计 | ✅ |
| **M1** | 一城一册全程数据通 (沈阳/外研必修一) | 单元 + section + 词表 + 真题映射 链路完整 | ✅ (units 66 + sections 93 + vocab_intro 2k+ 入仓) |
| **M2** | L1 课时题生成 (词汇 + 短句) | 任 1 unit 出 5 道单选 + 答案 + 考点 graph | ✅ PoC + 学生端 UI |
| **M3** | L2 单元题 + L3 阶段卷 | 单元卷 20+ 题混合 | ✅ L2 PoC (跨 unit shuffle); L3 同 algorithm 扩 (一册) |
| **M4** | L4 模拟卷 (完整 150 分 / 120 min) | 题型分布 = 真卷, 越纲率 < 5% | ✅ L4_replay (历年真题重组, 非押题) |
| **M5** | 学生交互界面 + 弱点反馈 | 登入 / 答题 / 错题集 / 个性化推荐 | ✅ MVP (`/student` 城市→教材→Unit→答题→自动评分) |

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
