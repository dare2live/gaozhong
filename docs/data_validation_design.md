# 数据强验证设计 — 独立重新推导 (2026-06-19)

> 用户立项 (2026-06-19): "数据齐全后派多 agents 把每个试卷都做一遍 = 对本轮数据的强验证; 课标/课本的识别加工也要巧妙设计验证方案, 确保正确准确 — 这是知识图谱关联与教程生成的前提。"
> 配 `data_accuracy_check.py`(D0) + `junior_accuracy_check.py`(初中 D0) + `cross_verify_pdf.py`(关键词命中) 用。本文档定义**第三类**验证: **独立重新推导**。

## 0. 为什么需要第三类验证 (现有门的盲区)

现有三门都是 **"对已落库数据自检"** 型, 不重读第一手源:
| 门 | 验什么 | 盲区 |
|---|---|---|
| `data_accuracy_check`(D0 26项) | 计数/卷型/截断/provenance/孤儿 | 不重新从源提取比对 — 提取时就错的值它认不出 |
| `junior_accuracy_check`(F1-F9) | 白名单命中/计数区间/题型分段/答案合法 | 同上: 白名单能收垃圾(ai/gif)、漏真词(app); 不重读源 |
| `cross_verify_pdf` | DB 词 ∈ PDF 词集(≥60%) | 关键词命中, 非语义; 不查值对错(选项错位/答案误读) |

**实证盲区 (坑23, L-2026-06-19-ZC)**: 2024 答案图我**视觉扫读**得一套答案, 与 PaddleOCR 大面积分歧; 三门**全绿也抓不到** — 因为没有"独立重读源再比对值"的环节。这正是本设计补的洞。

## 1. 第一性原理: 验证 = 独立重新推导, 不是自检

**真相源 = 第一手源**(答案图/页图/课标 PDF/课本 PDF 的像素与文本), **不是派生 jsonl/DB**(可能撒谎的二手货)。
强验证 = **另一个独立 agent 不看 committed, 从源重新推导一遍, 再 diff**:
- 独立性 (坑16): 不锚定我的结果; agent 先写下自己的读数, 再打开 committed 比对。
- 双源 (坑23): 低清图 = **裁剪放大视觉精读 + PaddleOCR** 两源, 分歧项必第三次裁决 (视觉是第二独立源, 不用同一 OCR 自证)。
- 对抗确认 (坑16): 任何分歧再派**第三个** agent 只读争议项裁决"是 committed 错还是校验员读错"(false_alarm), 不附和不盲信。

## 2. 验证切片 (每片 1 独立 agent, 从源重推导)

| 切片 | 第一手源 | 比对目标 | 重点 |
|---|---|---|---|
| zk2024-answers | `data/junior_high/exams/2024_liaoning/11.png` | exam_questions.jsonl answer | 全45答案(MCQ字母+语篇填空词) |
| zk2025-stems | `2025_liaoning/p1..p8.jpg` | exam_questions.jsonl type/options/kaodian | 题型分段+完形选项+语篇填空考点 |
| gaokao-ln-provenance | DB + `data/external/`(EOL/GAOKAO-Bench/PDF) | exam_questions 辽宁行 | provenance 真实性(smoking-gun) + 卷型矛盾 |
| curr-L2-小学 | 义务课标 PDF p94-103 | curriculum_vocab 小学 + _vision_l2.txt | 抽样命中率/漏词 |
| curr-L3-初中 | 义务课标 PDF p105-134 | curriculum_vocab 三级 | 抽样页全词 + glyph 误解码 |
| curr-grammar | 义务课标 PDF p144-148 | grammar_items.jsonl(71) | 条目数/层级/understand_only |
| hujiao-vocab | 沪教 7a..9b.pdf 词表页 | hujiao_vocab.jsonl(926) | 抽样词 + 待OCR占比合理 |
| hs-textbook-sample | waiyan/renjiao PDF + DB | units/unit_vocab_intro/section_text | 单元边界/词归属/正文污染 |

## 3. Agent 契约 (delegation contract)

- **输入**: 1 切片的第一手源路径 + 比对文件路径 (不先喂 committed 值)。
- **工具**: Read(图/PDF 视觉, 最强独立源) + Bash(`ocr_image` CLI 裁剪放大 + PaddleOCR; pdfplumber; duckdb)。
- **机械复用**: `backend/services/data_sources/extract/ocr_image.py`(坑23 固化): `crop_and_upscale`+`paddleocr_lines`+`reconcile_readings`。视觉精读由 agent 做。
- **返回**: `{slice, source_read, derived_summary(独立读数), discrepancies[{item,committed,rederived,severity}], verdict}`。
- **禁止**: 写库/改文件/猜值(不确定标 UNSURE)。
- **对抗层**: 有分歧 → 第三 agent 只裁决争议项 → `{confirmed_errors, false_alarms, final_verdict}`。

## 4. 怎么跑 / 复跑

- Workflow: `gaozhong-data-strong-validation` (脚本存 session workflows/scripts/)。每次新获取数据后**重跑该切片**。
- 控制器(主对话)收 confirmed_errors → **每条走"数据教训三件套": 改单一计算点 + 改已落库数据 + 加 gate 断言防回归**(坑1)。
- false_alarm → 记录(校验员自身读错), 不改数据。

## 5. 与 D0 门的关系 (坑17: 新验证也要入门)

强验证 = **periodic 深度复核**(获取/重提取后跑), D0/junior gate = **每次 stop 的快门**。
强验证发现的真错 → 修复后在 D0/junior gate 加对应断言, 让快门以后也能抓 (一次深查 → 永久护栏)。
**门测 floor(已落库自洽), 强验证测 source-fidelity(提取是否忠于源)** — 两者互补, 都要 (坑12 延伸: 绿门≠提取忠实)。

## 6. 验证结果 (本轮 wf_9d0ef21a-35b, 2026-06-19, 14 agent/96万token)

**2 切片干净 (独立重推导确认正确)**: ✅ zk2024-answers (我裁剪放大OCR×视觉的答案全对) · ✅ hs-textbook-sample (高中外研/人教单元边界+词归属+正文无污染)。

**6 切片报真错 (对抗 agent 确认 + 我自核机制确认)** — 修复进度:

| # | 切片 | 真错 | 根因 (我自核) | 状态 |
|---|---|---|---|---|
| B1 | gaokao-ln-provenance | 2024辽宁卷 local_pdf(9)+gbu24(6) **同卷双源重复入库** =15 应=9 | 内容级重复, exact-string去重漏(两源文本微差) | ✅修(656c→) exam.py LOCAL_PDF_LIAONING_YEARS supersede + D0断言"2024/2025辽宁无GAOKAO-Bench重复" + 重建2024辽宁=9 |
| Z1 | zk2025-stems | OCR丢首位'1' (Q14/15/16→4/5/6) → Q4-7错位/丢; 选项以A-E大写开头被吞 | `_add_opts` 正则 `[^A-E]+?` bug + OCR题号碰撞 | ✅修 _add_opts marker-based重写 + 四选一仅A-D + OCR数字修正; Q1-16全4选项(修复11题); D0/junior绿。**五选四17-20待补(task#19)** |
| L3a/b/c | curr-L3 | `ame`/`fu`垃圾 + `app+application`缩写展开重复 + AmE变体(color)重复 | `_cross_validate` 的 `(ocr & real)` 把OCR读到的括号gloss当真词加 | ✅修(官方口径核对附录: 词头才是词条, `(=application)`/`(AmE color)`是注释) extract_paren_words 减单词变体/展开(跳多词防误删physical) + _GARBAGE去ame/fu; 1689→1660趋1600; F2c断言锁; stage_refined重生成F8绿 |
| H1 | hujiao-vocab | 15条 zh_def 截断 (`人人；所有人`→`人人；`) | **文本层源头即截断**(CID腐蚀), 提取忠于损坏文本; 未识别尾随；标待OCR | 📋task#18(低, 释义非词头) |
| L2a/G1 | curr-L2/grammar | `ice cream`/`ping-pong`多词漏 + 2条label字符截断 | 分词按空格拆 / _strip_plus剥inline+ | 📋task#20(低) |

**误报 (对抗层裁掉, 不改数据)**: curr-grammar引号类型/疑问句子项(非硬错) · hujiao元统计项 · curr-L3 `if`(真词非碎片)/`amE`大小写。

**关键确认**: 我刚提交的 **2024中考答案 + 高中教材 = 独立验证全对**; 错误集中在 **OCR派生的2025题面 + 课标三级提取过度/垃圾 + 沪教损坏文本层 + 高考跨源重复** — 都是"提取忠实度"问题, 三门(测自洽)抓不到, 正是强验证的价值。

> 修复纪律 (每条三件套): 改单一计算点(提取逻辑) + 改已落库数据(重跑) + 加 gate 断言(D0/junior 防回归)。逐条 commit。
