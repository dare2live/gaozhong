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

## 三层目标 schema (跨版本统一)

```
Textbook (version, volume_label)
└── Unit (number, theme_zh, theme_en, page_start, page_end)
    ├── Section (kind: reading | listening | speaking | writing | grammar | vocab | project | self-assessment, page_range, raw_text)
    │   ├── Sentence (lang=en, source_section, char_offset)
    │   ├── Phrase (canonical_form, type=collocation|idiom|功能表达)
    │   ├── GrammarPoint (label, example_sentence_ids[])
    │   └── Question (prompt, answer, type=multi-choice|fill|essay)
    └── Vocabulary (word, ipa, pos, zh_def, unit_id, frequency_rank, in_3500_list)
```

## 提取 pipeline (按依赖)

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

### P4. 词表抽取 (Words and Expressions / Vocabulary)
- **关键基础**: 这是后续 STEP 3 (高考映射) + STEP 4 (趣味化越纲过滤) 的 ground truth, 必须高质量.
- 词条排版规律: `word [ipa] pos. zh_def` 一行一条, 部分版本前缀符号 (`*` `△`) 表示不要求/选学.
- 解析:
  1. 用 pypdf 切出 vocabulary section 的页范围 (P3 给出).
  2. 正则 `^([a-zA-Z][a-zA-Z\-']+)\s+([\/\[].*?[\/\]])?\s+([a-z]+\.)\s+(.+)$` 抓行.
  3. 失败行单独入 `data/structured/extracted/<version>/<book>/vocab_failed.txt`, 人工校.
- 输出: `data/structured/extracted/<version>/<book>/vocabulary.jsonl`

### P5. 短语 / 句型 / 功能表达抽取 (LLM, 双校验)
- 这是 STEP 2 主难点, 用户反馈"表达方式比单词更重要".
- 输入: P3 给出的 reading/writing 板块 raw_text.
- 提示词关键 (草稿):
  - "只抽**多词单位**: 短语动词 / 固定搭配 / 习语 / 功能性表达 (邀请/拒绝/建议)."
  - "拒绝单词. 单词去 vocabulary.jsonl 查."
  - "每条带原句作为 evidence."
- 双校验: 两个 LLM 独立抽, 取交集 ≥ 0.7 (Cohen κ), 否则交叉评.
- 越纲过滤: 任何抽出的"表达" 中含 vocabulary.jsonl 之外的单词 → 标记 "out_of_syllabus", 待人工裁决.

### P6. 跨版本统一 schema 入库
- DuckDB (单文件, 与 gaokao 项目一致) 或 SQLite, 不引 Postgres.
- 表: textbooks / units / sections / vocabulary / phrases / grammar_points
- DDL 写在 `backend/db/schema.sql`.

## 不打算做的事 (避免范围蔓延)

- ❌ 自训分类器抽板块 (规则 + outline 已够)
- ❌ 自建 OCR pipeline (PDF 已可文本化)
- ❌ 抽 PDF 中的图片 / 听力音频 (STEP 1+2 范围之外)
- ❌ 跨版本 Unit 主题对齐 (STEP 3 任务, 不在 STEP 2)

## 评估指标 (STEP 2 验收门)

- 14 册教材 100% 切出 Unit, 每册 Unit 数与目录对齐 (人工抽样 4 册 cross-check)
- 词表抽取召回 ≥ 95% (人工对 1 册必修一 expected ~300 词)
- 短语/句型抽取交集召回 ≥ 70% (人工对 1 Unit, 双模型对比)
- 所有失败案例显式记录 (vocab_failed.txt / sections_unmatched.txt 等), 不静默吃
