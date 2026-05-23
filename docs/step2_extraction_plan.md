# STEP 2 教材内容结构化 — 提取策略 (基于 PDF 实测)

> 2026-05-23 用 `pypdf` 实测外研版 + 人教版 必修一. 本文记录提取路径选择, 在 STEP 2 启动时直接执行.

## 关键发现 (vs 假设)

| 假设 | 实测 | 影响 |
|---|---|---|
| PDF 可能是图片扫描, 需 OCR | ❌ **两版均为可选文本 PDF**, pypdf 直接抽出干净英文 | 工程量大幅降低, 不引入 PaddleOCR/Tesseract |
| 两版结构相似 | ⚠️ Unit 数 / 板块命名 / outline 都不一样 | 必须分版本写 extractor, 再统一到 schema |

## 两版结构对比 (必修一)

| 维度 | 外研版 (waiyan/bixiu_1.pdf) | 人教版 (renjiao/bixiu_1.pdf) |
|---|---|---|
| 总页数 | 139 | 138 |
| Unit 数 | 6 (Unit 1 - Unit 6) | 5 + Welcome Unit |
| PDF 书签 outline | ✅ 精确到每个 Unit 起始 (B1-2 Unit 1.pdf 等) | ❌ 无 outline |
| Unit 标题样式 | "Unit 1" (内文小字) | "UNIT 1 TEENAGE LIFE" (页眉大字, 主题全大写) |
| 子板块 | Reading / Listening and speaking / Writing / Developing ideas / Presenting ideas / Project / Self-assessment / Function / Learning to learn | Reading and Thinking / Reading and Writing / Listening / Pronunciation / Assessing Your Progress / Notes / Grammar |
| 词表位置 | "Words and expressions + Vocabulary" 单独 section | APPENDICES (p.108 起): Grammar → Words and Expressions in Each Unit → Vocabulary → Irregular Verbs |
| 文本质量 | 完美 | 完美 (封面有控制字符 `\x01\x13...`, 只在元数据/封底, 不影响内容) |

## 课标驱动 — schema 不自创, 直接对齐课标 (用户 2026-05-23 反馈)

英语课标 PDF (`data/curriculum/national/.../4.普通高中英语课程标准（2017年版2020年修订）.pdf`, 220 页) 已经把分类轴定义清楚, 不许另起炉灶:

| 课标定义对象 | 位置 | 直接当 schema 用 |
|---|---|---|
| 三大主题语境 + 子主题 | p20-22 | `unit.theme_context ∈ {"人与自我"/"人与社会"/"人与自然"}`, 配子主题枚举 |
| 六要素课程内容 | p20 | section/phrase 都打这 6 个 tag (主题语境/语篇类型/语言知识/文化知识/语言技能/学习策略) |
| 三类课程结构 | p17 | `unit.course_class ∈ {"必修"/"选择性必修"/"选修"}` (我们的教材就是 必修1-3 + 选必1-4) |
| **词汇表 3000 词 (附录 2)** | p129-182 | `vocabulary.cefr_level ∈ {"义教"/"必修"+`*`/"选必"+`**`}`, 课标是 master, 教材词表只做"哪 Unit 引入" mapping |
| **语法项目表 (附录 3)** | p187-191 | `grammar_point.label` 必须是课标这张表里的条目, 不许自创 |
| 学科核心素养水平 1-3 | p125-127 | 评估侧, STEP 4-6 用 |

→ "3500 词"的真实构成: 义教 1500 + 必修 500 + 选必 1000 = 3000, 各地最多再加 200. 课标原话.

## 跨版本统一 schema (课标驱动)

```
CurriculumStandard (常量, 从课标 PDF 一次性抽出)
├── ThemeContext (id, level1[人与自我/社会/自然], level2 子主题, level3 子主题)
├── CefrVocab (word, level=义教|必修|选必, ipa?, zh_def?)
└── GrammarItem (id, category[句子/时态/从句/...], label, level=义教|必修|选必)

Textbook (version=waiyan|renjiao, volume=必修1..选必4)
└── Unit (number, title_en, theme_context_id → ThemeContext, page_range)
    ├── Section (kind=reading|listening|writing|...,
    │            six_element_tag ∈ 主题语境|语篇类型|语言知识|文化知识|语言技能|学习策略,
    │            page_range, raw_text)
    │   ├── Sentence (en_text, source_section, char_offset)
    │   ├── Phrase (canonical, type=动词短语|搭配|习语|功能表达,
    │   │            evidence_sentence_id, oo_syllabus_words[])
    │   ├── GrammarOccurrence (grammar_item_id → GrammarItem, example_sentence_id)
    │   └── Question (prompt, answer, type)
    └── UnitVocabIntro (word → CefrVocab, first_seen_unit, role=主词/复现)
```

设计要点:
- `CurriculumStandard.*` 是 master, 跨版本共享; 教材词表/语法只做"出现位置 + Unit 引入" 的 mapping.
- `oo_syllabus_words[]` (out-of-syllabus): 抽出的 phrase 若含 CefrVocab 之外的词, 列在这里 — 给"不偏离学校"原则 (CLAUDE.md §1.2) 提供机器化判据.

## 提取 pipeline (按依赖)

### P0. 课标抽 (一次性, 跨版本共享, 必须先于 P4/P5)
- 输入: `data/curriculum/national/.../4.普通高中英语课程标准（2017年版2020年修订）.pdf`
- P0.1 **附录 2 词汇表** (p129-182): 一行一词 + 后缀 `*` / `**` 极易解析
  - 输出: `data/structured/curriculum/cefr_vocab.jsonl`
  - 验收: 总词数 ≈ 3000 (允许 ±50), 含 `*` 词 ≈ 500, 含 `**` 词 ≈ 1000
- P0.2 **附录 3 语法项目表** (p187-191): 编号 + 标题层级 + `*`/`**` 标
  - 输出: `data/structured/curriculum/grammar_items.jsonl`
- P0.3 **主题语境清单** (p20-46 课程内容章节): 三大语境 → 子主题
  - 输出: `data/structured/curriculum/theme_contexts.jsonl`
- P0.4 学科核心素养水平 (p125-127): 评估用, 留到 STEP 6
- 失败处理: 词汇表条目数偏离 ±5% → 报错重抽, 不静默吞.

### P1. PDF → raw page text
- 库: pypdf (已验证可用, requirements.txt 加上)
- 输出: `data/structured/extracted/<version>/<book>/page_<NNN>.txt`
- 失败处理: 单页提取失败显式抛, 不静默 fallback (CLAUDE.md §1.5)

### P2. 识别 Unit 边界
- **外研版**: 读 `reader.outline`, 直接得 `(Unit, start_page)` 列表, end_page = 下一 Unit 起始 - 1.
- **人教版**: 扫所有页第一行, 匹配 `^(WELCOME UNIT|UNIT \d+)` 正则, 命中为 Unit 起始.
- 输出: `data/structured/extracted/<version>/<book>/units.json` (一行一 Unit)
- 校验: Unit 数与教材封面/前言 "目录" 对齐, 不齐报错.

### P3. 识别子板块
- 用每版固定的板块名词典做 anchor 切分, 不去硬猜.
- 外研版 anchor: `["Starting out", "Understanding ideas", "Using language", "Developing ideas", "Presenting ideas", "Reflection", "Project", "Self-assessment"]`
- 人教版 anchor: `["Reading and Thinking", "Reading and Writing", "Listening", "Listening and Speaking", "Discovering Useful Structures", "Workbook", "Assessing Your Progress"]`
- 校验: 板块命中数 ∈ [3, 12] (太少漏抓, 太多正则太宽)

### P4. 教材词表抽 (Mapping 到课标 CefrVocab, 不当 master)
- **核心转变**: 课标 CefrVocab (P0.1) 是 master vocabulary, 教材词表**只解决"哪 Unit 引入"** 的 mapping.
- 教材词条排版: `word [ipa] pos. zh_def` 一行一条, 部分版本前缀符号 (`*` `△`) 表示选学/不要求.
- 解析:
  1. 用 pypdf 切出 vocabulary section 的页范围 (P3 给出).
  2. 正则 `^([a-zA-Z][a-zA-Z\-']+)\s+([\/\[].*?[\/\]])?\s+([a-z]+\.)\s+(.+)$` 抓行.
  3. 失败行单独入 `data/structured/extracted/<version>/<book>/vocab_failed.txt`, 人工校.
- **课标对齐**: 每个教材词 → join `cefr_vocab.jsonl` 看是否在 3000 词内.
  - 在 → `UnitVocabIntro(word, first_seen_unit, in_curriculum=true, cefr_level)`
  - 不在 → 标 `in_curriculum=false`, **教材在课标 200 词地方权限内的扩展** (各地最多再加 200), 这部分要单独审查
- 输出: `data/structured/extracted/<version>/<book>/unit_vocab_intro.jsonl`

### P5. 短语 / 句型 / 功能表达抽 (LLM, 双校验, 越纲机器判)
- 这是 STEP 2 主难点, 用户两次反馈: "教材的表达方式" + "课标作为辅助来设计提取方案".
- 输入: P3 reading/writing 板块 raw_text + P0.3 主题语境 anchor.
- 提示词骨架 (草稿):
  - "只抽**多词单位**: 动词短语 / 固定搭配 / 习语 / 功能表达 (邀请/拒绝/建议/感谢等)."
  - "拒绝单词. 单词查 cefr_vocab.jsonl."
  - "每条必须带: (a) 原句 evidence, (b) 主题语境标签 (从 theme_contexts.jsonl 选), (c) 功能/类型标签."
- 双校验: 两个 LLM 独立抽, 交集 ≥ 0.7 κ, 否则交叉评 + 人审.
- **越纲判 (机器化)**: 抽出的 phrase 逐 token 查 cefr_vocab.jsonl, 不在的列 `oo_syllabus_words[]`.
  - 全在课标内 → `keep` (主推)
  - 含 1-2 `**` 词 → `keep_extension` (选必扩展, 可教但标黄)
  - 含完全表外词 → `flag_for_human` (人审决定是否教)

### P5b. 语法点抽 (Mapping 到课标 GrammarItem)
- 教材里的 grammar 板块都对应一个或多个课标语法项目 (P0.2 的 grammar_items.jsonl).
- 关键差异: **不允许自造语法名**, 必须 map 到 `grammar_item_id`.
- 例: 教材 "Discovering Useful Structures" 讲 "现在完成时与一般过去时对比" → 拆成两个 GrammarOccurrence, 各引用对应 GrammarItem.
- 输出: `data/structured/extracted/<version>/<book>/grammar_occurrences.jsonl`

### P6. 课标 + 教材统一入库
- DuckDB (单文件, 与 gaokao 项目一致) 或 SQLite, 不引 Postgres.
- 表 (课标层先建): `cefr_vocab` / `grammar_items` / `theme_contexts`
- 表 (教材层): `textbooks` / `units` / `sections` / `unit_vocab_intro` / `phrases` / `grammar_occurrences` / `questions`
- 所有教材层表的 *_id 必须能 JOIN 回课标层 (foreign key on `word` / `grammar_item_id` / `theme_context_id`).
- DDL 写在 `backend/db/schema.sql`.

## 不打算做的事 (避免范围蔓延)

- ❌ 自训分类器抽板块 (规则 + outline 已够)
- ❌ 自建 OCR pipeline (PDF 已可文本化)
- ❌ 抽 PDF 中的图片 / 听力音频 (STEP 1+2 范围之外)
- ❌ 跨版本 Unit 主题对齐 (STEP 3 任务, 不在 STEP 2)

## 评估指标 (STEP 2 验收门)

课标层 (P0):
- `cefr_vocab.jsonl` 总词数 = 3000 ± 50, 含 `*` ≈ 500, `**` ≈ 1000
- `grammar_items.jsonl` 数与课标附录 3 编号对齐 (人工 cross-check)
- `theme_contexts.jsonl` 三大语境 + 子主题完整 (与 p22 列表 1:1)

教材层 (P1-P6):
- 14 册教材 100% 切出 Unit, 每册 Unit 数与目录对齐 (人工抽样 4 册)
- 教材词表 → CefrVocab 命中率 ≥ 90% (剩余 10% 是各地扩展 200 词或专名)
- 短语/句型抽取交集召回 ≥ 70% (人工对 1 Unit, 双模型对比)
- 语法点 → GrammarItem 100% 命中 (任何自造名禁止)
- 所有失败案例显式记录 (vocab_failed.txt / sections_unmatched.txt / phrase_flag_human.txt), 不静默吃
