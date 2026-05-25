# 断点续传 — 新 session 第一份读物

> 新 session 一打开, 先读本文件 + `goal.md` Phase 7.12 + `docs/model_driven_design.md` (宪法).

最后停止时间: **2026-05-26**
最后 commit: **`92f24a7`** audit: 逐题全文核对

---

## 1. 当前状态 — 数据层有严重问题待修

验证命令:
```bash
cd /Users/dp/Documents/M/gaozhong
python3 scripts/data_accuracy_check.py          # D0 (应全绿)
bash scripts/stop_gate.sh; echo "exit=$?"       # stop gate (应 exit 0)
python3 scripts/tools/audit/model_capability_audit.py  # 模型审计 (当前 97.3)
python3 scripts/tools/audit/cross_verify_pdf.py --all  # 交叉核对
```

---

## 2. 已完成 (不需要重做)

```
Phase 1-6  ✅  数据基石 + 题库 + 教师端 + 真问题修 + 40节课程 + 运营准备
Phase 7.1  ✅  40/40 讲义 enriched (180K+ chars)
Phase 7.2  ✅  听力 25 题 + 播放器 + 打印
Phase 7.3  ✅  续写 10 + 应用文 10
Phase 7.4  ✅  工具模块 12 工具 + 宪法 31 条入库 + 模型审计 97.3/100
Phase 7.5  ✅  Quiz mode 即时批改
```

---

## 3. 🔴 发现的严重数据问题 (本 session 审计暴露, 必须修)

### 3.1 真题数据污染 (L-N, L-O, L-P, L-Q)

| 问题 | 严重度 | 详情 |
|---|---|---|
| **2021 新高考II卷 完全缺失** | 🔴 致命 | GAOKAO-Bench 无此卷, DB 中 16 条全是甲卷 (L-P) |
| **2022 新高考II卷 完全缺失** | 🔴 致命 | 任何数据源都没有 (L-P) |
| **2010-2014 辽宁自主命题** | 🔴 严重 | GAOKAO-Bench 新课标II 是其他省份的, 不是辽宁 (L-P) |
| **题型标签三个标反** | 🟡 已修 | cloze_test/cloze_passage/fill_in_blanks 互换 (L-O, 已修 exam.py) |
| **2020 PDF 是课标不是真题** | 🟡 已知 | scmlzx_english_2017_rev2020 实为课程标准 (L-Q) |
| **答案 B 偏 76%** | 🟡 已知 | 听力/阅读练习答案分布严重偏 B (L-L) |

### 3.2 当前 verified 数据全景

| 年份 | 来源 | 状态 | 条数 | 全文核对 |
|---|---|---|---|---|
| 2015-2020 | GAOKAO-Bench | ✅ verified (新课标全国II) | 48 | 2020 无真题 PDF 未核对 |
| 2021 | — | ❌ **完全缺失** | 0 | — |
| 2022 | — | ❌ **完全缺失** | 0 | — |
| 2023 | GAOKAO-Bench-Updates | ✅ verified | 6 | 无 PDF 未核对 |
| 2024 | GAOKAO-Bench-Updates + PDF | ✅ **全文核对 PASS** | 6 | 6/6 (76-87%) |
| 2025 | PDF only | ⚠️ 粗提取 | 9 | — |

### 3.3 全系统宪法审计 (2026-05-25)

| 审计层 | 得分 | 关键问题 |
|---|---|---|
| 数据+图谱 | 78/100 | 2024/2025 图谱孤立 (1 边 vs 108); 38 主题已修 |
| 内容+题库 | 42/100 | 答案B偏; 275 synth 无解析; 无难度梯度; 31/40 讲义缺段 |
| 工具+流程 | 72/100 | 7 模块绕过宪法; 5 工具缺失 |
| **综合** | **64/100** | 目标每项 100 |

---

## 4. 下一步计划 (goal.md Phase 7.12)

```
Phase A: 真题数据清洗 + 补全 ← 最高优先
  ├─ 从 gaokao 项目获取 2021/2022 新高考II卷 PDF
  ├─ GAOKAO-Bench-Updates 已 clone (2023+2024 各 6 条 verified)
  ├─ 逐题拆分 (55-60 题/年) + cross_verify_pdf 核对
  └─ 清除 DB 中错误标注的 2010-2014 + 2021 假数据

Phase B: 知识图谱重建
  ├─ 新题→word/grammar edges (2024/2025 当前只有 1 条边)
  └─ course_materials ref_id 统一

Phase C: 模型重训 (337 逐题标注 → 用干净数据重训)
  └─ 当前 trend_engine 结论不可信 (训练数据 ~50% 污染)

Phase D: 全量内容重写 (P16 解析对应原文 + P17 重写标准)
  ├─ D1 解析标注原文段落+句子
  ├─ D2 答案均匀化
  ├─ D3 synth 补解析/淘汰
  ├─ D4-D7 见 goal.md
  └─ 等数据清洗 + 模型重训完成后统一做

Phase E: 全系统审计 → 目标 100/100
```

---

## 5. 本 session 完整功能清单 (别忘了这些已经建好)

| 功能 | 文件 | 状态 |
|---|---|---|
| PDF 打印 | `frontend/static/app.css` @media print + 讲义 modal 打印按钮 | ✅ |
| 听力播放器 | `frontend/static/common.js` GZ.audioPlayer() + play/pause/progress/speed | ✅ |
| 音频命名规范 | `backend/config/audio_config.yaml` data/audio/{year}/listening/{id}.mp3 | ✅ |
| C tab 听力面板 | `frontend/static/app_router.js` 筛选+原文展开+播放器 | ✅ |
| Quiz mode | `/api/course/quiz` + 前端即时批改 | ✅ |
| D tab 宪法展示 | `/api/constitution/list` + 前端卡片渲染 | ✅ |
| /lessons skill | `~/.claude/commands/lessons.md` 查/加/审教训 | ✅ |
| 阅读练习 22 题 | `backend/config/reading_exercises.yaml` + reading.py loader | ✅ (待模型审计后重写) |

## 6. codex review 关键发现 (3 次 review)

### Review 1: 宪法 + 工具审计
- 宪法 JSON schema 没定义 (只有示例无强制约束)
- trend_engine 当时用等权 OLS → 已修为 WLS
- 2024/2025 缺口是最关键 → 已部分解决
- **最关键缺失工具: model_capability_audit** → 已建
- 话题匹配太粗 (关键词无分词) → 已知但未修

### Review 2: 真题深度分析
- codex agent 超时, 未完成细粒度分析
- 后来由本地 fine_grain_annotator 替代完成 (337 逐题标注)

### Review 3: 全系统宪法审计 (3 路并行)
- 数据层: 38 主题孤立 (已修) + 2024/2025 图谱 1 边 (待修)
- 内容层: 答案 B 偏 76% (致命) + 275 无解析 + 31/40 缺段 + 无难度梯度
- 工具层: alignment_checker ROOT bug (已修) + 7 模块绕过宪法 + 5 工具缺失

## 7. 用户关键决策和指令 (必须遵守)

| 用户原话 (摘要) | 落到什么 | 是否已实施 |
|---|---|---|
| "内容必须紧贴课标高考真题命题思路" | 宪法 §1 + P2 趋势优先 | ✅ 写入宪法, 代码部分合规 |
| "建模型来检查偏离度, 后续可持续使用" | exam_alignment_checker 8 维度 | ✅ 已建 |
| "模型要持续学习和分析, 热力图, 关联性" | trend_engine + fine_grain_annotator | ✅ 已建 (但数据有污染) |
| "越近的真题权重越高" | 宪法 P1 年份权重 2025=5 | ✅ 代码已改 WLS |
| "趋势优先是正向的不是违宪" | 宪法 P1-P3 正向铁律 | ✅ |
| "写进宪法, 入数据库, 前端展示, 程序化执行" | constitution 表 + API + enforce() | ✅ |
| "解析要对应原文段落和具体句子" | 宪法 P16 | ✅ 写入, 待实施 |
| "该重写的重写, 可优化的优化" | 宪法 P17 | ✅ 写入, 等数据清洗后统一做 |
| "交叉核对工具放工具模块, 程序化确保" | cross_verify_pdf + init_db 门禁 | ✅ 已建+单测 |
| "审计目标必须全部满分" | 宪法 §7 三层 100/100 | ✅ 写入 (当前 64) |
| "做成 skill 随时维护使用" | /lessons skill | ✅ |
| "从 gaokao 项目做好数据源" | 进 gaokao 项目工作 | 🔲 部分 (clone 了 Updates, 2021/2022 待获取) |
| "全部原版 PDF 做交叉核对" | cross_verify_pdf --all 逐题全文比对 | ✅ (发现 2020 PDF 是课标) |
| "模型预测目标 95 分以上" | model_capability_audit 97.3 | ✅ (但数据污染后需重测) |

## 8. gaokao 姊妹项目详细状态

路径: `/Users/dp/Documents/M/gaokao/`

### 已完成
- clone GAOKAO-Bench-Updates 到 `data/external/GAOKAO-Bench-Updates/`
  - 2023 English: Reading(4) + Cloze_Test(1) + Fill_in_Blanks(1) = 6 条 新课标全国Ⅱ卷
  - 2024 English: Reading(4) + Cloze_Test(1) + Fill_in_Blanks(1) = 6 条 新课标Ⅱ
- 导出 verified: `gaozhong/data/gaokao_verified_xgkii_2023_2024.jsonl` (12 条)

### gaokao 项目已有的 PDF
```
data/raw/pdfs/cdn_zgkao_com/zgkao_2024_xgkii_english__english_2024.pdf  ← 2024 真题 ✅
data/raw/pdfs/jhgk_cn/jhgk_2025_xgkii_english__english_2025.pdf        ← 2025 真题 ✅
data/raw/pdfs/scmlzx_net/scmlzx_english_2017_rev2020__english_2020.pdf  ← ❌ 这是课标不是真题!
```

### gaokao 项目的数据问题
| 问题 | 详情 |
|---|---|
| GAOKAO-Bench 2021 | 无新高考II卷, "解析版" 实为全国甲卷 |
| GAOKAO-Bench 2022 | 完全无新高考II卷 (只有甲/乙) |
| GAOKAO-Bench 2023 原版 | 在 gaozhong DB 中被混入 4 套卷, 只有 ~1/4 是 II 卷 |
| 2020 PDF | 文件名误导, 实际是课程标准 |

### 待做
- 获取 2021 新高考II卷 PDF (搜索 "2021 新高考全国II卷 英语" — cpsenglish.com 有题面但需核实)
- 获取 2022 新高考II卷 PDF (同上)
- 获取 2015-2019 真题 PDF 用于交叉核对
- gaokao 项目有 `scripts/pull_official_pdfs.py` + `pdf_sources.yaml` 可扩展

---

## 6. 关键文件索引

| 文件 | 作用 |
|---|---|
| `goal.md` | 全局目标 + Phase 7.12 详细计划 |
| `docs/model_driven_design.md` | 设计宪法 (8 原则 + 17 铁律 + 8 违宪) |
| `docs/lessons_learned.md` | 19 条教训 (L-A 到 L-Q) |
| `data/reports/exam_patterns.json` | 命题特征模型 (⚠️ 待数据清洗后重建) |
| `data/reports/trend_analysis.json` | 趋势分析 (⚠️ 待数据清洗后重建) |
| `data/reports/fine_grain_annotations.json` | 337 逐题标注 |
| `data/gaokao_verified_xgkii_2023_2024.jsonl` | 2023+2024 verified 数据 |
| `scripts/tools/` | 12 工具 (alignment/generation/audit/monitor) |
| `backend/services/constitution.py` | 宪法程序化执行 (enforce_before_generation) |

---

## 7. 快速接续

```
"读 docs/RESUME.md, 从 Phase A 数据清洗开始"
```
