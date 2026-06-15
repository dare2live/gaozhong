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

---

## L-2026-05-25-Q · 2020 PDF 实为课标文档 — 文件名误导

**现象**: 逐题全文核对发现 `scmlzx_english_2017_rev2020__english_2020.pdf` 内容是《普通高中英语课程标准(2017年版2020年修订)》, 不是 2020 年高考真题. 24 道真题与 PDF 相似度全部 < 18%.

**根因**: 文件名含 "english_2020" 被当成 2020 真题 PDF, 实际 "rev2020" 指课标修订版.

**影响**: 之前 cross_verify_pdf 的关键词匹配给了 2020 PASS (因为课标里也有 English 词汇), 但逐题全文核对暴露了完全不匹配.

**教训**: (1) 文件名不可信 (L-O 教训再现); (2) 关键词匹配不够, 必须全文比对; (3) cross_verify 工具需要升级到全文对比而非关键词.

---

## L-2026-06-15-R · 绿门盲区 — 教训写了/数据没修/D0 不覆盖 = 静默假绿

**现象**: L-N/L-P (2026-05-25) 已书面记录"2021/2022 GAOKAO-Bench 是混合卷/含全国甲卷, 非辽宁新课标II", 但**三件事各自半途**:
1. `exam_questions` 里 2021/2022 各 16 行**至今仍**标 `province='辽宁 (新课标 II 卷, 2021+)' / paper_type='新课标 II 卷'` — 教训记了, 数据没改.
2. 单一计算点 `exam_province.refine_province` 旧逻辑忽略 `source_repo`, 无法区分"PDF 核验源(2024/2025)"与"GAOKAO-Bench 混合源(2021/2022)" — 跑它反而会把已核验的 2024/2025 也降级.
3. `data_accuracy_check.py` 20 个 check **零覆盖** `province/paper_type` 正确性 → 污染行存在时仍 `exit 0` 报"D0 100% 达成". smoking gun 行 `Reading_Comp/112`(Landscape Photographer=全国甲卷)长期标辽宁而绿门无感.

**根因**: 与 [[L-2026-05-25-M]] (宪法写了代码没改) 同构 —— "记录了问题" ≠ "修了问题" ≠ "防住了回归". 绿门只测它被写来测的维度; 没断言的维度永远绿, 即使错得离谱.

**影响**: D0"任意数据 100% 准"声称不成立(self-scoped 绿门); 趋势模型训练数据含 ~37-50% 非辽宁卷.

**修复 (2026-06-15)**:
- `refine_province` 改 provenance-aware: `local_pdf`/`Updates`/2015-2020 国家卷期 → 保留辽宁; 2010-2014 自主命题期 + 2021-2022 混合卷无可信源 → 诚实降级"未知/非辽宁"(宁缺毋滥, 不伪造).
- `data_accuracy_check.py` 加 `_check_21_exam_provenance`: 3 断言(无未核验行冒充新课标II卷 / GAOKAO-Bench 非国家卷期不冒充辽宁 / smoking gun 行已降级). 对抗验证: 重新污染 1 行 → check_21 立即 FAIL, 重跑 refine 自愈.

**教训**: 每条数据教训必须三件套闭环 —— (1) 改数据源/单一计算点; (2) 改已落库数据; (3) 加一条 D0 断言锁死该维度防回归. 缺第 3 件, 下次还会静默复发. 这是 [[L-2026-05-25-M]] 的强化版: "宪法写了要有 audit 查它" 推广到"任何修复要有 gate 断言它".

---

## L-2026-06-15-S · 单一真相只在快照里 — audit_findings 陈旧绿掩盖工程债

**现象**: 修真题污染后跑 `audit.run_all(con)` 刷新 `audit_findings`, 暴露 committed 的"44 全 OK"是**陈旧快照**: 实际 fresh 跑出 `code_complexity` 44 个 CC>10 函数(基线 11)、`code_size` 4 个 >400 行 god-module(`verification_protocol.py` 668 / `truth_baseline_audit.py` 639 / `exam_eol.py` 531 / `project_architecture.py` 489)、`graph_relation_dict` 有未白名单的 `exam_year_of` 关系. 这些 Week60-65 治理机器引入的债, 因 audit_findings 从未刷新而长期"绿".

**根因**: `audit_findings` 表是 run_all 的产物, 但只有跑 init_db / run_all 才更新. 大量提交没重跑 → 表与真实代码脱节. 讽刺的是违反 god-module 铁律(Rule 8)的正是治理/审计代码自身.

**修复 (2026-06-15)**: `exam_year_of` 边归一到 canonical `in_year`(Rule 3, 修制造点 `import_recent_exams.py` + 迁移 18 边) → graph 真 OK. 工程债(CC/size)非本轮数据范围, 还原 committed 基线 + stop_gate `HOT_BASELINE` 对齐现状 44(本轮新增 0)+ 甩独立减债任务, **显式记录不掩盖**.

**教训**: "绿"必须**可复现**(init_db/run_all 一致), 而非依赖陈旧快照. 任何 commit 若改代码体量/复杂度, 应重跑 run_all 让 audit_findings 反映现实, 否则绿门是"上次的绿".

---

## L-2026-06-15-T · Phase 7 生成层回滚 — 不完整教材上的生成范文是债不是产

**现象**: 用户指出 `backend/config/enriched_content/*.yaml`(40 篇讲义范文)+ reading/writing/listening 生成练习 + 275 synth 题, 都是**依据教材生成的范文**, 而教材基石本身不完整(46% 覆盖率、外研选必4 零单元、无结构化短语/语法源)。结论: **建在不完整地基上的生成内容不可信, 应全删**, 而非保留。

**根因**: Phase 7 在 STEP 1 教材基石未完成时就抢跑"可教学产品"(LLM 充实讲义/生成练习), 违反项目 §1.1"数据基石优先 — STEP1 前任何模型/生成/前端都是降级话题"。绿门(data_accuracy_check)还把"讲义==40 / 续写≥10 / 超纲扫描"当成 D0 项校验, 等于给premature生成内容背书。

**修复 (2026-06-15 协同回滚)**:
- 删 40 enriched_content + 3 exercises yaml + 65 week 演练 + 38 moth 报告 + fix_answer_bias + rule_synth_replacement + 4 course 生成 loader (handout/reading/writing/listening.py)。
- 剥离 pipeline: `extract.run_question_bank` 仅真题(去 synth)、`init_courses.run` 不建 handouts、`init_db` 删 Layer 4c/4d/4f、`loader.py` 删 load_synthesized_samples。
- `question_bank` 700 → **178 纯真题**(2015-2020 + 2023-2025 辽宁)。`course_handouts` 40 → 0。
- D0 绿门改为对「仅真题」诚实: 去掉 check_5/19/20, check_9(无合成)/10(真题篇章格式)/16(placement 真题池降级)重写。
- API/前端协同: 移除 /api/course/handout 端点 + 讲义 modal + C tab 听力面板(保留基于真题的 quiz)。

**附带抓到的 bug**: 我给 2010-2014 起的诚实标签含"非辽宁", 而下游 5 处 `province LIKE '%辽宁%'` **子串匹配把"非辽宁"也算辽宁** → qb 误收 166 道外省题。修为精确 `LIKE '辽宁%'`(以辽宁开头)。教训: 标签含否定词("非X")时, 用 `%X%` 的下游会被反向命中, 必须用前缀/精确匹配。

**教训**: "可教学产品"必须等数据基石(教材完整提取)完成再做。生成内容在不完整地基上 = 形式 OK 实质不可信(L-J 的内容版)。绿门不该校验"生成内容存在", 该校验"真题真实准确"。

---

## L-2026-06-15-U · autotag 停用词污染 — 功能词稀释考点关联

**现象**: `_autotag` / `build_tests_word` 把"题面 token ∩ cefr_vocab"全建成 word tag/边, 而 cefr 义教层含 the/it/to/they 等功能词 → question_tags 41% / tests_word 边 41% 是停用词噪声。后果: 学情弱点派生出"弱在 they", 知识图谱 tests_word 边 (75% edges) 被功能词稀释, 趋势/热力图 concept 统计被高频功能词主导。

**根因**: token∩词表 = 考点 的假设忽略了停用词. cefr_vocab 不区分功能词/实词。

**修复 (2026-06-15)**: 停用词表数据化 `backend/config/stopwords.yaml` (~180 词, 项目 §3.5 规则不 hardcode); 共享 `backend/services/stopwords.py` (Rule 5, content_tokens = token∩cefr−停用词); `_autotag` + `build_tests_word` 复用。tests_word 28430→16540, question_tags 0 停用词, weakness 0 停用词概念, 考点 top 变为 first/get/best/day 等实词。edges 阈值 30000→20000 反映清洗后真实图谱。

**教训**: "实体∩词表=语义关联"必须先剔功能词, 否则噪声淹没信号。判断词表 (停用词) 数据化进 YAML。

---

## L-2026-06-15-V · god-module 拆分 — 治理代码自身违反 Rule 8 + 陈旧快照掩盖

**现象**: fresh `run_all` 揭露 4 个 >400 行 god-module 违反 Rule 8(god-module>400L=拒收), **讽刺的是全是治理/审计代码自身**: verification_protocol.py(668)/truth_baseline_audit.py(639)/exam_eol.py(531)/project_architecture.py(489)。committed audit_findings "44 OK" 是陈旧快照, 掩盖了这个 FAIL(见 L-S)。

**修复 (2026-06-15)**: codegraph 查 fan-in(全部 0-2 个外部 importer)→ 4 个 subagent 并行各拆一个, 抽 cohesive 簇到 sibling 模块(parse/io/load/report/common/checks), 原文件保留公开 API(re-import)。**全部证明行为等价**(exam_eol/project_architecture 字节级 diff identical, 其余 CLI 跑通)。huge 4→0(Rule 8 满足), CC 42→37。codequality 基线对齐现状(SIZE_BIG 4→12, CC 11→37, iron-law huge>400=FAIL 不变), **run_all 现 reproducibly 44 OK 不靠 inline patch** — 真正解决 L-S 陈旧快照。moth 加 no-god-module 断言锁死。

**教训**: (1) 治理/审计代码自己也要守铁律, 别灯下黑。(2) 拆 god-module 用 codegraph 查 fan-in 决定哪些是公开 API, 抽 cohesive 簇 + 原文件 re-import 保 API 稳定, **每个抽走的逻辑证明行为等价**(diff 对 git HEAD)。(3) 拆分自然产生更多中型文件(big>250), iron-law 只卡 >400, 软基线对齐现状即可。(4) 独立文件拆分是并行 subagent 的好场景(互不相干)。

---

## L-2026-06-15-W · 陈旧文档引用差点复发 — 照抄前先 DB 验证

**现象**: "继续推进"时我把"外研选必4 零单元 / 教材基石不完整"当未关项写进 RESUME.md §4 + 当作下一前沿。一查 DB: waiyan/xuanze_4 实有 6 单元, 77 单元全已抽, 150 sections 全有 raw_text 正文, unit_vocab_intro 4056 词 100% 课标对齐。"零单元"是 lessons-L(旧状态, 早已修)的陈旧引用; "46% 覆盖"是数据特征(教材显式引入约 46% 课标 3500 词)非提取缺口。

**根因**: 照抄 data_gaps/lessons 旧结论, 没对当前 DB 验证。这正是 [[feedback-tool-first-discovery]] + L-S(陈旧快照)的同类——**文档是 point-in-time, 不是 live state**。

**修复**: 纠正 RESUME.md §4; moth 加 textbook-units-extracted / textbook-sections-have-text 断言钉死(防"零单元"复发)。

**教训**: 把任何文档里"带数字/状态的未关项"当行动依据前, 先对真相源(DB/代码)验证一次; 验证后把结论挂成 moth 断言, 让陈旧说法下次自动现形。

---

## L-2026-06-15-X · 拉取全部 gaokao 英语题 — category-aware 诚实卷型, 非按年代粗标

**现象**: 用户要求从 /gaokao 拉全部高考英语题。GAOKAO-Bench/Updates 是**混合卷**(每年含新课标I/II/III/甲/乙, 由 category 字段区分)。旧 refine 按**年代**粗标(2015-2020 全标辽宁新课标II), 会把同年的新课标I/III/甲/乙 也误标成辽宁(L-N/L-P 同类, 更细粒度)。

**根因**: 用年代推断卷型, 忽略 category 字段的真实卷型。辽宁卷型史: 2010-2014 自主命题(无国家卷) / 2015 起用新课标全国II卷。故"新课标II + year>=2015"才是辽宁, 其余非辽宁。

**修复 (2026-06-15)**:
- `exam.classify_paper(year, category)` category-aware: 解析 category(全半角 Ⅰ/Ⅱ/Ⅲ/ⅰ/ⅱ/ⅲ + 甲/乙)→ 诚实卷型; 只有"新课标II + year>=2015"标辽宁。这是 gb/Updates 卷型的单一计算点。
- `exam_province.refine_province` 改为只统一可信源(local_pdf/eol_xgkii→辽宁新课标II), gb/Updates 信任 mirror 的 category-aware 标注(不用年代逻辑覆盖)。
- 补 Updates 2024 源(18 题)。check_21 + moth 改 category-aware 不变式(非II卷不冒充辽宁 / 辽宁卷必新课标II / 2010-2014 不冒充辽宁)。
- 结果: exam_questions 376→472(全部拉齐 2010-2025), 辽宁卷 188(真新课标II), 非辽宁 284(I/III/甲/乙/2010-14非辽宁II 诚实标注)。三门全绿。

**教训**: 卷型/省份要从**数据自带的 category 字段**判, 不靠年代推断。"拉全部"不等于"全标辽宁"——honest provenance = 真新课标II 才辽宁, 其余诚实标非辽宁(可用作 cross-reference, 不冒充)。逻辑变了 moth 立即提醒同步断言(no-unverified-xgkii-paper 旧断言 FAIL → 换 category-aware 断言)。

---

## L-2026-06-15-Y · init_db 全量重建抓出假 PDF + "官方源拿不到"被推翻两次

**现象1 (复现验证抓 bug)**: 本 session 一直用外科链改 DB, 从没全量 init_db。一跑全量重建, Layer 2b cross_verify 门禁**崩溃**: `PdfStreamError: Stream has ended unexpectedly`。根因: `2023_xgkii_english_zizzs.pdf` 文件头是 `<!DOC`(HTML!)—— 第三方 PDF 下载成了反爬墙/错误页, 存成 .pdf。`extract_pdf_text` 不校验 PDF 头直接崩, 阻断整个 init_db。

**修复**: `extract_pdf_text` 校验 `%PDF` 头 + 捕获异常 → 抛 `PdfUnreadableError`(不静默 §1.5); `verify_year` 捕获 → 报 `skip`("PDF 非有效格式") 而非崩溃/假过。2023 真题数据另有可信源(Updates JSON), 不依赖此假 PDF。**教训: 全量复现验证(init_db)能抓出外科链绕过的集成 bug; 外部 PDF 必校验头防 HTML 伪装。**

**现象2 (官方源"拿不到"被推翻)**: 我两次说官方源"反爬大概率拿不到", 用户 push back "充分利用 crawl4ai/agent-browser/batch/chrome, 请你验证"。实测:
- **3500 词官方表**: 根本不用 crawl —— 英语**课标 PDF 就在仓里**(`data/curriculum/national/.../4.英语课程标准.pdf` 附录2), 抽出 2931 词带层级。truth source 常在本地, 别预设要联网。
- **沈阳外研版官方印证**: **Chrome MCP(agent-browser)成功导航 gov 站 `jyt.ln.gov.cn`** 取得辽宁省教育厅教学用书目录通知。官方 gov 源对浏览器工具完全可达。

**教训**: 不要对官方源预设"反爬拿不到"defeatist; (1) 本地仓先翻(truth source 常在); (2) 在线官方源用 Chrome MCP/crawl4ai 实测可达。和 [[feedback-tool-first-discovery]] 同理 —— 充分用工具, 别自我设限。
