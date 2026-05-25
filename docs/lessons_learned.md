# Lessons Learned — 治理 / 流程 / 反例沉淀

> 用户 2026-05-23 强约束: "持续总结经验教训写到文档里, 可以建立 hook 的就从流程和系统层面治理".
> 凡是踩过的坑必须写一条 L-编号, 含 (1) 现象 (2) 根因 (3) 自动化兜底 (hook/audit/test).

---

## L-2026-05-23-A · vocab extractor 把"lesson#" 误当 "Unit#"

**现象**: `extract_vocab_intro` 抽 1842 行, 但 unit_number 出现 7, 14, 21, 24, 44, 52, 69 等远大于实际 Unit 上限 (外研每册 6 Unit). 导致 build_introduces_word 时大量 src=unit:waiyan/bixiu_1/U24 — 这种 unit 节点不存在, graph_edge_validity FAIL.

**根因**: 我误读教材排版. "Words and expressions" section 实际是按 **"UNIT 1 / UNIT 2 ..." 标头分段**, 每 Unit 一组词条; 而**行末数字** (regex 抓的那个) 其实是该词条出现的 **lesson 内序号 / 段落号**, 不是 Unit 编号.

**自动化兜底 (已上线)**:
1. **graph_edge_validity audit** — `audit/graph.py` 跑 edges.src/dst 必须 in nodes, 立刻抓出 unit:U24 不存在
2. **vocab_alignment audit** — `audit/textbook.py` 报 extractor 召回率 (validated rows / raw rows)
3. **links/build_introduces_word INNER JOIN units 过滤** — 临时止血, 不让脏数据污染 graph
4. **lessons_learned.md** 本条记录, 给后续 session 看

**永久修法 (待 STEP 2 第三刀)**: 重写 `_parse_entry_line`, 用 "UNIT N" 标头切, 不靠行末数字读 Unit.

**教训**: 抽 PDF 前必须实测样本 ≥ 5 行, 验证 regex 各 group 语义. 不能凭"看起来像" 推断.

---

## L-2026-05-23-B · canonical 漏建 subject 节点 → edge 引用悬空

**现象**: `links/build_allowed_in_ln` 建 `publisher → subject:英语` 8 条 edge, 但 subject 节点没建过.

**根因**: canonical.build_all 早期遗漏 "subject" 这个常量节点类型.

**自动化兜底**:
1. **graph_edge_validity audit** — 立即抓出 8 条 missing dst
2. 同上, 用 audit 抓 unit 类型悬空 (本条修 subject 节点添加)

**永久修法**: canonical.build_all 加 `subject:英语` 节点 (已上线).

**教训**: 任何 `links/build_X` 新增 relation 必须确保 src/dst node_type 在 `ORPHAN_TOLERATED_TYPES` 名单中 OR 已有 canonical 建节点逻辑. 加 relation 是双工程 — 必涉及 nodes + edges 双侧.

---

## L-2026-05-23-C · audit.py 单文件 god-module

**现象**: backend/services/audit.py 241 L, 接近 250 god-module 阈值, hook 提醒.

**根因**: 多个独立审计函数堆一文件.

**自动化兜底**:
1. **PreToolUse hook** (`scripts/precode_review_hook.sh`) — 改 backend/services/* 时输出 size + CC + fan-in 提醒
2. **code_size audit** (`audit/codequality.py`) — 跑 init_db 时一并检查所有 .py size, >250 WARN, >400 FAIL
3. **code_complexity audit** — 同上, 全扫 CC>10 函数

**永久修法**: 拆成 audit/ 包 (8 个文件), 每个 < 120 L. 已上线.

**教训**: 同类操作不要堆一文件. 一个文件超 200 L 自检: 能否按"概念" 拆开?

---

## L-2026-05-23-D · vocab.py 拆函数前 CC=15 / 14

**现象**: vocab.py 写完, complexity_check 报 `extract_vocab_intro` CC=15, `_find_section_pages` CC=14. 都超 10 阈值.

**根因**: 一个函数干太多事 (try outline → fallback text → 解析行 → dedup → 输出 4 in 1).

**自动化兜底**:
1. **hook stdlib ast 算 CC** (complexity_check.py) — 不用装 radon
2. **code_complexity audit** — init_db 末尾报 hi CC 函数列表, 入 audit_findings

**永久修法**: 抽 `_section_pages_from_outline` `_section_pages_from_text` `_parse_entry_line` `_page_text` 4 个 helper 函数. 主函数降到 CC=6. 已上线.

**教训**: 写 extractor 类函数时, 把"找位置 / 解析行 / 后处理" 三段必拆 helper. 一气呵成 = god-function.

---

## L-2026-05-23-E · 外研版 xuanze_3/4 抽 0 unit

**现象**: textbook unit 召回 65/85 = 76%. 其中 waiyan/xuanze_3 + xuanze_4 抽 0 unit.

**根因**: 这两册无 PDF outline, regex `^UNIT N` 在页首也不命中 (扫描排版?).

**自动化兜底**:
1. **textbook_units audit** — 报告 per-vol units 数, < 4 时 WARN, = 0 时近 FAIL
2. **goal.md** 列 hotspot 待补

**永久修法 (待)**: 加第三策略 (内文 grep "UNIT N TITLE" 非页首, 或者 PDF text bbox 用 pdfplumber). 留 STEP 2 第三刀.

---

## L-2026-05-24-F · vocab extractor 漏抓 30-50% — "跑通" 不等于"数据准确"

**现象**: 用户 2026-05-24 问"数据治理到位吗", 跑真数据发现:
- 课标 3000 词 + 200 扩展 ≈ 3200, 实际外研抽 2025 / 人教 1644
- 某些 unit 仅 3-5 词 (bixiu_2/U3/U4) — 明显异常
- 整 7 册总词数比应有的低 30-50%

**根因**: vocab 抽器跑通 = 跑出 1842/1904 行, 数字够大没人怀疑. 但**没和"理论应有数"对账**.

**自动化兜底**:
1. **新 audit_vocab_per_volume_expected** — 每册 ≥ 200 词 (高一基础) / ≥ 300 (高二) / ≥ 250 (高三选必), 不达 FAIL
2. **vs_curriculum_total** — 7 册累计 ≥ 2800 词 (留 200 弹性), 不达 FAIL
3. **每 unit 范围 30-150 词** — < 10 词 WARN

**教训**: 任何"数据完整性" 检查不能只看"有数", 必须有**期望基线 anchor**.

---

## L-2026-05-24-G · 前端 3 页各自重写 — 加新页时偷懒

**现象**: 用户 2026-05-24 问"前端是否按统一框架优化", 实测:
- `index.html` 用 `app.js` (424 L)
- `teacher.html` 完全 inline JS + CSS, 238 L
- `student.html` 完全 inline JS + CSS, 129 L
- `fetchJSON` / `tagChip` 渲染 / table 渲染 重复 3 遍
- navigation / header / footer 不一致

**根因**: 我加 teacher.html 时图省事, 没看现有 app.js 是否能扩.

**自动化兜底**:
1. **PreToolUse hook 扩**: 改 frontend/*.html 时, 检测 inline `<script>` 块 > 80 L 或 inline `<style>` > 30 L → BLOCK
2. **新 audit_frontend_dupe** — 扫所有 html, 检 fetch( 出现 ≥ 2 次未走 common.js → WARN
3. **新建 frontend/_layout.html** + `common.js` + 强制注入式 header

**教训**: 新页面 = 新隐性 N 倍维护成本. 第二个页面诞生时就要抽 common.

---

## L-2026-05-24-H · 命题"趋势"用 raw count 假装"模型"

**现象**: 用户 2026-05-24 问"命题风格趋势是否研究了更适合的模型", 实测:
- `backend/services/trend.py` 只做 token 词频年聚合
- 没做时间序列趋势 / 主题演化 / 题型分布回归 / 难度年变化
- 文档 `docs/tooling_for_exam_analysis.md` 列出 sklearn/statsmodels 但**没用**

**根因**: 数据有, 但"叫做趋势" 容易, "真用模型分析" 难, 我偷懒.

**自动化兜底**:
1. 写一个 `backend/services/trend/model.py` 真上 sklearn 或 numpy 简单线性回归 → docs/exam_trend_analysis.md 必须有真模型输出
2. **新 audit_trend_model_substance** — 检查 trend service 是否有 import sklearn 或类似真模型, 没有 WARN

**教训**: 任何"分析 / 趋势 / 智能" 词都要被怀疑是否真做. 取个 fancy 名不等于做了.

---

## L-2026-05-24-I · 经济学人风格只抄配色, 没抄结构

**现象**: 用户 2026-05-24 问"研究了经济学人页面吗", 实测:
- 我做了: 红蓝双色 + Georgia serif 标题 + 细边 card
- 真 economist.com: sticky chart + drop cap + inline citation + annotation overlay + minimalist chart axis + 'most-read' rank box
- 我做到 30% 表面

**根因**: 借鉴别人的设计要看**结构**和**信息密度规则**, 不是配色字体. 配色易抄, 信息架构难学.

**自动化兜底**:
1. 列 docs/design_reference_economist.md, 列经济学人 10 个标志元素 + 我做了/没做
2. 任何"借鉴 X 风格" 任务必须先写 reference doc, 列 10 个元素, 不能直接动手

**教训**: 设计借鉴 = 拆解 + 选项 + 验证, 不是抄表面.

---

## L-2026-05-24-J · "形式 vs 实质" 系统性盲区

**现象**: 用户 2026-05-24 一次问 4 件事, 全都是"形式做了实质没":
- 数据治理 (10 项核查 0 做)
- 跨年度覆盖 (没算)
- 命题趋势模型 (raw count 假装模型)
- 经济学人风格 (浅借鉴)
- 深度交叉关联 (API 通, UI 没)
- 高考考点覆盖 (没算)

**根因**: 我倾向"跑通即完成", 不主动跑"是否真有效" 二阶验证.

**自动化兜底 (核心)**:
1. **Stop hook**: Claude 报 "完成" 前必须自检:
   - 数据 audit 0 FAIL?
   - 提到的"模型 / 趋势 / 智能 / 准确" 是否有真实证?
   - 提到的"借鉴 / 学习 / 风格" 是否有 reference doc?
   - 提到的"覆盖率 / 召回率 / 命中率" 是否有真数据 vs anchor?
   不通过 → 不允许 stop, 退回继续工作
2. **PR checklist 文档** (docs/pr_checklist.md): 完成任何"feat:" commit 前 5 项必走

**教训**: 我对自己的工作没有"二阶验证" 习惯. 必须 system 强制.

---

## 流程沉淀 (元 lesson)

### M-1 改代码前必走 codegraph + complexity
PreToolUse hook 已注册, 触发条件: backend/services|db|api/* 改动. 模式: lines>250 / funcs>15 / fan-in>3 / CC>10 函数 ≥3 时强提示 codegraph.

### M-2 commit 前必跑 init_db 全审计
DB 重建 < 3 秒, audit 全跑, 出 audit_findings 表. 任何 FAIL 应在 commit message 解释或修.

### M-3 数据问题先入 audit, 后修
不要绕过. 发现脏数据先加 audit_findings 报 FAIL, 再修 extractor / load 逻辑. 这样下次回归就有自动 detector.

### M-4 项目宪法 §1.5 数据基石优先
任何"加 LLM / 加新模型 / 改前端" 冲动都先 push back 回数据源完整性. 见 gaokao 项目反例 (5 session 才到位).

### M-5 用户提醒前的盲区 (元元教训, 2026-05-24)
我重复 3+ 次靠用户问出"形式 vs 实质"问题. 不可接受.
- 解决: Stop hook 自动跑 "claim vs evidence" 自查
- 解决: 任何"完成" 报告前自问 5 问 (是否跑过 init_db / CC 全清 / 前端复用 / 数据 vs anchor / 真模型还是 raw count)
- 解决: docs/pr_checklist.md 系统化

### M-6 不接受 "下次我注意" 类承诺
重复 ≥ 2 次的失误必须落 hook / audit / test, 不靠口头. 用户 2026-05-24 原话: "可用 hook 建起来的就从流程上系统上建好, 确保后续可持续使用, 而不是每次都要我提醒".

---

## L-2026-05-25-K · 粗粒度数据 ≠ 细粒度分析 — 56 块伪装成 337 题

**现象**: trend_engine 用 22 考点 × 7 年做趋势分析, 报 "七选五↑最快". 细粒度标注后发现七选五实际↓微降, 冠词介词↑才是真趋势.

**根因**: exam_questions 存的是"大题块" (一条=一整篇阅读含 4 题), 但分析当成"一道题"处理. 22 考点的频次被大题块膨胀 — 一块阅读同时命中 5 个考点, 实际只有 4 道子题.

**自动化兜底**: fine_grain_annotator.py 拆 "【N题详解】" 到逐题, 337 条真实子题.

**教训**: 数据粒度决定分析质量. 不拆到逐题就跑模型 = 垃圾进垃圾出. 宪法 §8 已加逐题入库标准.

---

## L-2026-05-25-L · 答案 B 偏 76% — 手写题目的隐性 bias

**现象**: 全系统审计发现听力 76% 答案是 B, 阅读练习 77% 是 B, 听力独白 100% 是 B. 连续 13 题 B.

**根因**: 手写 yaml 时下意识把正确答案放在 B 位 (人类写作 bias — 觉得 B 是"安全的中间位").

**自动化兜底**: fix_answer_bias.py (待完善); 更重要的是 model_capability_audit.py 应加 P11 答案均匀度检查.

**教训**: 人写内容 ≠ 免审. 宪法 V6 "人工内容免审 = 违宪" 就是为了防这类 bias.

---

## L-2026-05-25-M · 宪法写了但代码没改 — "文档驱动"的陷阱

**现象**: 宪法说 trend_engine 必须用加权回归, 但代码用等权 OLS. 宪法说 7 个内容模块必须检查 constitution, 但 0 个检查. stop hook 反复拦截 "工具和流程实现而不只是写到文档里".

**根因**: 先写宪法文档再改代码, 中间插了其他任务, 导致文档和代码脱节.

**自动化兜底**: model_capability_audit.py 的 weight_compliance 检查 (代码 vs 宪法权重一致性).

**教训**: 每写一条宪法规则, 必须同时写一个检查它的 audit 函数. 文档和代码必须原子提交.

---

## L-2026-05-25-N · 真题 paper_type 错标 — 2021/2022/2023 数据污染

**现象**: gaokao agent 审计发现:
- 2021: 16 条中 8 条是新课标 I 卷 (非辽宁), 被错标为 "新课标 II 卷"
- 2022: 新课标 II 卷完全缺失 — GAOKAO-Bench 只有全国甲/乙卷, 被错标为 II 卷
- 2023: 150 条混了 4 套卷 (I/II/甲/乙), 只有 ~1/4 是真正的新课标 II

**根因**: 初始导入时 `infer_province` 推断逻辑不够严格, 把所有"看起来像"的数据都标成了辽宁新课标 II 卷. GAOKAO-Bench 的 category 字段没有被正确解析.

**影响**: 趋势模型训练数据有 ~50% 是错误卷型 → 所有趋势分析结论可能有偏差 → 基于此生成的内容全部不可信.

**自动化兜底**: cross_validation_report.json (交叉验证); model_capability_audit 应加 paper_type 验证维度.

**教训**: D0 100% 准确率不只是"数据入库了", 而是"每条数据的每个字段都正确". paper_type 错标 = 整个模型失效. 宪法 §8 数据获取规范必须包含 paper_type 验证.

---

## L-2026-05-25-O · infer_question_type 三个题型标反 — 全部真题题型标签错误

**现象**: 交叉验证 agent 发现 exam.py 的文件名→题型映射全标反:
- cloze_test (实际是七选五) → 标成了完形填空
- cloze_passage (实际是语法填空) → 标成了完形填空(七选五/语篇)  
- fill_in_blanks (实际是完形填空) → 标成了语法填空

**根因**: 文件名与题型的对应关系靠猜, 没有验证. cloze_test 听起来像完形填空, 但 GAOKAO-Bench 的 cloze_test 实际是七选五格式 (选项 A-G).

**影响**: 56 条 2021-2023 真题的题型全错 → 题型分布分析全错 → 趋势模型在错误的题型上做趋势.

**自动化兜底**: cross_validation_report.json; 应在 init_db 中加题型格式校验 (七选五应有 A-G 选项, 完形应有 ABCD).

**教训**: 文件名不是 ground truth. 必须看实际内容 (题目格式/选项/答案) 来判断题型. 宪法 §8 "交叉验证" 就是为了抓这类错.

---

## L-2026-05-25-P · 辽宁卷型历史全错 — 2010-2014 自主命题, 2021-2022 完全缺失

**现象**: 深度审计发现数据污染远超预期:
- 2010-2014: 辽宁用自主命题, 不是新课标II → GAOKAO-Bench 的新课标II是其他省份的
- 2021: GAOKAO-Bench 完全没有新高考II卷, "解析版"实际是全国甲卷 (验证: Landscape Photographer = 甲卷)
- 2022: 新高考II卷完全缺失, GAOKAO-Bench 只有甲/乙卷
- 现有 export 37% 是非辽宁数据

**根因**: 最初导入时假设"新课标II = 辽宁", 没有验证辽宁实际用的是哪套卷. 辽宁卷型历史:
  2009-2014 自主命题 / 2015-2020 新课标全国II / 2021+ 新高考全国II

**影响**: 模型训练数据严重污染 → 所有趋势分析和考点分布结论无效

**教训**: 省份→卷型映射必须从官方源验证, 不能假设. 宪法 §1.1 "真题是唯一真理源" 的前提是"真题是对的真题".
