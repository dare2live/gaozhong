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

## 流程沉淀 (元 lesson)

### M-1 改代码前必走 codegraph + complexity
PreToolUse hook 已注册, 触发条件: backend/services|db|api/* 改动. 模式: lines>250 / funcs>15 / fan-in>3 / CC>10 函数 ≥3 时强提示 codegraph.

### M-2 commit 前必跑 init_db 全审计
DB 重建 < 3 秒, audit 全跑, 出 audit_findings 表. 任何 FAIL 应在 commit message 解释或修.

### M-3 数据问题先入 audit, 后修
不要绕过. 发现脏数据先加 audit_findings 报 FAIL, 再修 extractor / load 逻辑. 这样下次回归就有自动 detector.

### M-4 项目宪法 §1.5 数据基石优先
任何"加 LLM / 加新模型 / 改前端" 冲动都先 push back 回数据源完整性. 见 gaokao 项目反例 (5 session 才到位).
