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

## 5. gaokao 姊妹项目工作

路径: `/Users/dp/Documents/M/gaokao/`

已完成:
- clone GAOKAO-Bench-Updates 到 `data/external/GAOKAO-Bench-Updates/`
- 导出 verified 新课标II: `gaozhong/data/gaokao_verified_xgkii_2023_2024.jsonl` (12 条)

待做:
- 获取 2021/2022 新高考II卷 英语 PDF (网络源)
- 全部年份真题 PDF 归集到 gaokao 项目 `data/raw/pdfs/`

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
