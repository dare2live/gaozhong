# K12 英语分阶段平台 — 主架构 (第一性原理顶层设计) · v2

> 2026-06-17. architect-controller 全框架 (立法→控制→交付)。**v2 经 3 视角对抗评审 (第一性/务实/盲点) 大改定稿。**
> 平台级最高设计, 统一高中 (docs/architecture.md 八铁律) + 初中子系统 (junior_high_subsystem_design.md) + 核心竞争力。
> 冲突时: 本文定**为什么/是什么**, 八铁律定**代码怎么写**, RESUME 定**现在到哪**。
> ⚠️ 现状诚实声明: 本文多数"是什么"是**目标态**; 标 `[待建]` 者尚未实现; 初中地基审计 6 BLOCK 未修 → 全局 verdict=**REVISE** (§9)。

---

## 0. 第一性原理 (项目不可再分的本质)

中国学生 K12 沿**官方课标脊柱**学英语, 用**官方教材**承载, 受**官方考试** (中考/高考) 检验。
项目价值 = 把这条脊柱建成**一张知识图谱** + 在其上做**考点实证分析**, 使教学"分阶段/紧贴考试/个性化", 规模上超越人工教师。

**三真相源 (一切派生必溯回)**:
| 真相源 | 定义什么 | 权威 |
|---|---|---|
| **课标** (义务2022 三级 + 高中2017 义教/必修/选必) | **脊柱**: stage + 必学范围 | S |
| **教材** (沪教初中 / 人教·外研高中) | **实现**: unit/section + 实际教的词/语法, 按版本 | A |
| **真题** (中考沈阳省统一 / 高考辽宁II卷) | **检验**: 实际考什么 | S/A |

> 严谨性 (评审B1): **应试目标系下**课标是 stage 的**第一性代理真相源** — stage 真正的轴是"学习者认知前驱依赖", 课标是其政策代理。`deepens/expands` 边其实在重建被课标遮蔽的前驱轴; 课标改版需重对账 (死亡条款)。**不另建认知模型** (奥卡姆), 但留 amend 钩子。

**核心洞察 = stage 是统一维**: 平台是**一张图, 每个知识点带引入 stage**, 导出三能力 — **向下**(高阶知低阶, with/the=义务教育不当新词) · **向上**(低阶受控渗透高阶, 标 preview) · **跨阶段**(义/搭配/语法/思维螺旋深化, power 力量→power plant)。

---

## 1. 立法层 (Genesis — 不可变)

**为何存在**: 成为辽宁/沈阳 K12 英语的**单一知识图谱** — 每个 词/义项/语法/主题/考点 锚定其 课标stage + 教材locus + 真题evidence — 使教与学分阶段、紧贴考试、可个性化。

**死亡线 (≤3)**:
1. **D0**: 任意数据+关联 100% 准, 可溯回 课标/教材/真题; 溯不回标 `unknown`, 绝不假填 (§1.3)。垃圾词冒充真词 (审计F1) = 越线。
2. **不混口径**: stage / province (沈阳中考≠辽宁高考≠全国) / 卷型 / 版本 各自诚实 PIT 对齐。复用高中二分推初中 = 越线。
3. **派生不超越证据**: 趋势/语义扩展/生成/造题不超语料证据 — 无押题、无幻觉边、样本量诚实 (分布≥30 / 趋势≥5年每年≥10)。

**判断法典 (人话/机器话, 可 amend)**:
| 法 | 人话 | 机器话 |
|---|---|---|
| stage 双层 | 词级=最早接触阶段(向下兼容); **义项级=该义引入阶段**(跨阶段扩展) | `word.first_introduced_stage=min(课标级)`; `word_sense.stage` 独立 |
| 真相源优先 | 锚第一手 PDF 非派生表 | 提取从 PDF; 快照可能撒谎 |
| 提取鲁棒+诚实 | 抽不净 OCR+交叉验证+词典门; 抽不全标缺口 | text∧OCR∧词典门; `(cid:`/垃圾片段不入或标待OCR; extracted_n 透明 |
| 单一计算点 | 同提取/派生只算一次别处不复刻 | 共享 `textbook_vocab` 核心 [待建]; 不在 scripts/ 重写 (F6) |
| 双门 | 新数据必同挂 D0+moth | data_accuracy_check ∧ moth; stop_gate 触发器认该路径 (坑17/21) |
| 跨阶段边带证据 | 扩义要语料证实才教 | edge.evidence={corpus,n_occur,provenance}; C级未验证不上教学面 |

**死亡条款**: **感知死**(停止与新课标/真题对账) · **判断死**(taxonomy 固化不 amend) · **谄媚死**(垃圾词当考点/巧合共现当扩展边/N=2 冒充趋势/不可信 slope)。校准: 只按真相源对账+教研核实调整, 不按"看着酷"。

---

## 2. Canonical 模型 (一张图, stage 为轴) — 评审A1/A5 大改

**核心修订 (A1): 义项(sense)才是带 stage 的最小单位**, 非 word。power 单值 stage 会销毁"初中力量/高中 power plant"的跨阶段信息, expands_sense 再挖回 = 架构补救自己。故双层:

**知识点节点 (先有 PK 再谈关联 — 铁律2)**:
- `word` (lemma 单 PK): 带 `first_introduced_stage` (单值=最早接触, **仅向下兼容判定**); 跨版本共享 (差异在 introduces 边)。
- **`word_sense`** (word→`has_sense`→sense): **sense 带 stage + 释义 + 例句**; `expands_sense`/`collocates_into` 的 dst 挂这里 (否则边 word→word 自指空转)。
- `grammar` / `theme`(主题语境): 带 stage。
- **句法/语篇/思维 (A5b, 五维的 PK 位)**: `discourse_genre`(记叙/议论/说明…) · `text_type` · `syntax_pattern`(句子结构, =grammar 的 stage-deepening 视图, 经 `deepens` 边, 暂不另立节点除非证不足) · `thinking_level`(Bloom 描述/分析/评判/创造, 课标硬维度, 作正交属性轴)。
- **学习者侧 (A5a, 错题脊柱 — 高中 tutorial_consumer_spec 已立, K12 继承)**: `student` · `mistake`(带 stage + 映射 exam_point/word_sense) · `weakness`(派生, 单一计算点, 零 orphan)。§10.6 回溯补救的 src 节点在此。

**容器**: `volume`/`unit`(Module)/`section`, 带 `version`(沪教/人教/外研) + `stage`。
**检验**: `exam_question`/`exam_point`, 带 `exam_type` ∈ {中考, 高考, **校本测评**(A5c, 日常作业/月考=错题主源)} + `province` + `year` + 卷制 era。**D0 红线: 校本题不与官方真题混口径做趋势** (provenance 分层)。

**边 (走 edges + graph service — 铁律3)**:
- 阶段内: `introduces_word`(unit→word, 带version) / `has_sense` / `uses_grammar` / `theme_of_unit` / `tests_word`(=考过唯一真相, 已收口) / `tests_grammar` / `tests_exam_point` / `made_mistake`(student→mistake) / `weak_at`(student→exam_point/word).
- **跨阶段 (stage 轴)**: `expands_sense`(低阶 sense→高阶 sense) / `collocates_into`(词→高阶搭配) / `deepens`(低阶语法/syntax→高阶) / `spirals`(同主题跨阶段).

**单一计算点**: 派生事实 (stage/考过/越纲/趋势/跨阶段边/weakness) 只在 `backend/services/` 算一次入表 (铁律1)。

---

## 3. 真相源 → 提取架构 [Phase2.6 待建, 修审计根因]

**问题 (审计实证)**: PDF 好, 提取层 LOSSY — CMap(高中)/CID字体码(沪教释义)/digit-glyph误解码/双栏reflow/`*`超纲标/`[:40]`截断 → **垃圾词(假真相)** + **丢真词(缺真相)**。当前 curriculum_vocab 仍含 fuit/gif/ginl, goal 缺失 (F1/F2 未修)。

**第一性提取律 (单一计算点, 四重防线) [待运转]**:
```
PDF ─┬─ text-layer (pdfplumber 双栏 crop, 可读页主源)
     ├─ OCR (~/.venvs/ocr PaddleOCR, **仅 CID/扫描/伪影页** ~26页非全量, 控成本)
     ├─ 交叉验证 (text∩OCR; 已证可读页 171/171=100%)
     └─ 结构/词典门 (词典校验去垃圾片段, 防误杀专名/新词用白名单; `*`存 supra 标记; `(cid:`标待OCR; extracted_n 透明)
            ↓ [待建] backend/services/data_sources/extract/textbook_vocab.py 共享核心
              (沪教/人教/外研/课标 都调; 现 scripts/ 复刻 vocab_renjiao = F6 待收口)
            ↓ emit {data, source_pdf, extracted_n, gaps[], method, provenance} (§1.3 不凑数)
```

---

## 4. 子系统物理布局 — 评审A3/A4 大改: 单库 + node_type (奥卡姆)

**§6 澄清 (关键)**: CLAUDE.md §6 "DuckDB 完全独立, 不 ATTACH 不混用" 的原约束是 **gaozhong ↔ 姊妹项目 gaokao 跨项目边界** (防两项目库混)。**不是** junior ↔ senior **同项目内**约束 (v1 误植)。

**决策 = 单库 `gaozhong.duckdb`** (现 canonical = 通用 `nodes(concept_id,node_type,label,attrs_json)+edges`, 非 per-entity 表; stage 已落 `attrs_json.stage`):
- 初/高中知识点同表, `node_type` 区分 (`word`/`junior_word` 或统一 word + `attrs.stage/version` 区分); 跨阶段边**天然是 edges 一行** (§3 "边一等公民"立即满足)。
- 隔离靠**落库前过 `junior_accuracy_check` 门 + node_type 过滤 + 事务**, 非物理分库 — generic schema 下"加 stage"只是 attrs_json 加 key (零 ALTER 风险)。
- 双库(gaozhong_junior.duckdb)**列为备选**, 仅当未来确需物理隔离; 跨库**禁 VIEW**(DuckDB 跨文件 VIEW 必 ATTACH, 那才违 §6), 若双库则集成走"Python 分别 read_only 连两库 + 内存合并"应用层 join。
- ✅ **当前 jsonl 未入任何库 = 低成本走单库的窗口**; v1 的 separate-DB+VIEW 三态 = 想象复杂度 (architect rule6), 弃。

---

## 5. 门 / 证伪架构

| 层 | 门 | 状态 |
|---|---|---|
| 高中数据 | data_accuracy_check + moth + stop_gate | ✅ 全绿 (46 moth/0 FAIL) |
| **初中数据 [Phase2.6 待建, 坑17]** | junior 段断言 (8条: 无垃圾词头/三级数透明/二级505/无cid释义/沪教词量护栏/语法71/stage无orphan/契约登记) + moth + project_architecture.yaml 注册 | ❌ 0 覆盖 (审计F5) |
| 跨阶段派生 [待建] | stage_refined/扩展边 无 orphan + provenance + 语料证据门; 趋势 province+卷制+样本量门 (坑12) | — |
| 触发器 | stop_gate change-detection 认 `data/junior_high/**` + `scripts/*junior*` (坑21) | ❌ 待加 |

---

## 6. 核心竞争力层 (跨阶段考点实证分析) — 评审A6/A7

建在干净图谱上的分析层 (用户核心竞争力, 非押题=方向性指引):
- **考点趋势/热力/分布**: province-scoped + 卷制分段 + 样本量诚实 + 分层非平均 (坑12)。高考 post-2021 仅5年/2025=9<10 → "样本不足"banner。
- **关联性**: 共现/题材↔考点/词↔考点边。
- **中考×高考评估轨迹 (A7 修正)**: 中考省统一仅 **N=2(2024-2025)** → 只做**静态交叉点清单**(中考考过∩高考考过=最高优先级地基), **不做中考侧趋势**(N=2 冒充趋势=谄媚死)。C 落地且达阈值才解锁。
- **语义扩展挖掘 (B, NLP 子项目级, A8)**: 298 候选(=stage 错位启发, 真扩义比例 unknown, 须持久化) → pipeline: 跨stage语料对齐 → 义项消歧 → PMI/共现 → 双模型+教研校验 → 带 evidence 的 expands_sense 边。
- **自编教程 (A6, 继承 docs/tutorial_consumer_spec.md, 扩 K12 版)**: 契约 `generate_tutorial(stage, exam_priority, version) → 结构化教程`; 验收门 = 词量≤已学stage+课标(§1.2) + R2不抄 + provenance; 加 stage 维(分阶段/跨阶段补救/preview 渗透)。**无契约不开工**(防元数据壳重演)。

---

## 7. 建设路线 (显式 DAG, 地基优先) — 评审A8

```
Phase2.6 初中地基修复+双门 (审计F1-F8: 词典门/OCR坏格&诚实1589/*召回/cid诚实/二级505/语法71/收口textbook_vocab/junior门+触发器)
   │  out: 干净 junior vocab+grammar + 共享提取器 + junior_accuracy_check 绿
   ├──────────────┬─────────────────────────┐
   ↓              ↓                         ↓ (真题获取可并行, 抽取依赖2.6共享提取器)
A. Phase3集成   C. 沈阳中考真题(2024+省统一)    
   stage_refined  out: 中考exam_question/考点
   (修复后)回填    │
   高中节点+单库    │
   word_sense层     │
   │               │
   ↓ A 产出干净 stage + sense 节点
B. 语义扩展边 ←──── C (跨stage语料需中考侧)
   298持久化→pipeline→expands_sense/collocates_into 边
   │
   ↓
Phase4 核心竞争力跨阶段层 (中考×高考静态轨迹 + 趋势 + 自编教程) + 前端 stage 浮窗
   ← (B, C)
```
**依赖铁序**: `2.6→A→B`; `B←C`; `Phase4←(A,B,C)`。C 的真题**获取**可与 2.6 并行, 但**抽取**依赖 2.6 的共享提取器 (不能真并行抽取)。

---

## 8. 工具栈
| 工具 | 职责 |
|---|---|
| data_accuracy_check + stop_gate | D0 强校验门 (每子系统一套) |
| moth assert / coupling | 漂移 + 删改前 fan-in/孤儿审计 |
| codegraph query/context | 改提取器/服务前 blast-radius + 单一计算点定位 |
| ~/.venvs/ocr PaddleOCR (ocr-python) | CID/扫描页 OCR + 文本层交叉验证 (全局跨项目) |
| sherpa takeover | 新 session 单页对账 |
| scripts.tools.map doctor | live 状态单一入口 |
| Workflow 多 agent | 并行审计/对抗复核/设计盲点扫描 (本架构 v1→v2 即用) |
| architect-controller skill | 顶层设计/重排 |

---

## 9. Verdict: REVISE (与子系统 §11.3 收敛)

第一性脊柱 (三真相源 + **sense级 stage 轴** + 地基优先序) 方向正确、立法层硬, 但**定稿前已落定的修订** (v2 本次):
- ✅ A1 sense 节点 (义项带 stage, 非 word 单值); A4 单库 node_type (弃双库三态); A5 补 学习者/句法语篇思维/校本 节点; A6 继承 tutorial 契约; A7 中考轨迹=静态非趋势; A8 显式 DAG + B 降级; B1 课标=政策代理软化; A2 全文未实现改 [待建]。
- ⏳ **未落地 (REVISE 的实质)**: 初中地基审计 6 BLOCK (垃圾词/丢真词/欠收/cid/0门/F6复刻) **未修** → **Phase2.6 是解除 REVISE 的唯一路径**, A/B/C/Phase4 全阻塞于它 (§1.1 数据基石优先)。

**即时下一步 = Phase2.6 地基修复 (C 真题获取并行)** → 达标后 A→B → Phase4 核心竞争力跨阶段层。
