# K12 英语分阶段平台 — 主架构 (第一性原理顶层设计)

> 2026-06-17. architect-controller 全框架 (立法→控制→交付)。本文是**平台级最高设计**,
> 统一高中 (docs/architecture.md 八铁律) + 初中子系统 (junior_high_subsystem_design.md) +
> 核心竞争力 (考点趋势/关联分析)。冲突时: 本文定**为什么/是什么**, 八铁律定**代码怎么写**, RESUME 定**现在到哪**。

---

## 0. 第一性原理 (项目不可再分的本质)

中国学生 K12 (小学→初中→高中) 沿**官方课标脊柱**学英语, 用**官方教材**承载, 受**官方考试** (中考/高考) 检验。
项目的全部价值 = 把这条脊柱建成**一张知识图谱** + 在其上做**考点实证分析**, 使教学"分阶段 / 紧贴考试 / 个性化", 在数据规模上超越人工教师。

**三个不可再分的真相源 (一切派生必溯回)**:
| 真相源 | 定义什么 | 权威性 |
|---|---|---|
| **课标** (义务2022 三级 + 高中2017 义教/必修/选必) | **脊柱**: stage(何时学) + 必学范围 | S (教育部) |
| **教材** (沪教初中 / 人教·外研高中) | **实现**: unit/section + 实际教的词/语法, 按版本/地区 | A (出版社原版) |
| **真题** (中考沈阳省统一 / 高考辽宁II卷) | **检验**: 实际考什么 | S/A (官方/教研) |

其余 (趋势/关联/语义扩展/生成内容) **全是派生**, 无独立真相性, 必溯回上三者 + 带 provenance。

**核心洞察 (用户立意的第一性表达)**: **stage 是统一维**。平台不是"初中+高中两系统", 是**一张图, 每个知识点带引入 stage**, 由此自然导出三种能力 —
- **向下** (compatible): 高阶知道低阶已学 (with/the=义务教育, 不当高中新词)。
- **向上** (preview): 低阶受控渗透高阶 (标 preview, 老师可控, ≤下阶段课标, 不超载)。
- **跨阶段** (expansion): 词义/搭配/语法/思维随 stage 螺旋深化 (power 初中力量 → 高中 power plant)。

---

## 1. 立法层 (Genesis — 不可变, 极硬)

**为何存在**: 成为辽宁/沈阳 K12 英语学习的**单一知识图谱** — 每个 词/语法/主题/考点 锚定其 课标stage + 教材locus + 真题evidence — 使教与学分阶段、紧贴考试、可个性化。

**死亡线 (≤3, 越过即背叛)**:
1. **D0**: 任意数据 + 任意关联 100% 准, 每个 datum 可溯回 课标/教材/真题 真相源; 溯不回标 `unknown`, **绝不假填/不凑数** (§1.3)。垃圾词冒充真词 (审计 F1) = 越线。
2. **不混口径**: stage (小学/初中/高中) / province (沈阳中考≠辽宁高考≠全国) / 卷型 / 教材版本 各自诚实, PIT 对齐 (按生效年份课标/卷制)。复用高中二分推初中 = 越线 (gaokao 卷型坑)。
3. **派生不超越证据**: 趋势/语义扩展/生成内容/造题不得超出语料证据 — 无 押题、无幻觉边、样本量诚实 (分布≥30 / 趋势≥5年每年≥10)。"AI 押中考点" = 越线。

**判断法典 (人话 / 机器话, 可 amend 留 trail)**:
| 法 | 人话 | 机器话 |
|---|---|---|
| stage 单一真相源 | 一个词的阶段 = 哪部课标最早引入 | `stage=min(课标级)`: 二级→小学/三级\二级→初中/必修→高中必修/选必→高中选修 |
| 真相源优先 | 判断对错锚第一手 PDF, 非派生表 | 提取从 PDF; 派生表/快照可能撒谎, 不当真相 |
| 提取鲁棒+诚实 | 抽不干净就 OCR + 交叉验证 + 词典校验; 抽不全标缺口 | text-layer ∧ OCR ∧ 词典门 ∧ extracted_n 透明; 任何 `(cid:`/垃圾片段 = 不入或标待OCR |
| 单一计算点 | 同一提取/派生只写一次, 别处不复刻 | 共享 `textbook_vocab` 核心, 不在 scripts/ 重写 (审计 F6) |
| 双门 | 新数据落地必同时挂 D0 + moth | data_accuracy_check ∧ moth claims; stop_gate 触发器认该路径 (坑17/21) |
| 跨阶段边带证据 | "power 高中扩义"要语料证实才教 | edge.evidence={corpus,n_occur,provenance∈{mined,dual_model,human}}; C级未验证不上教学面 |

**死亡条款 (何信号=系统死)**:
- **感知死**: stage/考点 停止与新课标 (2022改版)、新真题对账。
- **判断死**: stage taxonomy / 考点体系 固化, 世界变 (课标改版/中考改革) 而不 amend。
- **谄媚死**: 产出"惊艳"实为噪声 — 垃圾词当考点 (F1)、巧合共现当语义扩展边、不可信 slope 当趋势。校准铁律: 只按真相源对账 + 教研核实调整, 不按"看着酷"。

---

## 2. Canonical 模型 (一张图, stage 为轴)

**实体 (节点, 先有 PK 再谈关联 — 铁律2)**:
- 知识点: `word` / `grammar` / `theme`(主题语境) — **每个带 `stage`** (小学/初中/高中必修/选修/校本超纲) + `province_scope` (全国课标/沈阳教材/辽宁真题)。
- 容器: `volume`(分册) / `unit`(单元/Module) / `section`(语篇) — 带 `version`(沪教/人教/外研) + `stage`。
- 检验: `exam_question` / `exam_point` — 带 `exam_type`(中考/高考) + `province` + `year` + 卷制 era。

**边 (N:M 走 edges + graph service — 铁律3)**:
- 阶段内: `introduces_word`(unit→word) / `uses_grammar` / `theme_of_unit` / `tests_word`(exam→word, =考过唯一真相, 已收口) / `tests_grammar` / `tests_exam_point`。
- **跨阶段 (平台新增, stage 轴)**: `expands_sense`(低阶词→高阶新义) / `collocates_into`(词→高阶搭配) / `deepens`(低阶语法→高阶深化) / `spirals`(同主题跨阶段复现)。全带 provenance + 语料证据。

**单一计算点**: 派生事实 (stage / 考过 / 越纲 / 趋势 / 跨阶段边) 只在 `backend/services/` 算一次入表; API/前端/脚本/另一 service **不准重写同 JOIN/agg** (铁律1)。

---

## 3. 真相源 → 提取架构 (审计驱动的鲁棒提取)

**问题 (审计实证)**: PDF 是好真相源, 但提取层 LOSSY — CMap损坏 (高中)、CID字体码 (沪教释义)、digit-glyph 误解码、双栏 reflow、`*`超纲标、`[:40]`截断 → 产生**垃圾词 (假真相)** + **丢真词 (缺真相)**。

**第一性原理提取律 (单一计算点, 四重防线)**:
```
PDF ─┬─ text-layer 抽 (pdfplumber 双栏 crop, 可读页主源)
     ├─ OCR 抽 (~/.venvs/ocr PaddleOCR, CID/扫描/伪影页)
     ├─ 交叉验证 (text ∩ OCR; 一致=高置信; 仅一方=核查; 已证可读页 171/171=100%)
     └─ 结构/词典门 (词典校验去垃圾片段; extracted_n 透明; `*`存 supra 标记; `(cid:` 标待OCR)
            ↓
     单一计算点提取器 (backend/services/data_sources/extract/textbook_vocab.py 共享核心,
       沪教/人教/外研/课标 都调; 不在 scripts/ 复刻 — 修审计 F6)
            ↓ emit 带 provenance + extracted_n + 缺口清单 (§1.3 不凑数)
```

**铁律**: 任何提取产物 = `{data, source_pdf, extracted_n, gaps[], method∈{text,ocr,fused}, provenance}`。抽不全报缺口不凑数; 抽脏经词典门拦截; ≥2 方法 (text+OCR) 交叉验证才高置信入库。

---

## 4. 子系统关系 (separate-build, stage-unified, merge-later)

**§6 DB 独立硬约束** + **统一平台目标** 的解 = 三态演进:
1. **构建态 (now)**: 初中 (沪教/义务课标) 与 高中 各自独立建 — 高中 `gaozhong.duckdb` / 初中 `gaozhong_junior.duckdb`, **schema 同构 + stage 列**, 不 ATTACH 不混写。各自 D0+moth 门。
2. **集成态**: stage-aware **VIEW 层** (只读) 跨库统一查 (给定 stage 返回累积集/新增集/渗透集), **非改表非 UNION 进单库**。跨阶段边在集成层算 (读两库, 写边表)。
3. **平台态**: 前端浮窗/学情/备课/趋势 消费集成 VIEW, 按 stage 过滤/渗透/回溯。

> 为何不一开始就单库 stage 列? — §6 独立 + 初中地基未达标 (审计) 不能污染已清高中库; 独立建+独立门, 达标后才经 VIEW 集成, 风险隔离 (mio 地基-上层严格偏序)。

---

## 5. 门 / 证伪架构 (每子系统 + 每跨阶段派生)

| 层 | 门 | 守什么 |
|---|---|---|
| 高中数据 | `data_accuracy_check.py` (D0) + `moth assert` + `stop_gate.sh` | 已有, 46 moth/0 FAIL, 全绿 |
| **初中数据 (待建, 坑17)** | `junior_accuracy_check` (8条: 无垃圾词头/三级数透明/二级505/无cid释义/沪教词量护栏/语法71/stage无orphan/契约登记) + moth junior 断言 | 修审计 F5 |
| 跨阶段派生 | stage_refined 无 orphan; 语义扩展边 provenance + 语料证据门; 趋势 province+卷制+样本量门 (坑12) | 防谄媚死 |
| 触发器 | stop_gate change-detection 认 `data/junior_high/**` + `scripts/*junior*` (坑21 防假阴性) | 改初中产物必触发门 |
| 对抗验证 | 每条修复后注 1 个坏数据 → 门必 FAIL; 自愈 → 绿 | 防绿门假绿 (坑1) |

---

## 6. 核心竞争力层 (跨阶段考点实证分析)

建在干净图谱上的**分析层** (用户反复强调=项目核心竞争力, 非押题而是方向性指引):
- **考点趋势/热力/分布**: province-scoped (辽宁高考/沈阳中考各自) + 卷制分段 + 样本量诚实 + 分层非平均 (坑12)。
- **关联性**: 共现/题材↔考点/词↔考点 边分析。
- **跨阶段新维 (平台独有)**: **中考×高考评估轨迹** — 哪些知识点中考考过 AND 高考考过 = 最高优先级地基; 单考 = stage 专属; 指导"初中必学牢什么"。**语义扩展挖掘** (298候选 → expands_sense/collocates_into 边)。
- **自编教程 / 备课 / 学情**: 消费上述, 按 stage + 考点优先级生成 (词量≤已学stage+课标, §1.2 不偏离)。

---

## 7. 建设路线 (地基优先, A/B/C 映射)

**铁序 (mio 地基-上层严格偏序, §1.1 不可协商)**:
```
Phase 2.6  初中地基修复 + 双门 (审计 F1-F6)  ← 阻断 A/B, 当前必做
   修共享提取器(F6) + 词典门(F1) + OCR坏格&诚实1589(F2) + *召回(F3) + cid诚实(F4)
   + 二级505(F7) + 语法71(F8) + junior_accuracy_check 8条门(F5) + 触发器(坑21)
        │
        ├─ A. Phase3 集成   stage_refined回填 + junior独立DB + stage-aware VIEW层
        ├─ B. 语义扩展边     298候选(去假候选) → 跨stage语料挖掘 → edges (依赖A)
        └─ C. 沈阳中考       2024+省统一卷 (独立性最高, 可与 2.6 并行)
        │
   Phase 4  核心竞争力跨阶段分析 (中考×高考轨迹/语义扩展/趋势) + 前端 stage 浮窗
```
**C 可与 2.6 并行** (中考数据独立, 不依赖初中词表地基); A 依赖 2.6; B 依赖 A。

---

## 8. 工具栈 (发挥项目各工具能力)

| 工具 | 在架构中的职责 |
|---|---|
| `data_accuracy_check.py` + `stop_gate.sh` | D0 强校验门 (每子系统一套) |
| `moth assert` / `moth coupling` | 声称-实况漂移 + 删改前 fan-in/孤儿引用审计 |
| `codegraph query/context` | 改提取器/服务前 blast-radius + 单一计算点定位 |
| `~/.venvs/ocr` PaddleOCR (`ocr-python`) | CID/扫描页 OCR + 文本层交叉验证 (跨项目全局) |
| `sherpa takeover` | 新 session 接手单页对账 (3门+真相源+junior) |
| `scripts.tools.map doctor` | live 状态单一入口 |
| Workflow (多 agent) | 并行审计/对抗复核/设计盲点扫描 (本次审计即用) |
| `architect-controller` skill | 顶层设计/重排 (本文) |

---

## 9. Verdict
**PROCEED**: 第一性原理清晰 (三真相源 + stage 统一轴), 立法层硬 (D0/不混口径/派生不超证据 三死亡线),
canonical 模型单一计算点, 提取四重防线修审计根因, 子系统 separate-build-stage-VIEW-merge 解 §6 张力,
门覆盖每子系统 + 跨阶段。**即时下一步 = Phase 2.6 地基修复 (C 并行)**, 然后 A→B, 终到 Phase4 核心竞争力跨阶段层。
