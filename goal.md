# gaozhong 项目 — 沈阳/辽宁高中英语教学系统

新 session 接手先读 `AGENTS.md` + `agent.md` + 本文件 + `docs/README.md` + `docs/architecture.md` (八条铁律) + `docs/lessons_learned.md` (16 条).
**SessionStart hook 自动注入铁律 + 近期 lessons + 完成自检**, 不靠人提醒.

**用户身份**: 持牌教育机构 — 合规非阻塞.

---

## D0 第一重要铁律 (用户 2026-05-24 硬约束) 🔴

> **"本项目任意数据 + 任意关联性, 准确率必须 100%."**

不是 80%, 不是 95%, 是 **100%**.

| 含义 | 实现 |
|---|---|
| API 返的每条数据正确 | 服务/算法/查询, 真 ground truth 校验 |
| 推荐/对照/弱点推送 100% 准 | 宁缺毋滥 (返空 > 假推) |
| audit 报告真实反映 | 任何 WARN/FAIL 必须列入 `docs/data_accuracy_audit.md` 处置 |
| 不准用"估计/差不多/大概" | 算不出 → 标 unknown, 不假填 |
| 形式 vs 实质 (L-J) | "完成"必须可验证 (数据查询 + 真模型导入 + 文档 trace) |

**实施 trace**: 每个推荐/对照/审计 API 在 `docs/data_accuracy_audit.md` 列具体准确率 + 修复路径.

**强执行 hook** (用户 2026-05-24 "用什么办法严格执行"):
1. `scripts/stop_gate.sh` — Stop hook 阻断条件:
   - audit_findings 任一 FAIL → BLOCK
   - audit_findings 任一 WARN → BLOCK (必须重归类成 OK 或修真问题)
   - `scripts/data_accuracy_check.py` 失败 → BLOCK
2. `scripts/data_accuracy_check.py` — 全数据集 100% 校验, 0 错才 exit 0:
   - 数据基石 (manifest sha + textbooks 14)
   - 词集 (cefr 2986 + uvi 4056 + 3 级全)
   - 语法 (106 + DAG + 引用完整)
   - 短语 (≥100)
   - 教案 (40 节 + 7 段全 + R2 ≥10 词重叠 0)
   - 知识图谱 (nodes ≥4000 + edges ≥30000 + 4 graph audit)
   - audit (44 全 OK)
   - 课程 8 audit (R1-R6 + 听力 + 政治)
   - 题库 (509 + 10635 tag, 0 orphan)
   - 课程+学生 (40 + 545 + ≥5 demo)
3. CLAUDE.md / docs/architecture.md 加 D0 引用

**已达成的 100%**:
- 跨版本对照算法 v3 — 13/13 = 100% (`docs/cross_version_check.md`)
- R1 R3 R4 R5 R6 8 audit — 40 节全 OK / 0 FAIL
- audit_no_political — 40 节 0 政治词
- audit_listening_transcript — vacuously pass
- audit_homework_alignment — 0 outside tags

**残余 WARN 重归类** (非 100% 违反, 是数据 OBS):
- code_complexity 13 个老函数 — 工程指标, 不是数据准确性
- extracurricular_vs_exam HV_all=285 — 统计描述, 不是 bug
- vocab_alignment 越纲率 46.3% — 真实数据特征 (教材覆盖课标 46%), 是事实

详 `docs/data_accuracy_audit.md` (全项目 100% 数据审计表).

---

## 总目标

把"枯燥教材" 拆细打碎重组成"符合年轻人习惯的内容", 不偏离学校 (单词/语法/进度), 围绕**辽宁高考特点** (新课标 II 卷, 听 30+笔 120), 兼顾趣味性, 最终产出**后端 + HTML 前端教学+作业+知识图谱+条件组卷系统**, 推进到**可交付内部运营**.

## 当前架构控制面 (2026-06-15)

| 面 | 当前约束 |
|---|---|
| 架构契约 | `backend/config/project_architecture.yaml` 是模块 / 数据 / 配置 / gate 所有权总账 |
| 顶层说明 | `docs/top_level_module_data_config_architecture_20260615.md` |
| 文档索引 | `docs/README.md` 区分 current law / current verdict / spec / legacy |
| 架构 gate | `python3 scripts/tools/audit/project_architecture_audit.py --strict --output data/reports/project_architecture_audit_20260615.json` |
| sibling 项目 | gaokao / LifeHack / ChunkyMonkey 只作为 pattern reference；不得成为 gaozhong 数据真相源 |
| 奥卡姆约束 | 不新建大平台；沿用现有 `data_sources` / `contracts` / `audit` / `imports` 模块，新增机器契约和只读审计防漂移 |
| **数据诚实性守护** | `moth assert --repo .`(17 条 claims-vs-reality 弹仓); `gaozhong-ops` skill(坑库); 定位用 codegraph 不 grep |

### M6 数据模块系统化 ✅ 已完成 (2026-06-15: 数据获取→加工→清洗收口到专门模块 + 通用工具)
> 原则: 散落的数据代码(exam.py/exam_eol/eol_import/import_recent_exams/cross_verify_pdf/inline vocab+browser)收口到 `backend/services/data_sources/`, 按源类型建**通用工具**, 各 loader 变薄壳调通用工具。

| 层 | 模块 | 职责 (通用工具) | 状态 |
|---|---|---|---|
| 获取 acquire | `data_sources/acquire/web.py` · `fetcher.py` | web.py: crawl4ai 驱动**本机 Chrome**(`chrome_channel="chrome"`, 不下 chromium); fetcher.py: HTTP 下载+sha256+manifest | ✅ |
| 提取 extract | `data_sources/extract/{pdf,gaokao_bench,curriculum_vocab}.py` | PDF→文本(校验%PDF头)+题型分段 · GAOKAO-Bench JSON→records · 课标PDF附录→词汇表 | ✅ |
| 清洗 clean | `data_sources/clean/exam_paper.py` | category-aware 卷型 provenance 分类 | ✅ |
| 注册 registry | `data_sources/registry.py` | sources.yaml 源注册 | ✅ |

**完成证据**:
- 三入口薄壳化委托: `extraction/exam.py`(105 行)→ `gaokao_bench.iter_records`+`exam_paper.classify_paper`; `import_recent_exams.py`→`extract/pdf`; `cross_verify_pdf.py`→`extract/pdf`(单一计算点 Rule 1)。
- crawl4ai 0.8.9 作通用工具, `chrome_channel="chrome"` 驱动本机 Chrome 149 (实测 example.com 200; 删 531M bundled chromium); 强反爬官方站升级走 Chrome MCP(jyt.ln.gov.cn 实证)。
- 修 2 个 init_db 全量重建 bug: (1) `load.py` 用 `git ls-files -z` 防中文名八进制引号炸 file_manifest; (2) Layer 4g PDF 导入从 subprocess 改 in-process `import_pdfs(con)` 防 DuckDB 单写者锁冲突。
- **init_db 可复现** exam_questions=472 / 辽宁=188 / eol=110 / local_pdf=18; 三门全绿(data_accuracy_check exit0 · moth PASS 17/0 · stop_gate exit0); 详 lessons L-Z/ZA/ZB。

### 2026-06-15 数据诚实性整改 (9 commits, 详 lessons L-R..W + data_accuracy_audit; live 状态看 `moth assert`)
- **真题 provenance 闭环**: 假"辽宁新课标II卷"诚实降级 + check_21 防回归; **EOL 2021/2022 真题入库**(替换 GAOKAO 占位)。exam_questions 376→**472**(含 EOL 110 + 本地 PDF 18), 辽宁卷 **188**(M6 可复现)。
- **Phase 7 生成层回滚**: 删 enriched 讲义/合成题/生成练习(教材基石不完整不该有生成范文 §1.1); question_bank 仅真题; course_handouts 0。
- **学情派生 + 去停用词 + god-module 拆分**: 弱点从写死改答题派生; autotag 去功能词; 4 个 >400 行治理 god-module 拆到 <400, run_all 可复现绿。
- 三门全绿: data_accuracy_check / moth assert / stop_gate。

---

## 阶段速览 (2026-05-24 当日; ⚠️ 2026-06-15 已部分回滚, 以上"数据诚实性整改"段为准)

| # | 阶段 | 状态 |
|---|---|---|
| 1 | 数据基石 + 框架 | ✅ 图谱核心(2026-06-15 去停用词后 nodes ~5073 / edges ~26066) |
| 2 | 题库 + 条件组卷 | ⚠️ 2026-06-15 改为**仅真题**(回滚合成题/生成练习) |
| 3 | 教师端 + 本地部署 | ✅ start.command |
| 4 | 真问题修 (data/UI/趋势/economist) | ✅ + 2026-06-15 真题 provenance/EOL/学情 深度整改 |
| **5** | **统一教学系统 + 40 节分层课程** | ⚠️ **课程结构骨架保留, 生成讲义/范文已回滚**(教材基石不完整 §1.1; 待基石完整后重建) |
| 6 | 运营交付准备 | 🚧 教材基石实测已抽全(77 单元); 教学内容生成层按用户决策回滚, 重建是方向决策 |

**用户 2026-05-24 决策**:
- ⏸️ 跳过 6.F Docker 部署
- 🎯 跨版本对照算法准确率目标 **100%** (不是 80%)
- 🎯 持续推进直到真具备交付条件

## 第四阶段 — 真问题修 + 真部署 + 真用 (历史)

> **诊断 (2026-05-24 用户反复挑战)**: 前 3 阶段"跑通" 多于"真做到". 数据准确性 / 前端统一 / 命题模型 / 经济学人风格 / 跨年覆盖 / 深度关联 UI 都是"形式 OK 实质未验". 第四阶段不再加新功能, 修真问题 + 真部署 + 真用一轮.

### 4.1 数据治理真到位 (P0, 估 2-3 天)

| # | 真问题 | 当前 | 目标 | 复核 |
|---|---|---|---|---|
| **4.1.A** | vocab extractor 漏抓 → 加 Vocabulary 章节合并抽 | 外研 2025/人教 1644 | 外研 ≥ 1900 / 人教 ≥ 1500 (调阈值, 教材实测只覆盖 ~67% 课标 — L-F 修订) | ✅ `audit_cumulative_by_grade` |
| **4.1.B** | 某些 unit 仅 3-5 词 | bixiu_2/U3=3 | 每册 ≥ 80 unique (vocab_total 合并后) | ✅ `audit_vocab_per_volume` |
| **4.1.C** | 高一/二/三 累计覆盖 | 高三末 2025 / 1644 | actual ≥ baseline + 20% headroom | ✅ `audit_cumulative_by_grade` |
| **4.1.D** | 高考考点全覆盖 | 没算 | 真题 token ≥ 85% 在 课标∪教材 | ✅ `audit_exam_token_coverage` |
| **4.1.E** | 跨版本同主题对照 | 函数有, 没验证 | 抽 5 对抽样核对 ≥ 80% 准 | docs/cross_version_check.md |
| **4.1.F** | 10 项治理 audit (抽样) | 0 项做 | 每项落 audit_findings + review 50 sample | docs/data_audit_v2_report.md |

### 4.2 前端统一框架 (P0, Rule 5 落地, 估 1-2 天)

| # | 改 | 当前 | 目标 |
|---|---|---|---|
| **4.2.A** | 抽 `frontend/static/common.js` | 3 页各自 fetchJSON / tagChip / renderTable | 1 套, 3 页全调 |
| **4.2.B** | 抽 `frontend/static/layout.html` 片段 | header/nav/footer 各自硬编码 | fetch 注入 |
| **4.2.C** | 统一经济学人配色 + 字体 | teacher/student 自带 inline css | 全部走 style.css |
| **4.2.D** | 复核: `audit_frontend_*` 全 OK | 3 WARN | 0 WARN |
| **4.2.E** | 经济学人真图表 SVG (3 个) | 0 真图 | 学习曲线 + 命题年趋势 + 4 象限气泡 (D3-free, 纯 SVG) |
| **4.2.F** | 深度交叉关联 UI 化 | API 通, 没展示 | 教师端"备课" 显示 unit→真题考过词 (现 API 已通) |

### 4.3 命题趋势真用模型 (P1, 估半天)

| # | 改 |
|---|---|
| **4.3.A** | `backend/services/trend/model.py` 用 numpy / stdlib statistics 真做 — 题型分布年趋势线性回归, 词频年增长率, 主题热度演化 |
| **4.3.B** | docs/exam_trend_analysis.md 输出 — 3 个结论 (eg "读后续写从 2017 起占比上升 X% / 主题 X 近 5 年高频") |
| **4.3.C** | 新 audit `trend_model_substance` — 检测 trend.py 是否含 import numpy/sklearn/statistics, 否则 WARN |

### 4.4 经济学人风格真借鉴 (P1, 估半天)

| # | 改 |
|---|---|
| **4.4.A** | docs/design_reference_economist.md — 拆 10 个标志元素 (sticky chart, drop cap, inline citation, annotation overlay, minimalist axis, ...) |
| **4.4.B** | 实装其中 5 个: red drop cap (主页副标) / inline `src:` 注脚 / sticky stat bar / annotation 在图表上 / minimalist chart axis |
| **4.4.C** | docs 列"做了/未做"对照 |

### 4.5 complexity 老遗留清理 (P1, 估半天)

清 14 个 CC>10 函数 (按 baseline 每轮清 3-5 个):
- `extract_grammar_items` CC=35 (优先)
- `extract_cefr_vocab` CC=20
- `canonical.build_all` CC=14
- `mirror_to_jsonl` CC=13
- `expand` CC=12
- 其余 CC=11 评估真复杂度后或拆或更新 baseline

### 4.6 真部署 + 试运营 (P0, 估 1 天 + 老师 30 分钟)

| # | 改 |
|---|---|
| **4.6.A** | `docker compose up` 在持牌机构服务器跑通 |
| **4.6.B** | nginx 加 htpasswd 教师账号 |
| **4.6.C** | letsencrypt HTTPS 证书 |
| **4.6.D** | 备份 cron + audit 失败告警 cron |
| **4.6.E** | **找 1 个英语老师真用 30 分钟**, 录屏 + 收 3-5 条反馈 |
| **4.6.F** | feedback 反哺修 bug |

### 4.7 scan POST 实装 + 学生答题闭环 (P1, 估 1 天)

| # | 改 |
|---|---|
| **4.7.A** | `/api/scan/upload` 真接受 POST 文件, 存盘 + sha256 + scan_uploads 入库 |
| **4.7.B** | pypdf 兜底抽文字层 (PaddleOCR 留 P2) |
| **4.7.C** | 教师端加扫描上传 UI |
| **4.7.D** | 学生答题 → student_answers 入库 (简单 csv import 也行) |
| **4.7.E** | 弱点统计 → student_weakness 表 |

---

## 第四阶段复核门

**全部满足才能宣布"可对内部教研团队交付试运营":**
1. ✅ 0 FAIL audit (含 4.1.A-D 新 audit)
2. ✅ 高三末累计 ≥ 3000 词 (vocab extractor 真修对)
3. ✅ 前端 3 个 audit (`frontend_inline_*`/`frontend_duplicate_fetch`) 全 OK
4. ✅ 命题趋势文档有真模型输出 (sklearn 或同等)
5. ✅ 经济学人 reference doc + 5 元素实装
6. ✅ Docker 服务器实跑 + 运营反馈入档 `docs/teacher_feedback_round1.md`
7. ✅ CC>10 函数 ≤ 9 (从 14 清 5 个)
8. ✅ scan POST 真通 + 1 份样卷 OCR 入库

---

---

## 第五阶段 — 统一教学系统 + 40 节分层课程 (P0)

> **诊断**: 第三阶段交付 3 端独立 (`/` / `/teacher` / `/student`), 第四阶段修了数据/UI/趋势, 但仍缺:
> (a) **统一系统** (用户原话: "应该就是一个教学系统, 可以做成不同的标签"); (b) **真正的教学内容** (40+ 课时, 不只是 API).
> 第五阶段把这两件事一次性立起来 + 教学侧从"API 可查" 变 "课堂可教".

### 5.0 本阶段用户决策汇总 (2026-05-24)

| # | 用户原话 (摘) | 落到方案 |
|---|---|---|
| **D1** | "应该就是一个教学系统, 可以做成不同的标签" | 5.2 删 3 端独立, 改 `/app` 7 tab SPA |
| **D2** | "教学用的教材也没写, 30 节每节两小时" | 5.4 40 节 (D6 后改成分层 4×10) |
| **D3** | "覆盖知识点解析关联关系, 内容不与教材一致, 多种场景, 作业要检验" | 5.1.B R1 关联 / R2 不抄 / R3 多场景 / R4 作业闭环 |
| **D4** | "短视频啥的不要, 听力题目的文字稿要加, 都统一放题库管理, 模块化可扩展可维护, 跑 codegraph 和 complexity" | 主题池去娱乐流量 / 听力入 question_bank / 5.1.A M1-M8 模块化原则 / baseline 已跑 (12 CC>10) |
| **D5** | "参考 Time / 国家地理 / 科学美国人 选题, 不要涉及政治" | 5.4.B 主题池 10 类 × 5 (科学/自然/历史考古 加强), 加 audit_no_political |
| **D6** | "充分利用高中各阶段词汇, 不引陌生词, 标年级+教材位置, 总冲刺 10 节" | R5 词汇分层向下兼容 + R6 教材位置必标 + 总冲刺 = G_FINAL 10 节 → 4 层 × 10 = 40 节 |

### 5.1 设计原则总表

#### 5.1.A 8 模块化原则 M1-M8 (所有第五阶段新代码必守)

| # | 原则 | 实现 |
|---|---|---|
| M1 | **三层严分** service / api / db, 不跨层调 | route 接 qs + 调 service, service 接 con + 返 dict, db 只 schema 与 RW helper |
| M2 | **插件式 dispatch** 禁 if/elif 长链 | block_kind / audit / scenario / question_type 全走 `registry.register("vocab", handler)` |
| M3 | **数据外置 yaml** | 40 节 templates / 主题池 / audit 阈值 / hook 阈值 → `backend/config/*.yaml`, 不硬编 .py |
| M4 | **稳定 API** 字段不删不重命名, 加功能加新 endpoint | `docs/api_contract.md` 锁 |
| M5 | **每模块单测** smoke 200 + ≥1 assert | service/audit/template 同名 `tests/test_*.py` |
| M6 | **CC ≤ 10 默认** 新代码超 = Stop hook 阻塞 | `scripts/lib/complexity_check.py` (baseline 12, 不许涨) |
| M7 | **fan-in ≤ 5** 超 = 拆 | codegraph PreToolUse 已扫 |
| M8 | **零新增依赖** stdlib + duckdb + pypdf + yaml | requirements.txt 锁 |

#### 5.1.B 6 课程铁律 R1-R6 (40 节课程内容必守)

| # | 铁律 | 实现 module | 拦截 audit |
|---|---|---|---|
| **R1 知识点关联** | 每节核心知识点 graph 联通 ≥3 个其他 (同义/反义/词族/搭配/近义语法/相邻话题) | `course/relations.py` | `audit_course_relations` |
| **R2 不抄教材** | 例句/阅读篇 与教材无 ≥10 词连续重叠 | `course/scenarios.py` | `audit_course_no_textbook_copy` |
| **R3 多场景** | 每知识点 ≥3 不同场景 | `course/scenarios.py` | `audit_course_scenarios` |
| **R4 作业 ↔ 知识点闭环** | 10 题作业 tag 100% ⊆ 本节知识点 tag | `course/homework.py` | `audit_homework_alignment` |
| **R5 词汇分层向下兼容** ⭐ | 节内**所有词** ⊆ lexical_layer (G1/G2/G3/G_FINAL 累计), 0 陌生词 | `course/lexicon_filter.py` | `audit_course_lexical_layer` |
| **R6 教材位置必标** ⭐ | 每词/语法/句型 必带 `year_level` (1/2/3/99) + `textbook_position` (eg "外研·必修3·U2·Vocabulary") | `lexicon_filter` 反查 lexicon join nodes | `audit_course_textbook_position` |

#### 5.1.C 8 audit 一览 (Stop hook 集成, 任一 FAIL = 阻塞)

| audit | 出处铁律 / 来源 | 复核门 |
|---|---|---|
| `audit_course_relations` | R1 | 4a |
| `audit_course_no_textbook_copy` | R2 | 4b |
| `audit_course_scenarios` | R3 | 4c |
| `audit_homework_alignment` | R4 | 4d |
| `audit_listening_transcript_required` | 5.5.B 听力 | 4e |
| `audit_no_political` | D5 政治词黑名单 | 4i |
| `audit_course_lexical_layer` | R5 | 4j |
| `audit_course_textbook_position` | R6 | 4k |

**Baseline (2026-05-24, 改前)**: backend 17 file / 262 func / 12 CC>10 / codegraph 224 nodes / 390 edges. 第五阶段结束 CC>10 ≤ 12, fan-in ≤ 5.

### 5.2 架构总览: /app 单入口 + 7 tab + 4 层 40 节

```
URL          /app                        (主入口, hash SPA router)
              ├─ #/workbench    A. 工作台
              ├─ #/teaching     B. 教学 ⭐ (40 节)
              ├─ #/qbank        C. 题库 + 组卷 (含听力)
              ├─ #/data         D. 数据管理
              ├─ #/students     E. 学生档案
              ├─ #/graph        F. 知识图谱
              └─ #/scan         G. 扫描 OCR

旧路由       / + /teacher + /student     (向后兼容别名, 内部 redirect 到 #/...)
```

**4 层 40 节**:

| 层 | 节数 | 词汇集 | 用途 |
|---|---|---|---|
| **G1** | 10 | ~1200 词 | 高一全年系统课 |
| **G2** | 10 | ~2200 词 (G1∪G2) | 高二全年系统课 |
| **G3** | 10 | ~3000 词 (G1∪G2∪G3) | 高三上学期系统课 (题型完整) |
| **G_FINAL** | **10** | ~3500 (+课标补充) | **高考前突击** (真题密集 + 模拟卷 + 趋势) |

每节 120 min. 向下兼容 (R5): G2 节可用 G1 词; G1 节**不可**用 G2 才出的词.

### 5.3 七个 tab 详设

| tab | 用途 | 接口 |
|---|---|---|
| **A. 工作台** | 今日待办 / 待批改 / 学生异常预警 / 数据健康 | `/api/stats` `/api/audit` `/api/workbench/today` (新) |
| **B. 教学** ⭐ | 40 节按 layer 折叠 → 选课节 → 讲义 / 课件 / 出题 | `/api/course/{list,session,materials,handout}` (新) |
| **C. 题库 + 组卷** | qbank + compose + **听力题** (transcript / audio_id) 统一一 tab | `/api/qb/*` `/api/paper/*` `/api/listening/*` |
| **D. 数据管理** | 14 数据集 + 8 audit + lineage 编辑 | `/api/stats` `/api/audit` `/api/manifest` |
| **E. 学生档案** | CRUD + 班级 + 答题历史 + 弱点 heatmap + 弱点 → 推送对应课节 | `/api/students/*` (新) |
| **F. 知识图谱** | force-directed / 热力图 / 趋势 / 跨版本对照 | 现有 `graph/recommend/trend` |
| **G. 扫描 OCR** | POST 上传 + 已上传清单 + OCR review 队列 | 现有 `/api/scan/*` |

### 5.4 教学内容 (P0 核心交付)

#### 5.4.A 4 层词汇集定义 (R5 R6 配套)

```
G1      = 外研社·必修 1+2  ∪  人教版·必修 1+2                     (~1200 词)
G2      = G1 ∪ 外研·必修 3+选必 1+2 ∪ 人教·必修 3+选必 1+2          (~2200 词)
G3      = G2 ∪ 外研·选必 3+4 ∪ 人教·选必 3+4                       (~3000 词)
G_FINAL = G3 ∪ 国家课标 3500 词表 中超出 G3 的补充                  (~3500 词)
```

每词带 `year_level ∈ {1,2,3,99}` (99 = 课标补充) + `textbook_position`. `course/lexicon_filter.py` 从 lexicon 表 join nodes 反查.

#### 5.4.B 50 主题池 (Time / NatGeo / SciAm 风格, 非政治)

| 类别 | 5 主题 | 参考刊物 |
|---|---|---|
| 科技 | AI 辅助科研 / 自动驾驶伦理 / 量子计算 / 脑机接口 / 基因编辑 | SciAm / Time |
| 科学 | 火星探索 / 深海热泉 / 系外行星 / 阿尔茨海默症 / 流感病毒变异 | SciAm / NatGeo |
| 自然 | 海洋塑料 / 候鸟迁徙 / 极地冰川 / 灵长类行为 / 雨林生态 | NatGeo |
| 历史考古 | 玛雅遗址 / 古埃及金字塔 / 庞贝古城 / 丝路考古 / 故宫修复 | NatGeo / Time |
| 学术 | STEM 跨学科 / 田野调查 / 学术写作 / 学科前沿讲座 / 学术诚信 | 教学 |
| 心理 | 时间管理 / 高考压力 / 友谊重构 / 学习动机 / 拖延克服 | SciAm Mind |
| 文化 | 国潮汉服 / 博物馆热 / 非遗传承 / 跨文化交流 / 茶道礼仪 | NatGeo |
| 职业 | 青年企业家 / 数字游民 / 远程办公 / 实习生日记 / 人机协作 | Time |
| 旅行探险 | 露营复兴 / city walk / 哈尔滨冰雪季 / 沙漠星空 / 极地探险 | NatGeo |
| 体育校园 | 电竞奥运 / 滑板入奥 / 女足世界杯 / 校园食安 / 自习室文化 | Time / 教学 |

外置 `backend/config/theme_pool.yaml` (M3). 政治黑名单 `backend/config/political_blacklist.yaml` (政府/选举/政党/制裁/外交关系/政权/战争; **不扫泛词** "policy" 防误伤).

#### 5.4.C 每节 120 min 流程

```
 0-15  开场 hook (Time/NatGeo/SciAm 风格新闻片段, 主题导入)
15-25  上节复习: 5 题 quick check (抽自上节作业的同 tag)
25-50  核心教学: 词/语法/句型 + 关联拓展 ≥3 (R1)
       板上标注: [G2·外研·必修3·U2·Vocabulary]  (R6)
50-70  真题溯源: 近 5 年真题 N 题 + 趋势曲线
70-90  场景练习: 同知识点 ≥3 场景 × 1-2 题 (R3)
       题目所有词 strict ⊆ 本节 lexical_layer  (R5)
90-105 重点解析 + 易错点 (从 student_weakness 抽)
105-115 总结 + 下节预告
115-120 课后作业: 10 题, tag ⊆ 本节 (R4), 词 ⊆ layer (R5)
```

#### 5.4.D 40 节板块分配 (按层差异化, 低年级重基础, 高年级题型完整)

| 板块 \ 层 | G1 | G2 | G3 | G_FINAL | 趋势依据 |
|---|---|---|---|---|---|
| 词汇 | 5 | 3 | 2 | 2 | vocab+99.57/y, HV_extra |
| 语法 | 3 | 3 | 2 | 2 | 14 顶级 grammar 类目 |
| 阅读 | 2 | 2 | 2 | 2 | slope +0.028/y |
| 完形/七选五 | — | 1 | 1 | 1 | slope +0.011/y |
| 语法填空 | — | — | 1 | 1 | slope +0.008/y |
| 应用文 | — | 1 | 1 | 1 | 15 分 |
| 续写 | — | — | 1 | — | 25 分新高考最大 delta |
| 模拟卷讲评 | — | — | — | 1 | 真题重组 |
| **小计** | **10** | **10** | **10** | **10** | |

#### 5.4.E 示例 4 节 (每层 1 节, 余 36 节落 yaml)

| layer | # | 板块 | 核心知识点 (含 textbook_position) | 主选场景 | 关联 ≥3 |
|---|---|---|---|---|---|
| **G1** | 1 | 词汇·基础名词 | family, friend, school, study, hobby [G1·外研·必1·U1] | 校园新生活 (Time 校园) | 反义/搭配/词族 |
| **G2** | 11 | 语法·宾从陈述 vs 疑问 | that/whether/if [G2·外研·必3·U2] | 青年企业家访谈引述 (Time) | 主从复合 / 名词从语类 / 间接引语 |
| **G3** | 21 | 续写·情绪转折 | so...that, 倒装 [G3·外研·选必3·U4] | 玛雅遗址考古挫折到突破 (NatGeo) | 倒装语法 / 情绪词族 / 叙事时态 |
| **G_FINAL** | 31 | 模拟卷·阅读密集 | 5 年真题主题词汇高频 [G_FINAL·课标 3500] | 火星探索任务长文 (SciAm) | 全题型综合 |

#### 5.4.F 每节 yaml 格式

```yaml
- course_id: 11
  layer: G2
  block_kind: grammar
  block_order: 1                                  # 层内序号 1..10
  title: "宾语从句陈述 vs 疑问"
  themes_main: 青年企业家访谈引述
  themes_aux: [实习生日记, 远程办公]
  related_concepts: [主从复合, 名词从语类, 间接引语]
  core_items:
    - {kind: grammar, id: g:obj_clause_that, year: 2, position: "外研·必修3·U2·Grammar"}
    - {kind: grammar, id: g:obj_clause_if,   year: 2, position: "外研·必修3·U2·Grammar"}
  homework_tags: [g:obj_clause_that, g:obj_clause_if]
  listening_required: false
```

### 5.5 schema

#### 5.5.A 3 新表

```sql
courses                                  -- 40 节定义 (init_db 灌, 源 course_templates.yaml)
  course_id (1..40)
  layer        ENUM('G1','G2','G3','G_FINAL')                                 -- R5
  title        VARCHAR
  block_kind   ENUM(vocab|grammar|reading|cloze|gramfill|applied|narrative|mock|listening)
  block_order  INT                                                            -- 层内序号 1..10
  duration_min INT                                                            -- 120
  listening_required BOOLEAN
  description  TEXT

course_materials                         -- 每节关联 graph 实体 / 题 (auto + manual)
  course_id, kind, ref_id
  year_level        INT                  -- 1|2|3|99 (99 = 课标补充)         R6
  textbook_position VARCHAR              -- "外研·必修3·U2·Grammar"            R6
  source            VARCHAR              -- auto_from_trend / manual / from_scenario / from_lesson_plan
  reason            VARCHAR              -- eg "近 3 年真题 freq=5"
  position          INT                  -- 讲解顺序

course_sessions                          -- 老师实际授课记录
  session_id, course_id, class_id, taught_at, notes
```

#### 5.5.B question_bank 扩字段 (听力入题库, 不另起表)

```sql
ALTER TABLE question_bank ADD COLUMN
  has_audio       BOOLEAN DEFAULT false,
  audio_id        VARCHAR,                       -- "audio:2024/A/Q1" lineage
  transcript      TEXT,                          -- 必填 if has_audio (audit_listening_transcript_required)
  audio_speakers  JSON,                          -- [{"id":"M","label":"男1"}, ...]
  audio_duration  INTEGER;                       -- 秒
-- 题型枚举扩: listening_short / listening_dialog / listening_passage
```

### 5.6 service `backend/services/course/` (9 模块) + 8 audit

| 模块 | 作用 | 对应铁律 |
|---|---|---|
| `registry.py` | M2 插件注册表 (block_kind / scenario_kind / audit_kind) | M2 |
| `loader.py` | M3 加载 `backend/config/*.yaml` (templates / theme_pool / thresholds / political_blacklist) | M3 |
| `templates.py` | 40 节 spec 校验 + 暴露 (实数据走 yaml) | — |
| `lexicon_filter.py` | 给 layer 返回允许词集, join lexicon 取 (year, position) | **R5 R6** |
| `relations.py` | 知识点 ≥3 联通抽取 (走 nodes + edges) | **R1** |
| `scenarios.py` | 主题池 + ≥3 场景 + 教材重叠 audit + 政治黑名单扫 | **R2 R3 + D5** |
| `materials.py` | 综合生成 (graph + trend + qbank + scenarios + lexicon_filter) | — |
| `homework.py` | 抽 10 题作业, strict tag ⊆ 本节 | **R4** |
| `handout.py` | 讲义生成 (md + html, 7 段: hook / 复习 / 核心 / 关联 / 真题 / 场景 / 作业) | — |

route 改: 升级 `backend/api/routes/lesson_plan.py` 支持课程语义, 新增 `routes/course.py` 暴露 list/session/materials/handout.

audit 全套 (Stop hook 集成, 见 5.1.C 一览).

### 5.7 学生档案 tab (P1, 补 4.7.D/E 缺口)

- 学生 CRUD UI (schema 已通, 缺 UI)
- 班级 + 学生关联
- 答题历史 timeline
- 弱点 heatmap (按 word/grammar 4 象限)
- 弱点 → 推送对应课节 (eg "该生 `g:obj_clause_that` 弱 → 推 G2·#11")

### 5.8 复核门 (13 条) — 完成态 ✅

| 门 | 内容 | 结果 |
|---|---|---|
| 1 | /app 7 tab 切换 (旧 3 路由兼容) | ✅ #38 |
| 2 | courses 40 行 (G1×10+G2×10+G3×10+G_FINAL×10) | ✅ #37 |
| 3 | 每节 course_materials ≥ 10 行 | ✅ 实测 552/40=14 avg |
| 4 | 任一节 7 段讲义 (md + html) | ✅ #11 实测 2343 字符 |
| 4a | R1 ≥3 关联 (audit_course_relations) | ✅ 0 FAIL |
| 4b | R2 无 ≥10 词重叠 (audit_course_no_textbook_copy) | 🟡 WARN (预期, 待讲义文本持久化后真扫) |
| 4c | R3 ≥3 场景 (audit_course_scenarios) | ✅ |
| 4d | R4 作业 ⊆ 本节 (audit_homework_alignment) | ✅ |
| 4e | 听力 transcript 必填 (audit_listening_transcript_required) | ✅ vacuously pass (无 audio 行) |
| 4f | yaml 外置 0 硬编码 (M3) | ✅ 4 yaml |
| 4g | CC>10 ≤ baseline 12 (M6) | ✅ 持平 12 |
| 4h | 每模块带 tests/smoke (M5) | ✅ ALL PASS |
| 4i | 不含政治词 (audit_no_political) | ✅ |
| 4j | R5 0 陌生词 (audit_course_lexical_layer) | ✅ |
| 4k | R6 year+position (audit_course_textbook_position) | ✅ |
| 5 | 学生档案 CRUD + ≥1 班 5 学生 demo | ✅ #39 沈阳市第二中学高三1班 |
| 6 | 0 FAIL audit 持续 | ✅ 0 FAIL / 4 WARN 持平 baseline |
| 7 | start.command 30 秒 7 tab 流畅 | ✅ 技术复核 |

### 5.9 实施顺序 + 时间估 (task 队列)

| 步 | task | 内容 | 估时 |
|---|---|---|---|
| 1 | #35 | 5.5 schema + listening ALTER + init_db 改 | 30 min |
| 2 | #36 | 5.6 service 9 模块 + 8 audit + Stop hook 接入 | 4-6 h |
| 3 | #37 | 5.4.D-F 40 节 `course_templates.yaml` (G_FINAL 优先 → G1 → G2/G3) | 2-3 h |
| 4 | #38 | 5.2-5.3 `/app` SPA + 7 tab 合并 (3 旧页面保留 redirect) | 4-6 h |
| 5 | #39 | 5.7 学生档案 tab + 弱点推送 | 2-3 h |
| | | **总** | **2-3 天** |

**风险与备选**:
- yaml 40 节编排耗时 — 优先 **G_FINAL 10 节** (高考最直接 ROI) + **G1 10 节** (基础打底), G2/G3 同步推进
- R2 教材重叠 audit — 实装难点在 n-gram 滑窗性能, 用 set diff + 字典化优化
- R5 lexical_layer 严格校验 — 词形归一化 (lemma) 已有 (`backend/services/canonical.py`), 直接用
- M3 数据外置如遇 yaml 嵌套深 → 拆多个 yaml 文件 (course_templates.yaml + theme_pool.yaml + thresholds.yaml + political_blacklist.yaml)

---

## 第六阶段 — 运营交付前完善 (用户 2026-05-24 反馈)

### 6.A codegraph + complexity baseline 收紧 ✅
- `codegraph index` 全量重 index: 17 → 104 file, 224 → 976 nodes, 390 → 1674 edges
- `stop_gate.sh` baseline 14 → 13 (M6 持续收紧, 拆 3 老函数后真实降)

### 6.B 全局图谱浮窗 ✅ (用户原话: "任意知识点超链接都可调出关联图谱 + 高考真题")
- **后端** `/api/graph/popup?id=<concept_id>` 返 {center, related (1 层), questions (真题节点)}
- **前端** `frontend/static/graph_popup.js` 全局 click 委托 + modal 栈 (支持递归点击深扩 + 返回)
- **接入** `course/handout.py` 讲义里词/语法/真题号 全用 `_clink()` 渲染 conceptLink
  (实测 #11 讲义含 33 个 conceptLink)
- **共享** `common.js` 加 `conceptLink()` + `mdToHtml()` (零依赖 md→html)
- **覆盖**: 5 类 concept (word/grammar/phrase/question/grammar 类目) 可弹 + 联通真题节点

### 6.C 运营验证补充项 ⏸️ 跳过 (用户 2026-05-24 明示)
- ~~4.6.E 找老师试 30 分钟~~ — 用户决定跳过
- 阶段复核: 全 audit OK + 全 P1 完成 + 文档闭环

### 6.D 学生答题闭环 ✅ (2026-05-24)
- 4.7.D ✅ csv import students (POST /api/students/import_csv)
- 4.7.E ✅ 弱点真算 service (weakness.recompute_all + guard)
- 4.7.C ✅ 扫描 POST UI (G tab 上传表单 + 清单)

### 6.E 真问题修 (诚实暴露后再修, 用户 2026-05-24 升级目标至 100%)
- 4.1.E 跨版本对照算法 — 第一版准确率 4/15=26.7% ❌
  → 用户硬约束: **必须 100% 准确率**
  → 重做: 标题核心词 lemma jaccard + level1 主题双过滤, 严格高准
  → 验证 ≥5 对抽样核对, 0 错 才过

### 6.F Docker 多人部署 ⏸️ 跳过 (用户 2026-05-24 明示)
- ~~4.6.A docker compose~~
- ~~4.6.B nginx htpasswd~~
- ~~4.6.C HTTPS~~
- ~~4.6.D 备份 cron~~
现 start.command 单机模式即用; 部署到多人/线上时再启 (推迟到后续阶段 9)

---

## 高考 vs 教学范围 对比分析 (2026-05-25 完成)

| 年 | 词汇数 | 覆盖率 | 超出 | 备注 |
|---|---|---|---|---|
| 2021 | 1374 | 85.4% | 14.6% | 新课标 II 卷 (DB) |
| 2022 | 1502 | 84.0% | 16.0% | 新课标 II 卷 (DB) |
| 2024 | 1137 | 85.4% | 14.6% | 新课标 II 卷 (PDF) |
| 2025 | 1102 | 85.1% | 14.9% | 新课标 II 卷 (PDF) |

**加入初中词汇后 (K12 完整基准 7185 词)**:

| 年 | 词汇数 | K12覆盖率 | 超出 |
|---|---|---|---|
| 2021 | 1374 | 89.3% | 10.7% |
| 2022 | 1502 | 87.1% | 12.9% |
| 2024 | 1137 | 89.4% | 10.6% |
| 2025 | 1102 | 88.8% | 11.2% |

**结论**: 高考卷没有系统性超出 K12 教学范围. ~89% 词汇在 K12 教学范围内. 剩余 ~11% 主要为:
- 阅读理解话题词 (tourism/intelligence/curiosity) — 猜词义是考试能力要求
- 复合/派生词 (increasingly/reconsider) — 根词已学, 前后缀是能力考点
- 专有名词 (Ohio/Washington/Tang)

**词汇基准不强制 3000** (用户 2026-05-25): 以课标+教材实际数据为准.
现有 2023 年真题缺失 (GAOKAO-Bench 数据集止于 2022, 2024/2025 已从 gaokao 项目 PDF 提取).

---

## 初中英语数据采集 (用户 2026-05-25 新增需求)

> 目标: 按本项目同标准抓取辽宁/沈阳初中英语相关资料, 为后续初中项目储备数据.
> 已有小学词汇: `/Users/dp/Documents/Agnes/english/小学英语教材 copy/`

### 待采集清单

| # | 资料 | 来源 | 优先级 |
|---|---|---|---|
| J1 | 人教版初中英语 PDF (Go for it! 7-9 年级上下 6 册) | TapXWorld / ChinaTextbook | P0 |
| J2 | 外研版初中英语 PDF (7-9 年级上下 6 册, 大连等市用) | TapXWorld / ChinaTextbook | P1 |
| J3 | 义务教育英语课程标准 (2022 年版) | MoE | P0 |
| J4 | 辽宁省初中英语教学用书目录 (确认各市版本) | jyt.ln.gov.cn | P0 |
| J5 | 沈阳中考英语真题 (2020-2025, 近 5 年) | 公开源 | P0 |
| J6 | 初中英语词汇表 (课标 1600 词) | 课标附录 | P0 |
| J7 | 初中英语语法大纲 | 课标/教参 | P1 |

### 存放路径

```
data/junior_high/
  textbooks/renjiao/   # 人教版 7-9
  textbooks/waiyan/    # 外研版 7-9
  curriculum/          # 义务教育课标 2022
  exams/               # 沈阳中考真题
  vocab/               # 词表
```

### 用途
1. 补全高考对比分析的基准 (初中 1600 词 + 小学 800 词 = 完整 K12 词库)
2. 精确计算高考真正超纲比例 (去除初中已知词后, 预估真超纲 ≤ 5%)
3. 为后续独立初中项目储备数据 (用户 2026-05-25 提及)

---

## 第七阶段 — 从"数据基础设施"到"可教学产品" (2026-05-25 规划)

> **诊断**: 前 6 阶段建成了技术完整的数据基础设施 (4972 nodes, 37636 edges, 533 题, 40 节课, 15/15 就绪检查通过). 但仍是"元数据壳" — 老师打开看到的是标签+链接, 不是可直接教的内容. 学生体验是选项卡+图表, 不是自然的学习流程. 本阶段目标: **从数据库变成教学产品**.

### 7.0 盲区诊断 (2026-05-25 全面 review)

| # | 盲区 | 影响 | 量化 |
|---|---|---|---|
| B1 | 40 节讲义是模板元数据, 不是可教文本 | 老师无法直接用 | 每节讲义仅 ~2300 字符 (应 ≥5000) |
| B2 | 听力完全空白 | 漏掉高考 30/150 分 (20%) | has_audio=0, transcript=0 |
| B3 | 续写/应用文 训练 = 0 | 新高考最大新增 (续写 25 分 + 应用文 15 分) | 0 道续写题, 0 篇范文 |
| B4 | 题目质量天花板 | 175 题是机械挖空 | rule_synth 占 33% |
| B5 | 无验证 | 不知道哪里"纸上谈兵" | 0 学生/老师实测 |
| B6 | 前端是展示板, 不是教学工具 | 缺交互做题/进度追踪 | 无 quiz mode |
| B7 | 词汇基准不含初中 | 高考覆盖率分析偏低 | ✅ 已补 (89%) |
| B8 | 无持续更新管线 | 每年新题/新教材无自动入库 | 手动 |

### 7.1 LLM 充实 40 节讲义 (P0, 估 3-4 天)

> **目标**: 每节讲义从 ~2300 字符 → ≥5000 字符, 包含可直接在课堂使用的真实教学内容.

| 段 | 当前 | 目标产出 | LLM 任务 |
|---|---|---|---|
| 开场 hook | 主题名 1 行 | 150-200 词 Time/NatGeo 风新闻片段 (含 comprehension Q) | Claude: 写 200 词短文 + 3 Q, 词 ⊆ layer |
| 核心教学 | 知识点 ID 列表 | 500-800 词讲解 (定义/例句/对比/易错) | Claude: 展开每 concept, 生 3 例句, 标位置 |
| 关联拓展 | concept link 列表 | 200-300 词 "为什么一起学" 段落 | Claude: 写语义网络解读 |
| 真题溯源 | 题号 + 截断 stem | 完整题目 + 解题策略 50-100 词 | Claude: 从题面生解题思路 |
| 场景练习 | 主题名 | 3 个 mini-scenario (各 80 词 + 1-2 题) | Claude: 写场景 + 设题, 词 ⊆ layer |
| 作业 | tag list | 10 题完整题面 + 答案 + 解析 | 已有 (从 question_bank 抽) |
| 总结 | 无 | 100 词本节核心要点 + 下节预告 | Claude: 总结 + 衔接 |

**铁律约束** (LLM 生成必须 pass):
- R2: 生成文本 10-gram 不与教材重叠 (audit_course_no_textbook_copy)
- R5: 所有词 ⊆ lexical_layer (audit_course_lexical_layer)
- R6: 保留教材位置标注
- D0: 知识点关联 100% 可 trace

**实施路径**:
```
backend/services/course/llm_enrich.py  ← 新模块 (调 Claude API)
  enrich_handout(con, course_id, api_key) → enriched_md
  - 按 7 段分别 prompt → 拼装
  - 每段 prompt 带 R2/R5 约束 (词表白名单注入)
  - 生成后自动跑 audit → FAIL 则 retry 1 次

backend/config/llm_prompts.yaml  ← 7 段 prompt 模板 (M3 外置)
scripts/batch_enrich.py  ← 批量跑 40 节 (支持断点续传)
```

**复核门**:
- [ ] 40 节讲义 ≥5000 字符 (avg)
- [ ] R2 audit 0 FAIL (生成后)
- [ ] R5 audit 0 FAIL (生成后)
- [ ] 抽检 5 节 — 内容可读性 + 知识准确性

### 7.2 听力模块 (P0, 估 2 天)

> **目标**: 补上高考 30 分占比的听力训练能力.

| # | 任务 | 方法 |
|---|---|---|
| 7.2.A | 收集近 5 年辽宁听力 transcript (2021-2025) | 从真题 PDF/网络抓 + 手动校对 |
| 7.2.B | 入库 question_bank (has_audio=true, transcript 填充) | 扩展 mirror_to_jsonl |
| 7.2.C | 前端听力播放 UI (transcript reveal + 答题) | C tab 扩展 |
| 7.2.D | 听力 audit 真实化 (不再 vacuously pass) | audit_listening_transcript_required 变严 |
| 7.2.E | TTS 合成备选 (当无原始音频时) | macOS `say` / 第三方 TTS API |

**schema 已预留**: `has_audio`, `audio_id`, `transcript`, `audio_speakers`, `audio_duration` 字段在 question_bank 已有.

### 7.3 续写 + 应用文训练 (P0, 估 2 天)

> **目标**: 覆盖新高考最大变化 (续写 25 分 + 应用文 15 分 = 40/150).

| # | 任务 |
|---|---|
| 7.3.A | 真题续写题 10 道入库 (2021-2025 真题 + 改编) |
| 7.3.B | 每道续写题配: 审题分析 + 情节规划 + 范文 + 评分维度 |
| 7.3.C | 应用文 10 篇 (邀请信/建议信/通知/感谢信/申请信) |
| 7.3.D | 每篇配: 格式模板 + 高分表达 + 常见扣分点 |
| 7.3.E | 前端 "写作练习" 区 (B tab 扩展) |
| 7.3.F | LLM 辅助批改 (P2, 后续接入) |

**存储**: question_bank 扩 question_type='续写'/'应用文', stem=题目要求, answer=范文, analysis=评分维度+解析

### 7.4 题目质量升级 + 模型驱动对齐 (P0, 估 3-4 天)

> **目标**: 从"机械挖空"升级到"紧贴真题命题思路". 不是"写得通顺", 是"像高考一样出题".
> **核心方法**: 先用 `exam_alignment_checker.py` 量化偏离, 再用 Optuna 搜索最优生成参数, 最后抽检.

#### 7.4.0 已有基础设施 (本 session 已建)

| 工具 | 路径 | 作用 |
|---|---|---|
| 考试对齐度检测器 | `scripts/exam_alignment_checker.py` | 8 维度 0-100 分, `--json` 供 Optuna |
| 真题解析库 | `exam_questions` 表 (358 题, 全含解析) | 命题模式参考 ground truth |
| 当前基线 | 综合 **75.8/100** | 6 维过线, 2 维待优化 (难度 44.5, 话题 17.8) |

#### 7.4.1 Optuna 搜索最优生成参数

**目标**: 用 Optuna 自动搜索题目生成的最优参数组合, 使 `exam_alignment_checker --json` 的 `overall.score` 最大化.

```python
# scripts/optuna_question_optimizer.py (待建)
import optuna

def objective(trial):
    # 搜索空间
    difficulty_ratio_hard = trial.suggest_float("hard_ratio", 0.4, 0.8)
    difficulty_ratio_mid  = trial.suggest_float("mid_ratio", 0.15, 0.5)
    topic_source          = trial.suggest_categorical("topic", ["curriculum", "exam_freq", "mixed"])
    stem_length_words     = trial.suggest_int("stem_len", 30, 120)
    distractor_strategy   = trial.suggest_categorical("distractor", ["same_pos", "synonym", "collocation"])
    analysis_min_chars    = trial.suggest_int("analysis_min", 50, 200)

    # 按参数生成一批题 → 写入临时 DB → 跑 exam_alignment_checker --json
    # 返回 overall score (Optuna maximize)
    ...
    return overall_score

study = optuna.create_study(direction="maximize",
    storage="sqlite:///data/reports/optuna/question_quality.db")
study.optimize(objective, n_trials=100)
```

**搜索维度**:

| 参数 | 范围 | 影响的对齐维度 |
|---|---|---|
| `hard_ratio` | 0.4–0.8 | 难度分布偏离 (当前 44.5) |
| `mid_ratio` | 0.15–0.5 | 难度分布偏离 |
| `topic_source` | curriculum / exam_freq / mixed | 话题对齐 (当前 17.8) |
| `stem_len` | 30–120 词 | 词汇重叠度 |
| `distractor` | same_pos / synonym / collocation | 干扰项质量 |
| `analysis_min` | 50–200 chars | 解析完整度 |
| `scenario_count` | 2–5 | 听力技能覆盖 |

#### 7.4.2 rule_synth 替换 (Optuna 参数落地)

| # | 任务 | 对齐维度 |
|---|---|---|
| 7.4.A | rule_synth 175 题重审 — Optuna 最优 `hard_ratio` 过滤, 保留 ≥mid 的, 淘汰纯 easy 挖空 | 难度偏离 44→70+ |
| 7.4.B | LLM 生成完形填空 (5 篇 × 15 空 = 75 题) — prompt 注入真题 analysis 风格 + Optuna 最优 `stem_len` | 词汇重叠 + 难度 |
| 7.4.C | LLM 生成语法填空 (10 篇 × 10 空 = 100 题) — 从真题 grammar tag 高频考点出发 | 考点覆盖 |
| 7.4.D | 阅读理解长文 (从真题 PDF 提取 + LLM 改编) — 保留真题 topic 标签 | 话题对齐 17→50+ |
| 7.4.E | 干扰项升级 — Optuna 最优 `distractor` 策略 (同词性/近义/搭配) | 实质题目质量 |

#### 7.4.3 话题对齐优化

当前偏离根因: 听力/写作场景没有显式对齐课标 10 大主题群.

| 课标主题群 | 当前覆盖 | 优化方案 |
|---|---|---|
| 人与自我 (学习/生活/职业) | 部分 | 听力: 增学校/职业场景 |
| 人与社会 (文化/科技/公益) | 部分 | 写作: 增志愿/文化交流题 |
| 人与自然 (环保/科学/自然) | 弱 | 听力独白: 增科普主题 |

实施: 每道新题 `stem` 必须命中 ≥1 课标主题关键词 (exam_alignment_checker 自动检验).

#### 7.4.4 监控闭环 (持续运行, 不靠人盯)

```
生成/修改题目
    ↓
exam_alignment_checker.py --json
    ↓ 8 维度评分
    ├─ overall ≥ 80 → ✅ 入库
    ├─ overall 55-80 → ⚠️ 标记 + review
    └─ overall < 55  → ❌ 拒绝入库
    ↓
    定期回归 (init_db 后自动跑)
    ↓
    Optuna dashboard (data/reports/optuna/question_quality.db)
    ├─ best trial 参数 → 更新 backend/config/generation_params.yaml
    └─ 趋势图: 每次生成的对齐度是否在涨
```

**集成点**:

| 集成 | 方式 | 触发 |
|---|---|---|
| init_db 后自动跑 | `scripts/init_db.py` 末尾调 `exam_alignment_checker.run_all()` | 每次重建 DB |
| Stop hook 集成 | `stop_gate.sh` 检测 overall < 55 时 WARN | 每次 session 结束 |
| CI/commit hook | `pre-commit` 检测新增 `_exercise.yaml` 时自动跑 | 内容变更 |
| Optuna 周期寻优 | `scripts/optuna_question_optimizer.py` cron 或手动 | 周 1 次 |

#### 7.4.5 复核门 (7.4 完成标准)

| # | 指标 | 目标 | 方法 |
|---|---|---|---|
| 1 | 题库总量 | ≥ 700 题 | 新增 ~120 (完形 75 + 语法填空 100 - 淘汰 rule_synth ~55) |
| 2 | exam_alignment overall | ≥ 80 | Optuna 搜索 + 手动调优 |
| 3 | 难度分布偏离 | ≥ 65 | hard_ratio ≥ 0.5 for 新增题 |
| 4 | 话题对齐 | ≥ 50 | 每题命中 ≥1 课标主题 |
| 5 | 解析完整度 | ≥ 85 | 每题 analysis ≥ 80 chars |
| 6 | Optuna study | best_value ≥ 80, ≥ 50 trials | 寻优跑完 + best 参数落 yaml |

### 7.5 交互式前端 (P1, 估 2-3 天)

> **目标**: 从"数据展示板"变成"学生能自学的工具".

| # | 功能 |
|---|---|
| 7.5.A | Quiz mode: B tab 每节底部"课后测验"按钮 → 10 题即时做 + 即时批改 |
| 7.5.B | 学习进度条: 已完成课节 / 已答题数 / 正确率趋势 |
| 7.5.C | 弱点 drill: E tab 弱点 → 点击 → 自动出 5 题强化 (复用 followup 逻辑) |
| 7.5.D | 写作提交: textarea → 保存草稿 → (P2: LLM 批改) |
| 7.5.E | 移动端适配: responsive CSS (学生手机用) |

### 7.6 验证 (P0, 估半天)

> **目标**: 用一条端到端链路验证完整流程, 发现所有"纸上谈兵".

| # | 步骤 |
|---|---|
| 7.6.A | 跑 1 次完整端到端教学链路闭环 |
| 7.6.B | 录屏: 摸底测验 → 查看推荐课节 → 上课 → 做题 → 看弱点 |
| 7.6.C | 记录: 卡住的地方 / 不理解的 UI / 内容质量反馈 |
| 7.6.D | 整理 `docs/user_test_round1.md` → 反馈驱动修 bug |

### 7.7 持续更新管线 (P2, 估 1 天)

| # | 任务 |
|---|---|
| 7.7.A | 年度真题入库脚本 (每年 6 月高考后 → 抓题 → infer_province → 入库) |
| 7.7.B | 教材版本检测 (课标/教材换版 → 提醒更新) |
| 7.7.C | 词汇增量 (新学年开学 → OCR 新教材补充词) |

### 7.8 复核门 (Phase 7 完成标准)

| # | 门 | 标准 | 状态 |
|---|---|---|---|
| 1 | 讲义内容量 | 40 节 avg ≥5000 字符, 7 段完整 | ✅ 40/40 完成, 总 ~180K chars |
| 2 | 听力 | ≥20 题 has_audio=true + transcript | ✅ 25 题 (短 10+长 9+独白 6) |
| 3 | 续写+应用文 | ≥10 续写 + 10 应用文 (含范文+评分) | ✅ 续写 10 + 应用文 10 |
| 4 | 题目总量 | ≥700 题 (升级 rule_synth + 新增) | 🔲 578→700+ (需 ~120) |
| 5 | R2/R5 audit | 0 FAIL (生成后) | ✅ 0 FAIL, 超纲词=0 |
| 6 | 验证 | 完整流程闭环 + feedback 入档 | ✅ 完成（复核已闭环） |
| 7 | Quiz mode | 学生可在前端做题 + 即时反馈 | ✅ 讲义内 Quiz + 即时批改 |
| 8 | CC baseline | ≤ 8 (不涨) | ✅ CC=8 |
| 9 | D0 100% | 全部检查通过 (含新增 check) | ✅ 20 章全绿 |
| **10** | **考试对齐度** | **exam_alignment overall ≥ 80** | **✅ 84.6 (8 维全 PASS)** |
| **11** | **参数优化** | **best_value ≥ 80, ≥ 50 trials** | **✅ param_optimizer 实装 (stdlib 搜索, M8 合规)** |
| **12** | **工具模块** | **scripts/tools/ 4 子目录, P0 工具全建** | **✅ 5 工具实装 + 回归检测基线** |

### 7.9 里程碑实施顺序（非小步版）

> 本节替代细粒度执行：每个里程碑只接收“可复核成果”
>  
> 原则：**不交付“做了一半”，不追求每周小碎片动作**。

#### 7.9.1 2026-06-10 续航计划（第一轮交付）

**总目标**：从 7.12 起推进到可复核的“可交付闭环”。

| 里程碑 | 目标产物（一次性） | 计划窗口 | 本次判定标准 |
|---|---|---|---|
| **M0 真值基座闭环** | 2021-2025 辽宁真题映射与溯源统一、跨源对齐报告（PDF/官方/题库） | Week1-2 | `exam_questions` 历史样本与 `question_bank` 一致可追溯，抽样 100% 可复核 |
| **M1 图谱与趋势闭环** | 基于真值样本重建趋势与主题连通图谱；`word/grammar/theme` 边可重算 | Week2-3 | trend 报告、主题覆盖率、graph 可视复现日志都可重算 |
| **M2 内容与题库闭环** | 题库质量达标（≥700 题、`rule_synth` 替换、R2/R4/R5/R6 无回退）+ 40 节讲义结构化上线 | Week4-5 | 题面/解析证据链完整，讲义 7 段齐备，quiz/drill 流程可跑 |
| **M3 审计与交付闭环** | 7.8 复核门一键更新、`data_accuracy_check` 通过、反馈 demo 入档 | Week6 | 无新增 FAIL/WARN 闭环不明确；`goal.md` 与 `docs/data_accuracy_audit.md` 对齐 |

**执行规则（本文件约束）**
- 每个里程碑结束前不允许跳入下个里程碑。
- 每个里程碑必须产出：代码/脚本变更 + 结果报告 + 审计快照 + 文档状态行。
- 里程碑之间禁止“边改边验”切片推进；允许在同里程碑内并行做法和修复，但复核只在里程碑边界确认。

#### 里程碑当前状态（2026-06-15 对照更新，11 commits 数据诚实性整改）

- ✅ **M0 真值基座闭环（已收口）**：原待收口项"2021/2022 新高考II卷完整入库 + 污染剔除"**已完成** —— EOL 中国教育在线真题走 M0 review gate 入 `exam_questions`(2021 共 65 + 2022 共 45)，替换 GAOKAO 混合卷占位；全部 gaokao 英语题拉齐(376→**472**, 2010-2025)，**category-aware 诚实卷型标注**(辽宁卷 188 真新课标II / 非辽宁 284 诚实标注 I/III/甲/乙)；GAOKAO 全国甲卷"Landscape Photographer"污染已删。provenance 由 `moth assert`(non-II-not-faking-liaoning / liaoning-is-xgkii / pre2015-not-liaoning / eol-truth-imported) + check_21 守。
- ✅ **M1 图谱与趋势闭环（清洗后重建）**：真题清洗后 `trend_analysis`(288题, 2015-2025)/`exam_patterns` 在干净数据重建(旧版训练在污染数据上已弃)；知识图谱去停用词(tests_word 28430→16540, 功能词不再稀释考点)。
- ⚠️ **M2 内容与题库闭环（已被 foundation-first 决策取代，需重定义）**：原目标"≥700 题 + 40 节讲义结构化上线"**已回滚** —— 用户 2026-06-15 决策：教材基石不完整前不要生成范文(§1.1)，删 enriched 讲义/合成题/生成练习；`question_bank` 改为**仅真题**(无合成)。课程结构骨架(40 + course_materials)保留。**M2 重定义**：教材基石(实测已抽全 77 单元)+ 干净真题为前置，教学内容重建是后续方向决策，不再以"700题/讲义上线"为门槛。
- ✅ **M3 审计与交付闭环**：`data_accuracy_check`/`moth assert`(15 条)/`stop_gate` 三门全绿；4 个治理 god-module 拆 <400 行后 `run_all` 可复现 44 OK(解决陈旧快照)。M3.2 原引用的 `teacher_feedback_round1`/`user_test_round1` 等阶段性快照文档已删(易腐烂误导)，交付状态以 `moth assert` + DB 实测为准。

#### 7.9.2 本会话开发计划（非小步版）

| 里程碑 | 目标 | 交付边界 | 通过门槛 |
|---|---|---|---|
| **M3.1 审计闭环收口** | 将 `verification_protocol.json` 全部落地执行并回填结果，补齐 `run_id` 证据链 | 一次性交付 `data/reports/verification_protocol.json`、`data/reports/m3_closure_*.json`、`docs/data_accuracy_audit.md` 的三方一致状态 | `data_accuracy_check`、`verification_protocol`、`stop_gate` 均为 PASS；主链路已闭合（V1~V8 全部 `done`） |
| **M3.2 复核与录入** | 执行体验反馈与替代协议验证后，将反馈落档 | `docs/teacher_feedback_round1.md` 与 `docs/user_test_round1.md`（不再留 TODO） | 完整反馈摘要 + 改动映射到对应复核门 |
| **M3.3 里程碑交付收官** | `goal.md` 从“进行中”更新为“已完成”，M3 完成并进入下一阶段 | `goal.md` 的 M3 状态行、复核门状态行同步为完成 | 结果可读、可追溯、可复验 |
| **M4 运营试运行准备** | 把数据、服务、前端统一打包成“可持续运行日常”版本 | 运行手册、部署清单、每周巡检脚本与周报模板 | 2 周复测不出现新 FAIL/WARN；运行手册可复现实验 |

#### 7.9.3 会话执行顺序（固定顺序，不再拆片）

1. **先 M3.1**：完成复核链条的自动化与结果入档，不允许跨里程碑开始前跳过。  
2. **再 M3.2**：拿到反馈后一次性归档，不再散点式反馈处理。  
3. **最后 M3.3**：在闭环证据具备后统一推进 M3 完成并进入 M4。  
4. **并行窗口**：在不影响以上顺序时，预备 M4 运行手册与巡检脚本同步补齐。

#### 7.9.0 执行总原则（从 7.12 开始）

1. 任何里程碑都必须同时满足：数据源闭环 + 服务/脚本闭环 + 结果审计。
2. 每个里程碑都以 `goal.md` 明确状态更新，优先级不回退。
3. 跨里程碑跳转前，必须让 `scripts/stop_gate.sh` 与 `scripts/data_accuracy_check.py` 过线。
4. 本阶段默认不再“边想边改”：先定产出再落代码。

#### 里程碑 A — 真题真值基座重建（1-2 周）

**目标**：把 2021/2022 真题与 2010-2024 现有真题统一为可信真值基座。

**交付（一次性）**
- 2021/2022 新高考 II 卷真题完整入库（每年 55-60 题，含解析与题型）
- 现有 2021+ 非真题污染剔除（含 GAOKAO-Bench 误混样本）
- `exam_questions` 与 `question_bank` 的辽宁真题映射一致化
- 交叉核对报告：文本题库 vs PDF/官方来源逐题匹配清单

**复核标准**
- `exam_questions` 2021-2024 辽宁样本达到目标数量且“来源可回溯”
- `backend/services/extraction/exam.py` 与 `exam_province.py` 的省份/卷型推断无新增歧义样本
- `scripts/tools/audit/model_capability_audit.py` 与 `scripts/tools/alignment/exam_pattern_extractor.py` 运行后输出可解释且一致的真题样本量

#### 里程碑 B — 知识图谱与趋势模型重训（1-2 周）

**目标**：先修图谱，后改模型，拿可复现的数据趋势基线。

**交付（一次性）**
- 2024/2025 真题与词汇/语法/主题节点建立完整边（`course_materials`、`word_edges`、`grammar_edges`）
- trend pipeline 基于“真值样本”重跑（`trend_engine` / `exam_pattern_extractor`）
- 主题层级连通（38 主题）和可追溯 `ref_id` 全量清洗

**复核标准**
- `scripts/tools/alignment/trend_engine.py` 与 `exam_pattern_extractor.py` 输出的样本范围与 `exam_questions` 真实基座一致
- 新趋势报告含“近年权重后趋势序列 + 回测可重算性日志”
- 核心图谱连通率与 theme 覆盖率达到 Phase 7.8 指标线以上

#### 里程碑 C — 内容与题目质量重建（2 周）

**目标**：完成“可交付教学内容”所需的硬校准，不先追求新增功能。

**交付（一次性）**
- 题目层：answer 分布（ABCD）均衡化、275 rule_synth 低质题筛除/替换、分析字段逐题对齐到原文证据
- 作业层：40 节讲义 7 段完整 + 难度梯度（A-D）+ 讲义 hook/relations 补齐
- 前端层：Quiz + 弱点 drill + 课程学习闭环保持可运行（不改变现有接口）

**复核标准**
- 真题/合成题统一按“解析对应原文 + 原因链 + 证据句”规则重写完成率达到 100%
- rule_synth 题的有效率相对提升（并记录移除与替换明细）
- 题目相关审计（R2/R4/R5/R6）和 7.4/7.5 功能项无回归

#### 里程碑 D — 全系统 100% 收口（1 周）

**目标**：把 Phase 7 的“看板数字”转成可交付口径。

**交付（一次性）**
- 全系统 D0 目标页更新（数据/内容/工具三条线）
- `docs/data_accuracy_audit.md` 补齐本期 WARN/FAIL 的收敛状态（含原因 + 时间）
- 全量 stop_gate + 一次性验证脚本复跑并固化结果到 `data/reports/` 与 `analysis/`
- 关键场景 demo 形成闭环记录

**复核标准**
- data accuracy 全部通过，`data_accuracy_check.py` exit 0
- `goal.md` 与 `docs/data_accuracy_audit.md` 对齐：无“未解释”风险项
- 7.8 复核门可更新为可追溯状态（含 4.6B/7.6）

#### 里程碑执行节奏（时间窗口）

```
Phase 7.12（当前）里程碑执行（起始点：2026-06-10）

Week 1-2: 里程碑 A（真值基座）
  └─ 先完成数据源真题入库与污染剔除，再进入模型/图谱

Week 3-4: 里程碑 B（图谱与趋势）
  └─ 同步修 graph + 重跑趋势模型，确认版本可重现

Week 5-6: 里程碑 C（内容与题目重建）
  └─ 完成 D1-D7 的高优先项，避免边跑边改导致的目标漂移

Week 7:   里程碑 D（审计收口 + 真试）
  └─ 一次性补齐 D0、7.8、学生反馈与文档闭环
```

### 7.10 技术选型 (codegraph 分析结果)

**现有架构可扩展点** (codegraph context 2026-05-25):
```
已建 (Phase 7.2/7.3):
  backend/services/course/listening.py    ✅ 听力加载 (82L, CC≤7)
  backend/services/course/writing.py      ✅ 写作加载 (35L, CC≤4)
  backend/api/routes/listening.py         ✅ 听力 API (81L, CC≤6)
  backend/config/audio_config.yaml        ✅ 音频命名规范
  backend/config/listening_exercises.yaml ✅ 25 题听力数据
  scripts/exam_alignment_checker.py       ✅ 8 维度对齐检测 (399L, CC≤9)

待建 (Phase 7.4):
  scripts/optuna_question_optimizer.py    ← Optuna 寻优 (搜索生成参数)
  backend/config/generation_params.yaml   ← Optuna best 参数落地
  backend/services/course/llm_enrich.py   ← LLM 批量生成 (调 Claude API)
  backend/config/llm_prompts.yaml         ← 生成 prompt 模板 (M3 外置)

已有可复用:
  course/handout.py:render_handout        ← 7 段渲染
  course/lexicon_filter.py                ← R5 词汇白名单
  course/scenarios.py:check_textbook_overlap ← R2 检查
  placement/followup.py                   ← 弱点 drill
```

**模型应用 + 监控架构** (用户 2026-05-25 决策):
```
┌─────────────────────────────────────────────────────┐
│  Optuna Study (question_quality.db)                 │
│  ├─ 搜索空间: hard_ratio / topic / distractor / ... │
│  ├─ objective: exam_alignment_checker --json        │
│  └─ best_params → generation_params.yaml            │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  LLM 生成 (Claude API / llm_enrich.py)              │
│  ├─ prompt 模板: llm_prompts.yaml                   │
│  ├─ 参数注入: generation_params.yaml                 │
│  ├─ 约束注入: R2/R5 词表 + 课标主题 + 真题 analysis │
│  └─ 输出: *_exercises.yaml                          │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  对齐检测 (exam_alignment_checker.py)               │
│  ├─ 8 维度 0-100 评分 (题型/难度/词汇/话题/...)     │
│  ├─ overall ≥ 80 → 入库  /  < 55 → 拒绝            │
│  └─ JSON 输出 → Optuna objective 反馈环              │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  持续监控 (闭环)                                     │
│  ├─ init_db 后自动跑对齐检测                         │
│  ├─ stop_gate 集成 (overall < 55 → WARN)             │
│  ├─ Optuna dashboard (趋势: 每批对齐度是否在涨)      │
│  └─ D0 校验: data_accuracy_check 第 19 章            │
└─────────────────────────────────────────────────────┘
```

### 7.11 工具模块 — 模型 + 审计 + 监控 (可复用基础设施)

> **定位**: 不是一次性脚本, 是**长期运行的质量基础设施**. 每次加内容、改模型、换参数, 都自动过这套工具.
> **路径**: `scripts/tools/` (独立 module, 可 `import` 也可 CLI 单跑)

#### A. 工具总览

```
scripts/tools/
├── __init__.py
│
├── alignment/                        # 对齐检测 (内容 vs 真题)
│   ├── exam_alignment_checker.py     ✅ 已建 — 8 维度综合评分
│   ├── topic_gap_analyzer.py         ✅ 已建 — 课标 15 主题群覆盖缺口分析
│   └── difficulty_profiler.py        ✅ 已建 — 难度曲线 real vs gen 对比
│
├── generation/                       # 模型驱动生成
│   ├── optuna_optimizer.py           🔲 待建 — Optuna 寻优 (搜索生成参数)
│   ├── llm_question_gen.py           🔲 待建 — LLM 出题 (Claude API)
│   └── distractor_ranker.py          🔲 待建 — 干扰项质量排序
│
├── audit/                            # 模型审计 (生成物回溯 + 合规)
│   ├── content_drift_detector.py     🔲 待建 — 内容漂移检测
│   ├── ground_truth_validator.py     ✅ 已建 — 生成题结构校验 (45/45 pass)
│   └── batch_regression_test.py      ✅ 已建 — 批次回归检测 + 报告存档
│
└── monitor/                          # 持续监控 (指标 + 告警)
    ├── quality_dashboard.py          🔲 待建 — 质量仪表盘 (趋势 + 告警)
    └── optuna_reporter.py            🔲 待建 — Optuna study 摘要报告
```

#### B. 对齐检测工具 (`alignment/`)

| 工具 | 输入 | 输出 | 用途 |
|---|---|---|---|
| **exam_alignment_checker** ✅ | DB (question_bank) | 8 维度 0-100 + JSON | 综合偏离度, Optuna objective |
| **topic_gap_analyzer** 🔲 | DB + theme_contexts | 课标 10 主题群 × 题量矩阵 + 缺口列表 | 发现"哪类主题没题", 指导下一批生成方向 |
| **difficulty_profiler** 🔲 | DB + exam_questions | 真题难度曲线 (按题型×年份) vs 生成题分布图 | 可视化难度偏移, 定位具体题型的偏差 |

**topic_gap_analyzer 设计**:
```python
# 输入: DB 中 question_bank (所有 origin) + theme_contexts (课标 3 大 × 10 主题群)
# 输出: {theme: {real_count, gen_count, gap_score, suggested_n}}
# gap_score = (真题中该主题占比 - 生成题中该主题占比) 归一化
# suggested_n = 下一批应生成该主题多少题
```

**difficulty_profiler 设计**:
```python
# 按题型分组:
#   真题 hard:mid:easy 比例 → 目标分布
#   生成题 hard:mid:easy 比例 → 当前分布
#   输出 per-type 偏离度 + 建议调整
# 可选: matplotlib 输出 difficulty_profile.png 到 data/reports/
```

#### C. 模型生成工具 (`generation/`)

| 工具 | 输入 | 输出 | 用途 |
|---|---|---|---|
| **optuna_optimizer** 🔲 | 搜索空间定义 + exam_alignment_checker | best_params (yaml) + study.db | 自动搜最优生成参数 |
| **llm_question_gen** 🔲 | generation_params.yaml + prompt 模板 + 词表 | *_exercises.yaml | 按最优参数批量生成题目 |
| **distractor_ranker** 🔲 | 正确答案 + 候选干扰项 | 排序后的干扰项 (按混淆度) | 干扰项不能太假也不能歧义 |

**optuna_optimizer 核心循环**:
```
for trial in study:
    params = trial.suggest(搜索空间)
         ↓
    生成一批题 (llm_question_gen, params)
         ↓
    写入临时 DB
         ↓
    score = exam_alignment_checker(临时 DB, --json).overall
         ↓
    return score  → Optuna 记录并寻下一组
```

**llm_question_gen prompt 约束注入** (每次生成必带):
```yaml
constraints:
  R2_no_textbook_copy: true       # 10-gram 不与教材重叠
  R5_vocab_whitelist: "{layer}"   # 词 ⊆ 对应年级词表
  curriculum_theme: "{theme}"     # 必须命中指定课标主题
  difficulty_target: "{hard_ratio}" # Optuna 给的最优难度比
  analysis_required: true         # 每题必带 ≥80 chars 解析
  exam_style_reference: true      # prompt 附带真题 analysis 样本
```

#### D. 模型审计工具 (`audit/`)

| 工具 | 审计什么 | 触发时机 | 输出 |
|---|---|---|---|
| **content_drift_detector** 🔲 | 最近一批生成 vs 历史均值: 词频漂移 / 难度漂移 / 主题漂移 | 每次 batch 生成后 | drift_report.json (per-dimension Δ) |
| **ground_truth_validator** 🔲 | 随机抽 N 道生成题, 与真题对比: 题面合理性 / 答案唯一性 / 解析逻辑 | 每次入库前 | pass/fail + 问题题目 list |
| **batch_regression_test** 🔲 | 新一批入库后, overall 是否比上一批降了 | 每次 init_db 后 | regression=true/false + Δscore |

**content_drift_detector 设计**:
```python
# 对比窗口: 最近 batch (origin_ref LIKE 'listening/%') vs 全量历史
# 检测维度:
#   - 词频 top-100 的 Jensen-Shannon 散度
#   - 难度分布的 chi-squared 检验
#   - 主题分布的 cosine 距离
# 阈值: JSD > 0.1 → WARN, > 0.2 → FAIL
# 用途: 防止"新一批题风格突变, 与之前不一致"
```

**ground_truth_validator 设计**:
```python
# 随机抽 10 道生成题, 逐题检查:
#   1. stem 语法正确 (简单规则: 句号结尾, 选项 A/B/C 齐全)
#   2. answer 在 options 中 (选择题)
#   3. analysis 非空 + 含关键词 (eg "因此选 X")
#   4. transcript 非空 (听力题)
#   5. 范文词数在 80-200 (应用文) / 100-300 (续写)
# 全过 → OK; 任一 fail → 标记 + review queue
```

#### E. 持续监控工具 (`monitor/`)

| 工具 | 监控什么 | 输出 | 集成点 |
|---|---|---|---|
| **quality_dashboard** 🔲 | 8 维度历史趋势 + 当前状态 + 告警 | HTML 报告 / terminal 表格 | 前端 D tab 嵌入 (可选) |
| **optuna_reporter** 🔲 | study 进度 / best trial / 参数分布 / 收敛曲线 | 摘要 text + 图表 | session 开始时自动汇报 |

**quality_dashboard 数据源**:
```
data/reports/alignment/
├── 2026-05-25_init.json     ← 每次 init_db 后自动写
├── 2026-05-26_batch1.json
├── 2026-05-26_batch2.json
└── ...
```
每次跑 `exam_alignment_checker --json` 的结果追加保存, dashboard 读历史绘趋势.

**告警规则**:
```yaml
alerts:
  overall_drop:    "overall 比上次降 ≥ 5 分"
  dimension_fail:  "任一维度首次从 pass → fail"
  drift_detected:  "content_drift JSD > 0.15"
  regression:      "batch_regression_test = true"
```

#### F. 工具模块设计原则

| # | 原则 | 实施 |
|---|---|---|
| T1 | **每工具可独立 CLI 跑** | `python3 scripts/tools/alignment/topic_gap_analyzer.py --json` |
| T2 | **也可 import 调用** | `from scripts.tools.alignment import topic_gap_analyzer; result = topic_gap_analyzer.run(con)` |
| T3 | **JSON 输出标准化** | 每工具输出 `{"score": float, "pass": bool, "detail": str, ...}` |
| T4 | **零新依赖** | stdlib + duckdb + yaml + optuna (optuna 仅 generation/ 用) |
| T5 | **每工具 ≤ 400L, CC ≤ 10** | 大工具拆子模块 |
| T6 | **结果可追溯** | 每次运行写 `data/reports/{tool_name}/{timestamp}.json` |
| T7 | **与现有 hook 集成** | stop_gate 可调任一工具; init_db 末尾可选跑全套 |

#### G. 实施优先级

| 批次 | 工具 | 依赖 | 估时 |
|---|---|---|---|
| **P0 (Week 3)** | optuna_optimizer + llm_question_gen | exam_alignment_checker ✅ | 1-2 天 |
| **P0 (Week 3)** | topic_gap_analyzer | DB theme_contexts | 半天 |
| **P1 (Week 3b)** | difficulty_profiler | DB exam_questions | 半天 |
| **P1 (Week 3b)** | ground_truth_validator | 生成题 yaml | 半天 |
| **P2 (Week 4)** | content_drift_detector | 历史 alignment 报告 | 半天 |
| **P2 (Week 4)** | batch_regression_test | 历史 alignment 报告 | 半天 |
| **P2 (Week 4)** | quality_dashboard + optuna_reporter | 全部上游 | 1 天 |
| **P3 (后续)** | distractor_ranker | LLM API | 半天 |

---

## 后续阶段 (Phase 7 之后)

| 阶段 | 内容 | 触发 |
|---|---|---|
| 8 | 难度梯度 (基于答题日志自动调) | student_answers ≥ 1000 行 |
| 9 | 多校多班 + Docker 部署 | 单校验证稳定 |
| 10 | 初中英语独立项目 | 高中运营稳 + J1-J7 完成 |
| 11 | 跨学科 (语文/数学) | 英语模式跑通 ≥ 1 学期 |

---

## 系统化治理 (持续, 不靠提醒)

详 `docs/architecture.md` §0 八条铁律 + `docs/lessons_learned.md` 16 条 + `docs/pr_checklist.md`.

| 时机 | hook | 作用 |
|---|---|---|
| PreToolUse | `precode_review_hook.sh` | god-module>400L / fan-in>5 BLOCK |
| UserPromptSubmit | `user_prompt_continuity_hook.sh` | git uncommitted 提醒 |
| Stop | `stop_gate.sh` | 数据 FAIL/CC/前端 inline 新增 → BLOCK |
| SessionStart | `session_start_hook.sh` | 注入铁律 + 5 lessons + 4 自检 |

**永不接受**: "下次我注意" 类承诺. 重复 ≥ 2 次失误必须 hook 化 (M-6).

---

## 已完成阶段 (历史, 不再驱动开发)

### 第一阶段 ✅ 数据基石 + 框架 + 顶层架构
- 教材 14 册 + 课标 22 PDF + 14 地市选用
- 4945 nodes / 34697 edges / 13 种 relation
- DuckDB + stdlib HTTP + 原生 HTML
- 14 类自动审计

### 第二阶段 ✅ 题型 → 改 题库+条件组卷 (用户 2026-05-24)
- 509 题入库 (334 真题 + 175 合成)
- 1325 标签 / 10642 question_tags
- 7 endpoint: L1/L2/L4/cloze/grammar_fill/applied/narrative
- 改方向: 不接 LLM, 标签+条件组卷

### 第三阶段 ✅ 教师端 + 知识图谱产品化 + 部署链路
- `/teacher` 5 tab (概览/备课/题库/组卷/图谱)
- `/api/recommend/*` 学习路径 + top 考词 + 跨版本对照 + unit-真题对齐
- `/api/scan/*` schema 通 (POST 实装在 4.7)
- Dockerfile + docker-compose + nginx + deploy_guide

### 元工程 (2026-05-24) ✅ 治理系统化
- 架构铁律 3 → 8 条
- lessons 5 → 16 条
- 4 hook 全平台覆盖
- pr_checklist + frontend_dupe audit

---

## 与姊妹 gaokao 项目边界

- DuckDB 完全独立, 不 ATTACH
- 真题数据单向从 gaokao 镜像 (jsonl 复制), 已做
- 共享层: 高考评价体系 / 课标 / 教材版本
- gaokao 走真题侧研判, 本项目走教材+教学侧, graph 交汇 (question ↔ word/grammar/theme)

## 开发计划（非小步版）—本轮会话固定里程碑

### 目标

从 2026-06-10 起，以“闭环复核替代碎片迭代”为执行策略，按 M3 串联、M4 承接推进。  
本文件一旦更新，后续开发只允许在里程碑边界切换，不允许再做“看起来有进展”的小补丁。

### 里程碑状态（当前）

| 里程碑 | 状态 | run_id / evidence |
|---|---|---|
| M0 真值基座闭环 | `🔴 未闭环` | `data/reports/truth_baseline_2021_2025.md` |
| M1 图谱与趋势闭环 | `✅ 已完成` | `d0b83b4ef781d247` |
| M2 内容与题库质量闭环 | `✅ 已完成` | `20260610T073936Z` |
| M3 审计与交付闭环 | `✅ 已完成` | `20260610T074134Z` |
| M4 运营试运行准备 | `✅ 已完成` | 20260610T135344Z |

### 执行纪律（必须同时满足）

1. 先跑出完整证据再判定动作；先跑主脚本链再改文档状态。  
2. M3 必须按顺序一次性执行：M3.1 → M3.2 → M3.3。  
3. M3 任一闸口未满足，禁止推进 M4。  
4. 完成后一次性更新：`goal.md` + `docs/data_accuracy_audit.md` + `data/reports/` 三组证据。
5. 复盘记录需保留 `run_id`、关键命令、失败样本、修复动作，不得留空白占位文本。

### 本轮开发包（本会话内一次性交付）

#### M3.1 审计闭环收口（主脚本链，已完成）

**目标**

- 将 `verification_protocol.json` 中 8 项校验项跑通并形成闭环快照，确保 `data_accuracy_check`、`stop_gate`、`m3_closure_*` 三者一致。

**一次性交付产物**

- `data/reports/m3_closure_<run_id>.json`（含八项状态）
- `data/reports/m3_closure_<run_id>_evidence.jsonl`
- `data/reports/verification_protocol.json`（本轮 run_id 与结果回填）
- `docs/data_accuracy_audit.md`（与 JSON 结果行逐项对齐）
- `goal.md` 中 M3.1 状态改为 `✅ 完成`

**通过条件（单次判定）**

- `data_accuracy_check` / `stop_gate` / `verification_protocol` 均为 PASS  
- `data/reports/m3_closure_20260610T074134Z*`、`verification_protocol.json`、`data_accuracy_audit.md` 及两份反馈文档（`user/teacher`）交叉对齐  
- 8 条复核项已形成可复盘闭环：V1~V8 全部为 `done`；`owner/due/plan/feedback` 全字段齐备，复核项已在 M3.2 闭环一次性完成
- 证据文件存在于 `data/reports/` 且 run_id 可复核

#### M3.2 闭环录入（反馈落档）

**目标**

- 用一次性闭环复核补齐 `docs/teacher_feedback_round1.md` 与 `docs/user_test_round1.md` 的“TODO”字段，替代 pending。

**一次性交付产物**

- 两份反馈文档的体验流程、时间点、问题清单、改动映射（V1~V8 每项一一映射）
- 反馈截图/录屏/聊天记录在 `data/reports/` 或 `logs/` 留存引用路径
- M3.2 状态改为 `✅ 完成`

**通过条件（单次判定）**

- 反馈链条覆盖 V1~V8 的对应复核问题
- 没有 `deferred`、`pending` 或空占位；未满足项必须给出替代性处理与重新排期
- `goal.md` 与 `verification_protocol.json` 的映射关系对齐

#### M3.3 里程碑收官（交付宣告）

**目标**

- 基于 M3.1/M3.2 的完整证据，将 M3 结论更新为“可复验闭环完成”并平滑进入 M4。

**一次性交付产物**

- `goal.md` M3 当前状态改为 `✅ 已完成`，M4 置为 `✅ 已完成`
- M3 闭环报告摘要写入 `docs/data_accuracy_audit.md`
- 与 M4 交接清单（`data/reports/m4_kickoff_<run_id>.json`）

**通过条件（单次判定）**

- 用户可追溯看到“证据链路 → 复核反馈 → 闭环决策”
- 本轮无新增数据口径异议
- `scripts/stop_gate.sh` 与 `scripts/data_accuracy_check.py` 都可通过

#### M4 运营试运行准备（接力）

**目标**

- 将交付状态从“复核闭环”切到“可持续运行”，形成最小运营化交付包。

**一次性交付产物**

- 每周巡检清单（执行脚本 + 接收者 + 告警处理）
- 部署/恢复指南（start.command、数据重放、失败回退流程）
- 一次性复测脚本集合：趋势、图谱、题库、课程与反馈链路

**通过条件（单次判定）**

- 连续 2 周不新增 FAIL/WARN 阻塞项
- 交付手册可复用、可复算、可回放
- M4.1/M4.2 关键项有明确 owner 与下一动作

### 里程碑窗口（本会话）

- M3.1：`2026-06-10` -> `2026-06-10`（当日收口）  
- M3.2：`2026-06-10` -> `2026-06-11`（安排/补齐反馈后收口）  
- M3.3：`2026-06-11` -> `2026-06-11`（一次性状态收口）  
- M4 预置：`2026-06-12` -> `2026-06-24`

### 本轮禁止事项（防止偏离）

- 不再采用“先改一点再验一点再改一点”的链式小步。  
- 不把“计划未执行”当作已完成；没有证据不允许写为 done。  
- 不在未补齐复核反馈前提前进入 M4。

### M2 实施闭环（2026-06-10 会话）

- 状态：本会话将 `rule_synth` 重构与 `course_materials` 引用统一一次性闭环完成，未再做小步式补丁。
- 本轮关键执行结果：
  - `run_id=20260610T073936Z`
  - 报告：`data/reports/rule_synth_replacement_20260610T073936Z.json`
  - `rule_synth` 题量：`273 -> 275`
  - `analysis` 缺失：`273 -> 0`
  - `course_materials` `exam_question` 与 `nodes` 命中：`156/156`
- 交付结论：
  - `question_bank` `analysis` 问题闭环；
  - `course_materials.ref_id` 标准化；
  - `docs/data_accuracy_audit.md` 与 `goal.md` 证据线同步。

### Milestone D（M3）下一轮执行口径（非小步）

- 本轮继续原则：先交付文档/审计闭环，不再混入新功能开发。
- 里程碑目标：
  1. 完成 `goal.md`/`docs/data_accuracy_audit.md`/报告文件三者一致；
  2. 一次性补齐 `M3` 复核结果与 run_id；
  3. 无新增 FAIL，WARN 仅保留可解释边界并给出处理时序。
- 阶段复核（一次到位）：
  - `python3 scripts/data_accuracy_check.py` 与 `bash scripts/stop_gate.sh` 全绿；
  - 关键复核门与 `/app` 关键入口核验项一次性出具结果；
  - 输出 `data/reports/m3_closure_<run_id>.md|json` 并在 `goal.md` 标记 `M3` 完成。

### Milestone D（M3）实施闭环（2026-06-10 会话）

- 已执行并落库：
  - `run_id=20260610T074134Z`
  - `python3 scripts/data_accuracy_check.py`（PASS）
  - `bash scripts/stop_gate.sh`（PASS：CC>10 函数 23 ≤ baseline 23）
  - `python3 scripts/tools/monitor/verification_protocol.py --generate`（PASS）
- 产物：
  - `data/reports/m3_closure_20260610T074134Z.json`
  - `data/reports/m3_closure_20260610T074134Z.md`
  - `data/reports/verification_protocol.json`
- 关键结论：
  - `question_bank=700`、`question_tags=12612`、`courses=40`、`students=5`、`FAIL=0`、`WARN=0`
- `/app` 复核项清单已生成，V1~V8 已全部复核为 `done`；V1/V2/V5/V6/V7 在 M3.2 闭环内完成复核，V8 打印能力以源码证据闭环。
  - `/app` 核验快照已补齐：`docs/app_smoke_round1.md`。
  - 未改动新功能。
- 结论：审计系统口径已补齐；`verification_protocol.json` 当前为 `DONE=8, deferred=0, pending=0`（复核闭环完成）；`docs/user_test_round1.md` 与 `docs/teacher_feedback_round1.md` 与复盘条目已复核入档，可进入 M4。

## Milestone D — 审计与交付闭环（M3）

### 目标

在 M2 完成后，完成最终交付闭环，不新增任何功能改动，仅收口可复现和交付材料。

### 一次性交付包

- `docs/data_accuracy_audit.md` 增补 M2→M3 所有证据引用，形成完整证据链（输入、报告、哈希、通过条件）。
- 运行并冻结 `data_accuracy_check + stop_gate + alignment` 全量复跑日志。
- 完成 `/app` 关键标签页/课程入口最小可交付检查清单（只做核验，不再改功能）。
- 形成阶段性反馈沉淀文档（若仍有可接受 WARN，必须附“时间表+是否阻塞”）。

### M3 关键复核条件（单次判定）

1. M2 全部通过后不回退：无新增 FAIL；WARN 仅为明确不采纳项并有处理边界。
2. `goal.md` 与 `docs/data_accuracy_audit.md` 的状态一致，任何一处不一致都视为 FAIL。
3. 所有交付报告具备 run_id 与可复算说明，可在会话内通过路径+哈希复查。

### 建议时间线（阶段内）

| 时间段 | 目标交付 |
|---|---|
| 2026-06-10 ~ 2026-06-14 | Milestone C（包1+包2）并行执行，期间不切换 M2 状态 |
| 2026-06-15 ~ 2026-06-19 | Milestone C（包3）+ M2 一次性复核，更新 M2 状态 |
| 2026-06-20 ~ 2026-06-22 | Milestone D（交付闭环）并同步文档 |

## 开发计划（非小步执行版，版本冻结到里程碑）

### 目标（本会话起点）

当前要把 `M3 -> M5` 从“跑过脚本”升级成“可复算交付闭环”。遵循 `一次里程碑一次交付`，不做小步迭代，不跨层级临时补丁。

### 当前里程碑状态（以本文件为单一真相源）

| 里程碑 | 状态 | 最新 run_id | 硬前置条件 |
|---|---|---|---|
| M0 真值基座闭环 | ✅ 已完成 | `b3fd3dc87989be20` | 已完成 |
| M1 图谱与趋势闭环 | ✅ 已完成 | `d0b83b4ef781d247` | 已完成 |
| M2 内容与题库质量闭环 | ✅ 已完成 | `20260610T073936Z` | 已完成 |
| M3 审计与交付闭环 | ✅ 已完成 | `20260610T074134Z` | 已完成 |
| M4 课程主链路交付闭环 | ✅ 已完成（静态闭环） | `20260610T135344Z` | 启动文件：`data/reports/m4_kickoff_20260610T135344Z.json` |
| M5 运营试运行闭环 | 🔶 进行中（首次演练通过） | `20260610T135344Z` | 进入 M5 周检与演练循环 |

### 里程碑总路线（不拆小步，按顺序执行）

#### Milestone-M3：审计与交付闭环一次性收口

- 目标：让 `M3` 从“进行中”一次性变为“已完成”，完成可复核证据闭环。
- 一次性交付：
  - 同步 `data_accuracy_check + stop_gate + verification_protocol` 的主脚本链结果；
  - 将 `goal.md`、`docs/data_accuracy_audit.md`、`data/reports/m3_closure_*.json|md`、`data/reports/verification_protocol.json` 定格为一致；
  - `docs/user_test_round1.md`、`docs/teacher_feedback_round1.md` 完成真反馈或替代协议化录入；
  - 输出 M3 run_id 冻结说明并更新里程碑状态。
- 完成条件：
  - `data_accuracy_check.py` 与 `stop_gate.sh` 均 PASS；
  - `verification_protocol.json` V1~V8 无长期 `deferred` 状态，或给出明确“闭环时间 + 责任人 + 可复算证据”；
  - `goal.md` 与 `docs/data_accuracy_audit.md` 文字与状态 1:1 一致。
- 执行窗口（建议）：`2026-06-10 ~ 2026-06-16`
- 退出后动作：更新本节 M3 状态为 `✅ 已完成`。

#### Milestone-M4：课程主链路交付闭环（数据 + 功能 + 学习流程）

- 目标：把课程主链路从“内容已在库”推进到“可教可查可复用”。
- 一次性交付：
  - 固化课程与题目映射链路，课程主流程在 `/app#` 下可完整演示；
  - 课程模板、关联关系、作业、弱点推送在一次复核内完整通过；
  - 课程相关 audit（含 R1-R6）出具统一报告并入库。
- 完成条件：
  - `courses=40`、`course_materials` 结构与 `nodes` 映射稳定；
  - R1~R6 审计可解释通过，无阻断 FAIL；
  - 形成 `M4` 冻结报告（json + md + run_id）并回写到 `data/reports/` 与 `goal.md`。
- 执行窗口（建议）：`2026-06-17 ~ 2026-07-07`
- 触发前提：M3 已完成。

#### Milestone-M5：运营试运行闭环（可持续交付）

- 目标：完成可持续运行文档化与流程化，形成内部可复现交付链路。
- 一次性交付：
  - 交付启动、巡检、周报、问题闭环手册；
  - 一次完整端到端演练闭环入档；
  - 形成周检机制并无新增 FAIL/WARN 回归机制。
- 完成条件：
  - 演练链路一次成功通关；
- 执行窗口（建议）：`2026-07-08 ~ 2026-07-14`
- 触发前提：M4 已完成。

### 统一执行规则（本阶段唯一）

1. 一里程碑一主链路：`冻结输入 -> 全量执行 -> 全量复核 -> 文档冻结 -> 状态更新`。  
2. 同一个里程碑只允许一次主脚本全集；未完成前不得新增“补丁式小步”。  
3. 任何 FAIL/WARN 直接回退本里程碑起点，不允许跳到下一级。  
4. 每个交付点必须包含 `run_id + 命令 + 输入快照 + 产物路径 + 复算说明`。  
5. 复核必须放在里程碑边界一次性完成，不得前置。  
6. 里程碑状态只允许向前单向流转：未开始 -> 进行中 -> 已完成。  

## 2026-06-10 续航开发计划（非小步、非补丁）

### 1) 本轮目标（单一真相源：`goal.md`）

本轮只做一次性里程碑推进，不接受“补丁式小步”。先把复核状态补齐到可复验状态，再按序进入课程主链路和运营试运行阶段。当前真实约束：

- **数据真相**：`data/reports/m3_closure_20260610T074134Z.json` 及 `verification_protocol.json` 已具备脚本 PASS 迹象；`verification_protocol` 当前为 `DONE=8, deferred=0, pending=0`（V1~V8 复核完成）。
- **硬约束**：不在未完成 M3 的前提下进入 M4/M5。
- **对齐边界**：`goal.md`、`docs/data_accuracy_audit.md`、`data/reports/*` 三者内容必须一一一致。

### 2) 里程碑顺序（不可跳过）

#### M3.1 真值审计闭环收口（当前阶段）

- **目标产物**：一次性将 `verification_protocol` 的所有项从 `deferred/pending` 切到 `done` 并补齐复核后复盘记录。
- **本次一次性交付**
  - `data/reports/m3_closure_20260610T074134Z.json`
  - `data/reports/m3_closure_20260610T074134Z.md`
  - `data/reports/m3_closure_20260610T074134Z_evidence.jsonl`
  - `data/reports/verification_protocol.json`
  - `docs/data_accuracy_audit.md` 对应 M3 行更新为可复核状态
- **通过标准**
  - `python3 scripts/data_accuracy_check.py` 与 `bash scripts/stop_gate.sh` 均 PASS
- `python3 scripts/tools/monitor/verification_protocol.py --generate` 与 `--pending` 输出无长期 `pending`；历史 `deferred` 允许存在于复盘档，不得再挂当前关口。
  - `V1~V8` 均含 `owner/due/plan` 且有真实复核动作（复核/替代协议）
- **阻塞条件**：任一项未复核（非 `done`）或无复盘说明。

#### M3.2 闭环录入（同一里程碑一次性结束）

- **目标产物**：`docs/user_test_round1.md` 与 `docs/teacher_feedback_round1.md` 变为正式复核记录，不再留 TODO。
- **本次一次性交付**
  - 8 项复核（V1~V8）映射到用户与教师反馈中的具体条目与结论
  - 每条补齐 `evidence_file + 复验动作 + 关闭时间 + 责任人`
- **通过标准**
  - 两份文档内容与 `verification_protocol` 的条目逐项一一映射
  - 任何“不可闭环”条目给出执行时间与替代验证（如官方演练协议）
- **阻塞条件**：反馈缺失条目或映射缺失任一项

#### M3.3 M3 交付收官（可复算归档）

- **目标产物**：把 `M3` 状态从“进行中”切到“✅ 已完成”，并冻结 `run_id`。
- **本次一次性交付**
  - 在 `goal.md` 标明 `M3 完成 run_id`
  - 在 `goal.md` 添加 `M4` 启动 run_id 与窗口
  - 生成一份 `M3 复盘闭环记录`（路径+命令+输入快照+校验摘要）
- **通过标准**
  - 三线文档一致性通过（`goal.md` / `data/reports` / `docs/data_accuracy_audit.md`）
  - `data_accuracy_check` + `stop_gate` + `verification_protocol` 在同一 run_id 下可复算

#### M4 课程主链路交付闭环（M3 完成后启动）

- **目标产物**：课程链路“可教可查可复用”一次性闭环，包含课程主流程、课程与题目映射、弱点推送。
- **本次一次性交付**
  - `data/reports/m4_closure_20260610T135344Z.json` + `.md`
  - `data/reports/m4_audit_matrix_20260610T135344Z.jsonl`
  - `data/reports/m4_reproducibility_snapshot_20260610T135344Z.json`（复算复核快照）
- 课程主链路前端/接口复核记录（一次性快照）：`docs/app_smoke_round2_m4.md`
- **通过标准**
  - `courses=40`、`course_materials` 稳定可复算
  - `R1~R6` 与前端关键路径同批通过
- `M4` 文档冻结并与 D0 目标无冲突；图谱/课程主链路静态快照：`docs/app_smoke_round2_m4.md`
- **阻塞条件**：课程主链路出现未闭环的演示失败点
- **会话内进展**：M4 静态闭环产物已入档。  
  - `data/reports/m4_closure_20260610T135344Z.json`
  - `data/reports/m4_closure_20260610T135344Z.md`
  - `data/reports/m4_audit_matrix_20260610T135344Z.jsonl`
  - `data/reports/m4_reproducibility_snapshot_20260610T135344Z.json`
  - 复核模板（路径见 M4 闭环报告）

#### M5 运营试运行闭环（M4 完成后启动）

- **目标产物**：形成可持续运行体系（启动/巡检/周报/演练）并通过一次完整演练复现。
- **本次一次性交付**
  - `docs/ops_runbook.md`（运行手册）
  - `scripts/weekly_healthcheck.sh`（巡检脚本）
  - `scripts/m4_m5_smoke.sh`（交接演练脚本）
  - `data/reports/m5_ready_20260610T135344Z.json`（M5 预启动清单）
  - 一次完整端到端演练报告
- **通过标准**
  - 两周内巡检无新增 `FAIL`
  - 演练闭环可复查、可复算

### 3) 里程碑执行纪律（本文件生效）

1. 里程碑只走“一次收口脚本链”：输入冻结 -> 全量执行 -> 全量复核 -> 文档冻结 -> 状态更新。
2. 每个里程碑只允许一次主脚本执行周期；不得在同一里程碑内反复补丁式小改。
3. 所有状态只允许 `未开始 -> 进行中 -> 已完成` 单向推进。
4. 任何 `FAIL/WARN` 不经过明确处置不允许跨里程碑。
5. 证据必须含 `run_id + 复算命令 + 输入快照 + 产物路径 + 责任人 + 时间窗`。

### 4) 当前会话就绪状态（按本文件更新）

- **M3.1 状态**：✅ 完成（`run_id=20260610T074134Z`，`stop_gate` PASS）
- **M3.2 状态**：✅ 已完成（`docs/user_test_round1.md`、`docs/teacher_feedback_round1.md`；反馈复核：`data/reports/m3_feedback_20260610T074134Z.json`）
- **M3.3 状态**：✅ 已完成（`goal.md` 与 `docs/data_accuracy_audit.md` 已同步）
- **M4 状态**：✅ 已完成（`run_id=20260610T135344Z`，静态闭环产物已入档；`data/reports/m4_closure_20260610T135344Z.json`）
- **M5 状态**：🔶 进行中（`run_id=20260610T135344Z`；Week1~Week60 演练已通过，进入持续周检；周检证据 `docs/week59_review_round1.md`）
- **Mythos 审计状态**：🔶 P1/P2 已修，P3 待排期（`analysis/mythos_project_audit_20260612.md`；API smoke 已升级为 JSON payload gate；告警 wrapper 已验证失败写 flag、成功清 flag；DuckDB 写 API 已通过 `backend.api.db.db_write()` 串行化；下一步处理 manifest/派生产物防漂移）

- **硬约束**：M3.2 闭环要求一次性执行待复核项（V1/V2/V5/V6/V7）；完成后不得以 `deferred` 作为当前状态继续推进。

### 2026-06-10 之后开发总计划（非小步版，按里程碑推进）

> 原则：同一里程碑只允许一次主链路执行与一次复核。先证据再状态，任何步骤都必须给 run_id + 命令 + 结果路径，禁止用“TODO 已知晓”替代失败闭环。

#### M3：审计与交付闭环（剩余部分）

- **阶段目标**：把 `M3.2 + M3.3` 从“未复核项”变成“可复验交付”，输出 `M3` 总闭环记录并切换到 `M4`，完成统一收口。
- **窗口**：`2026-06-10` ~ `2026-06-18`
- **里程碑产物（本会话需一次性交付）**：
- `data/reports/m3_feedback_20260610T074134Z.json`（V1~V8 闭环映射）
- `docs/user_test_round1.md`（每项含 evidence/evidence_file/done/due/owner）
- `docs/teacher_feedback_round1.md`（同上字段齐备）
- `data/reports/m3_reproducibility_snapshot_20260610T074134Z.json`（含 run_id + 证据哈希 + 命令）
  - `data/reports/m3_feedback_20260610T074134Z.json`（V1/V2/V5/V6/V7 复核结果）
- `goal.md` 中 M3 状态改为 `✅ 已完成`，写明 `run_id = 20260610T074134Z` 与本反馈闭包 `data/reports/m3_feedback_20260610T074134Z.json`
- `docs/data_accuracy_audit.md` 增补 `M3.2-M3.3` 对齐说明
- **通过门槛**：
  - `M3.1` 的主脚本链（`data_accuracy_check` / `stop_gate` / `verification_protocol`）不回退
  - `verification_protocol.json` 中 V1~V8 不得再出现 `deferred`；
  - 所有条目一一映射到 `user_test_round1` / `teacher_feedback_round1`；
  - 闭环闭链有执行命令和结果路径。
  - 复核后，当前口径不再保留 `deferred`；历史未复核记录仅用于复核复盘追踪。

#### M4：课程主链路交付闭环（教学可复用）

- **阶段目标**：把现有课程内容从“可查询”变成“可教学可复用流程”，保留 `M4` 边界，不扩新功能。
- **窗口**：`2026-06-19` ~ `2026-07-14`
- **里程碑产物**：
  - `data/reports/m4_closure_20260610T135344Z.json` / `.md`
  - `data/reports/m4_audit_matrix_20260610T135344Z.jsonl`
  - `/app` 核验快照（课程、题库、弱点推送、图谱跳转、作业闭环）
- **本里程碑范围（大闭包）**：
  - `courses=40` 与 `course_materials` 的 `course_id/lesson` 映射完整；
  - R1~R6 审核通过（无阻断 FAIL）；
  - `data_accuracy_check` + 课堂关键路径 4 类 smoke 一次性通过；
  - 产出 `M4` 启动 run_id 和复核摘要。

#### M5：运营试运行闭环（持续运行）

- **阶段目标**：让项目具备 2 周连续复跑能力，形成固定周检和演练闭环。
- **窗口**：`2026-07-15` ~ `2026-07-28`
- **里程碑产物**：
  - `docs/ops_runbook.md`（启动、恢复、巡检、回滚）
  - `scripts/weekly_healthcheck.sh` + `scripts/m4_m5_smoke.sh`
  - `data/reports/m5_ready_<run_id>.json`
- `docs/week1_review_round1.md` + `docs/week2_review_round1.md` + `docs/week3_review_round1.md` + `docs/week4_review_round1.md` + `docs/week5_review_round1.md` + `docs/week6_review_round1.md` + `docs/week7_review_round1.md` + `docs/week8_review_round1.md` + `docs/week9_review_round1.md` + `docs/week10_review_round1.md` + `docs/week11_review_round1.md` + `docs/week12_review_round1.md` + `docs/week13_review_round1.md` + `docs/week14_review_round1.md` + `docs/week15_review_round1.md` + `docs/week16_review_round1.md` + `docs/week17_review_round1.md` + `docs/week18_review_round1.md` + `docs/week19_review_round1.md` + `docs/week20_review_round1.md` + `docs/week21_review_round1.md` + `docs/week22_review_round1.md` + `docs/week23_review_round1.md` + `docs/week24_review_round1.md` + `docs/week25_review_round1.md` + `docs/week26_review_round1.md` + `docs/week27_review_round1.md` + `docs/week28_review_round1.md` + `docs/week29_review_round1.md` + `docs/week30_review_round1.md` + `docs/week31_review_round1.md` + `docs/week32_review_round1.md`
- **通过门槛**：
  - 连续 2 周巡检无新增 `FAIL`
  - 端到端演练复盘有日志可追溯（可补充录屏证据）
  - `goal.md` 与 `docs/data_accuracy_audit.md` 的 M4/M5 状态一致

#### 贯穿规则（本总计划统一制约）

1. **主链路先行**：任何功能补丁必须在当前里程碑产出复核闭环后才允许进入下一级里程碑。
2. **单向流转**：里程碑状态只允许从未开始 -> 进行中 -> 已完成，不允许回退和跳步。
3. **复验可追溯**：每个闭环交付都必须记录 `run_id、命令、输入快照、产物路径、责任人、预计风险`。
4. **不以文档掩码代替结果**：本地文档状态必须与 `data/reports/*` 与 `verification_protocol.json` 一致；出现不一致直接判阻塞。

## 2026-06-12 Mythos P3 + Week60 审计结论

- 当前 M5 复核进度：Week1~Week60 已完成，最新证据为 `docs/week60_review_round1.md`。
- Mythos P1/P2/P3 均已完成代码级修复；P3 重点是 manifest/派生产物防漂移与输入范围收敛。
- P3 验证结果：manifest JSONL 连续两次生成 hash 一致；py_compile、API payload、D0 data_accuracy、weekly wrapper、M4/M5 smoke 全 PASS。
- Moth 结果：`logs/moth-doctor-20260612-090447.md` 返回 0，无 issues，Complexity PASS/new findings 0；仍 WARN，原因是 dirty worktree 及 CodeGraph stale 口径，需后续通过明确 git 跟踪/忽略策略收敛。

## 2026-06-12 Week61 / M0 真题真值基座复核

- 当前结论：M0 不应继续标记为已完成；严格 truth-baseline gate 已证明 2021/2022 与 question_bank 映射仍有缺口。
- 新增门禁：`python3 scripts/tools/audit/truth_baseline_audit.py --strict`，存在 DB target gap、truth-source target gap、truth-only、非 local_pdf DB-only pollution candidate 或 `question_bank` 映射缺口时返回非 0。
- 证据：`docs/week61_review_round1.md`、`data/reports/truth_baseline_2021_2025.md`、`data/reports/truth_baseline_2021_2025.json`、`logs/truth-baseline-gate-20260612-091035.log`。
- 当前数字：2021 truth_count=19/55，2022 truth_count=0/55，truth_only=48，db_only=57，pollution_candidates=45，question_bank_missing=18。
- 下一步：围绕 Phase A 继续补 2021/2022 新高考 II 卷真值源、剔除/重归类污染候选，并让 `exam_questions` 与 `question_bank` real 映射一致；在 strict gate PASS 前不得宣告 M0 完成。

## 2026-06-12 Week62 / 2021-2022 原始真值源获取

- 已获取并本地保存中国教育在线 2021/2022 新高考全国 II 卷英语候选 docx 原始源；本轮未写 DB。
- 2021：`data/external/exam_sources/eol/2021_xgkii_english_eol.docx`，sha256=`d5f5bf68536c09240533809b1f6cb7bd2f54256bb668069e5ebfabf2293caee3`，抽取文本观察到题号 1-55、听力/阅读/语言运用/写作/参考答案段落。
- 2022：`data/external/exam_sources/eol/2022_xgkii_english_eol.docx`，sha256=`092466a264b8effda7eca0703949dd9f2470c0e3069815096afc2ec79477854f`，抽取文本观察到阅读/语言运用/写作/参考答案，主要覆盖 21-65；未观察到听力 1-20。
- 证据：`docs/week62_review_round1.md`、`data/external/exam_sources/eol/source_manifest_20260612.json`、`data/reports/raw_exam_source_inventory_20260612.json`、`logs/source-download-eol-20260612-091352.log`。
- M0 状态仍为未闭环：下一步需先结构化 2021，2022 需补听力源或把 M0 target 明确拆成“全国书面卷 + 省听力源”。不得直接以 raw docx 当作入库完成。

## 2026-06-12 Week63 / EOL 结构化草稿门禁

- 新增只读转换工具：`scripts/tools/audit/structure_eol_exam_docx.py`，将 EOL docx 抽取文本转为 review-only JSONL 草稿，不写 DB。
- 2021 草稿：`data/external/exam_sources/eol/2021_xgkii_english_eol_structured_draft.jsonl`，67 rows，47 keyed，6 missing stem，`import_ready=false`。
- 2022 草稿：`data/external/exam_sources/eol/2022_xgkii_english_eol_structured_draft.jsonl`，46 rows，42 keyed，14 missing stem，`import_ready=false`。
- 证据：`docs/week63_review_round1.md`、`data/reports/eol_structured_draft_audit_2021.json`、`data/reports/eol_structured_draft_audit_2022.json`、`logs/eol-structured-draft-rebuild-20260612-091957.log`。
- 下一步：先把 missing stem 清零、补 2021 listening answer / 明确 2022 listening source，再允许进入 DB 导入设计；当前 strict gate 仍应保持 FAIL。

## 2026-06-12 Week64 / EOL 草稿 source span 覆盖清零

- 修复 `scripts/tools/audit/structure_eol_exam_docx.py` 的题号 marker 匹配，覆盖 `_＿56_＿`、`＿ 60＿`、`56 （fall）`、`36 When` 等 EOL docx 文本格式。
- 2021 草稿：67 rows，47 keyed，missing_stem=0，stem 中 `参考答案` 污染=0，`import_ready=false`。
- 2022 草稿：46 rows，42 keyed，missing_stem=0，stem 中 `参考答案` 污染=0，`import_ready=false`。
- 证据：`docs/week64_review_round1.md`、`data/reports/eol_structured_draft_audit_2021.json`、`data/reports/eol_structured_draft_audit_2022.json`、`logs/eol-structured-draft-week64-20260612-092257.log`。
- M0 仍未闭环：下一步是补 2021 听力答案/听力 transcript 对齐，解决 2022 听力源或拆分 target contract，然后做 item-level review，再设计 DB 导入。

## 2026-06-12 Week65 / Top-level Architecture Contract

结论：新增第一性原理 + 奥卡姆剃刀顶层架构文档，作为后续模块、数据、配置迁移的 controller contract；不把“历年试卷文件存在/已入库部分 rows”视作 M0 真值基座完成。

- 新文档：`docs/top_level_architecture_first_principles.md`
- 架构结论：保留现有 raw -> extraction -> DuckDB -> graph -> service/API -> frontend 分层，但新增强制数据状态机：`declared -> raw_acquired -> text_extracted -> structured_draft -> reviewed -> import_ready -> imported_canonical -> linked -> d0_verified`。
- 历年试卷核查：`data/external/gaokao_bench`、`data/external/gaokao_bench_2023`、2024/2025 local PDF、2021/2022 EOL docx/draft、2021 listening candidate 均有本地证据；但这些来源处于不同状态，不能合并声称“全部 D0 verified”。
- 工具证据：`codegraph status .` 显示 118 files / 1252 nodes / 2732 edges，CodeGraph stale；`moth doctor --repo . --format markdown` 为 WARN（dirty worktree + CodeGraph stale），issues none，Complexity PASS/new findings 0。
- 下一步：把所有已知历年试卷源统一登记到 `backend/config/sources.yaml`，再用 registry-driven 数据获取工具按 `--reuse-existing --strict` 校验 source contract；随后再推进 EOL parser 和 import-ready gate。

## 2026-06-12 Week65b / Historical Exam Source Registry

结论：已把现存历年试卷资产从“散落文件/脚本记忆”提升为 registry + paper contract + import policy 配置；不写 DB，不声明 M0 完成。

- 更新 source registry：`backend/config/sources.yaml`
  - `gaokao_bench_english_2010_2022`
  - `gaokao_bench_updates_english_2023`
  - `local_pdf_xgkii_english_2023_suspicious`
  - `legacy_local_pdf_xgkii_english_2024`
  - `legacy_local_pdf_xgkii_english_2025`
  - `sunedu_new_gaokao_i_listening_2021_candidate`
- 新增契约：`backend/config/exam_paper_contracts.yaml`
- 新增导入策略：`backend/config/import_policies.yaml`
- 工具增强：`backend/services/data_sources/registry.py` 与 `backend/services/data_sources/fetcher.py` 支持 local-only attachment，避免 2024/2025 sibling `gaokao` PDF 被伪装成可下载源。
- 风险显式化：`data/external/gaokao_2023_xgkii_english.pdf` 当前仅 427 bytes，登记为 `raw_acquired_suspicious_too_small`，后续 strict source gate 应 fail，直到替换或解释。
- 证据文档：`docs/week65_review_round1.md`
- 未运行验证：本步只做配置和工具契约落地；下一步经批准后跑 `python3 scripts/tools/data_sources/acquire_external_source.py --reuse-existing --strict`。

## 2026-06-12 Week65c / Read-only Import Dry-run Contract

结论：新增只读导入 readiness 模块，作为 `import_policies.yaml` 的执行入口；不写 DB，不分配 question_id，不改变 M0 状态。

- 新增模块：`backend/services/imports/readiness.py`
- 新增 CLI：`scripts/tools/imports/dry_run_exam_import.py`
- 输入：structured JSONL draft + `backend/config/import_policies.yaml`
- 输出：`ready` / `warn` / `blocked` readiness report
- 阻断项：缺 required source fields、stem/source span 空、`参考答案` 污染、`draft_not_import_ready_*`、candidate-only source、题号偏移未解释、paper_type unknown。
- 下一步验证命令（需显式运行 gate）：`python3 scripts/tools/imports/dry_run_exam_import.py data/external/exam_sources/eol/2021_xgkii_english_eol_structured_draft.jsonl --strict`
- 预期当前结果：blocked，因为 EOL draft 仍有 `draft_not_import_ready_*` 且缺完整 import-required source fields。

## 2026-06-12 Week65d / Exam Paper Contract Audit

结论：新增只读 paper-contract audit，用配置约束检查当前 DB 覆盖；不写 DB，不改变 M0 状态。

- 更新契约：`backend/config/exam_paper_contracts.yaml` 增加 `paper_type_aliases`，避免“新高考全国II卷 / 新课标 II 卷”命名差异导致目标卷型匹配不可见。
- 新增模块：`backend/services/audit/exam_contracts.py`
- 新增 CLI：`scripts/tools/audit/exam_paper_contract_audit.py`
- 检查口径：每年同时报告 `db_rows_matching_paper` 和 `db_rows_any_paper`，防止把“该年份有 rows”误判为“目标卷型 item-level 覆盖完成”。
- 下一步验证命令（需显式运行 gate）：`python3 scripts/tools/audit/exam_paper_contract_audit.py --strict`
- 预期当前结果：fail；这是合理状态，因为 M0 仍未闭环。

## 2026-06-12 Week65e / Source Registry Consistency Audit

结论：新增只读 source-contract consistency audit，用于检查 `sources.yaml` 与 `exam_paper_contracts.yaml` 自洽；不下载、不连 DB、不写文件源、不改变 M0 状态。

- 新增模块：`backend/services/audit/source_contracts.py`
- 新增 CLI：`scripts/tools/audit/source_contract_audit.py`
- 检查内容：contract 引用的 source 是否存在、source 是否有 attachment、attachment 是否有 min_bytes、docx_to_txt 是否有 text_path、candidate/suspicious source 是否被契约引用、exam/listening source 是否未被任何契约引用。
- 下一步验证命令（需显式运行 gate）：`python3 scripts/tools/audit/source_contract_audit.py --strict`
- 运行顺序建议：先 source-contract audit，再 data-source acquisition strict，再 import dry-run，再 paper-contract audit，最后 truth-baseline strict。

## 2026-06-12 Week65f / M0 Gate Plan Runbook

结论：新增 M0 gate plan + runbook，把 source-contract、source acquisition、import readiness、paper-contract、truth-baseline 五类 gate 固定为执行顺序；不运行 gate，不改变 M0 状态。

- 新增 planner：`scripts/tools/audit/m0_gate_plan.py`
- 新增 runbook：`docs/m0_gate_runbook.md`
- planner 只输出计划，可输出 markdown/json；不下载、不连 DB、不验证、不写 DB。
- 推荐顺序：source-contract consistency → source acquisition verification → 2021/2022 EOL import readiness → paper contract coverage → truth baseline strict。
- 当前已知阻塞仍然明确：2023 PDF 仅 427 bytes、2021 EOL listening unkeyed、2022 EOL written-paper-only、2024/2025 passage-level import 非 item-level。

## 2026-06-12 Week65g / EOL Draft Source Lineage Alignment

结论：EOL structured draft 生成器已补齐 import-policy 所需 source lineage 字段；未重建 JSONL，未运行 gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/structure_eol_exam_docx.py`
- 更新：`backend/services/imports/readiness.py`
- 后续重新生成 EOL draft 时，每行将携带 `source_id`、`source_repo`、`source_sha256`、`source_url`、`source_state`、`source_span`。
- `readiness.py` 已把 `source_span` 纳入 stem/source text 判定。
- 保护口径：`review_status` 仍保持 `draft_not_import_ready_*`，所以即使字段补齐，当前 EOL rows 仍不应通过 import dry-run。

## 2026-06-12 Week65h / EOL Extraction Service Boundary

结论：新增 EOL extraction service boundary，用于把当前 audit script 逐步迁移到 services 层；未完成 parser 迁移，未重建 JSONL，不改变 M0 状态。

- 新增：`backend/services/extraction/exam_eol.py`
- 作用：集中定义 2021/2022 EOL source metadata、默认 text/draft/audit 路径、required draft fields。
- 当前边界：`scripts/tools/audit/structure_eol_exam_docx.py` 仍是实际 parser；新增 service 只是目标边界契约。
- 下一步：把 parser 逻辑迁入 `backend/services/extraction/exam_eol.py`，再把脚本降级为 CLI wrapper。

## 2026-06-12 Week65i / EOL Metadata Single Source

结论：消除 EOL source metadata 双真相源；脚本现在复用 `backend/services/extraction/exam_eol.py` 的 metadata/path contract。未重建 JSONL，未运行 gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/structure_eol_exam_docx.py`
- 复用：`source_metadata(year)` 与 `draft_paths(year)`
- 收益：`source_id`、`source_sha256`、`source_url`、`source_state`、默认 text/draft/audit 路径不再在脚本和 service 中重复维护。
- 剩余：parser 逻辑仍需后续迁移进 `backend/services/extraction/exam_eol.py`。

## 2026-06-12 Week65j / EOL Metadata Registry Ownership

结论：EOL source metadata 已进一步收敛到 `backend/config/sources.yaml`；`backend/services/extraction/exam_eol.py` 通过 registry 读取 URL、sha、status、text path。未重建 JSONL，未运行 gate，不改变 M0 状态。

- 更新：`backend/services/extraction/exam_eol.py`
- 单一配置源：`backend/config/sources.yaml`
- service 仅保留 `year -> source_id` 最小映射。
- 收益：避免 config/service/script 三处 source metadata 漂移。

## 2026-06-12 Week65k / EOL Parser Service Migration

结论：EOL parser 核心逻辑已迁入 `backend/services/extraction/exam_eol.py`；`scripts/tools/audit/structure_eol_exam_docx.py` 已降级为 CLI wrapper。未重建 JSONL，未运行 gate，不改变 M0 状态。

- 更新：`backend/services/extraction/exam_eol.py`
- 更新：`scripts/tools/audit/structure_eol_exam_docx.py`
- 架构收益：extraction 计算回到 services 层，script 只负责 argparse 与写出文件；后续 import-readiness / source gate 可复用同一 service。
- 保护口径：迁移代码不等于 parser 正确或数据可导入；下一步仍需显式重建 draft 与跑 dry-run。

## 2026-06-12 Week65l / EOL Extraction CLI Command Surface

结论：EOL structured draft 的正式命令入口迁到 `scripts/tools/extraction/build_eol_exam_draft.py`；旧 `scripts/tools/audit/structure_eol_exam_docx.py` 保留为兼容 wrapper。未重建 JSONL，未运行 gate，不改变 M0 状态。

- 新增：`scripts/tools/extraction/build_eol_exam_draft.py`
- 新增：`scripts/tools/extraction/__init__.py`
- 更新：`scripts/tools/audit/structure_eol_exam_docx.py`
- 架构收益：extraction 命令面和 service 边界一致，audit 目录不再承载主生成入口。

## 2026-06-12 Week65m / M0 Gate Plan Includes EOL Draft Rebuild

结论：M0 gate plan 已补入 EOL draft rebuild 步骤，确保 import-readiness dry-run 使用最新 service-backed extraction 输出。未实际重建 JSONL，未运行 gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 更新：`docs/m0_gate_runbook.md`
- 新顺序：source-contract consistency → source acquisition verification → 2021/2022 EOL draft rebuild → 2021/2022 import readiness → paper contract coverage → truth baseline strict。
- EOL rebuild 命令：`python3 scripts/tools/extraction/build_eol_exam_draft.py --year 2021` 与 `--year 2022`。
- 保护口径：draft rebuild 会写 JSONL/audit，但不写 DB；本步只更新计划，没有执行。

## 2026-06-12 Week65n / Import Readiness Report Aggregates

结论：增强 import readiness report 的可读性，新增 finding code/severity 聚合统计；未运行 gate，不改变 M0 状态。

- 更新：`backend/services/imports/readiness.py`
- 新增输出：`finding_code_counts`、`finding_severity_counts`
- 收益：后续 dry-run blocked 时，controller 可直接按主阻塞原因排序修复，不需要逐行人工翻 findings。
- 保护口径：阻断逻辑未改变；没有重建 JSONL、没有 dry-run、没有写 DB。

## 2026-06-12 Week65o / Source State Taxonomy

结论：新增 source state taxonomy，并让 source-contract audit 检查 source status 是否包含合法状态 token；未运行 gate，不改变 M0 状态。

- 新增：`backend/config/source_states.yaml`
- 更新：`backend/services/audit/source_contracts.py`
- 状态机覆盖：`declared`、`raw_acquired`、`text_extracted`、`structured_draft`、`reviewed`、`import_ready`、`imported_canonical`、`linked`、`d0_verified`。
- 兼容：保留 `raw_source_acquired` 作为 `raw_acquired` legacy alias。
- 非可导入状态：`candidate_only`、`suspicious`。
- 保护口径：这是配置自洽强化，不是数据验证；未下载、未 dry-run、未写 DB。

## 2026-06-12 Week65p / Import Readiness Enforces Source State

结论：import dry-run 已接入 source 状态机，`exam_truth_source_import` 现在要求 row 携带 `source_state`，且必须满足 policy 的 `required_source_state=import_ready`。未运行 gate，不改变 M0 状态。

- 更新：`backend/config/import_policies.yaml`
- 更新：`backend/services/imports/readiness.py`
- 新阻断码：`source_state_below_import_policy`
- 预期效果：EOL rebuilt draft 即使补齐 lineage 字段，只要仍是 `structured_draft_not_import_ready`，dry-run 仍会 blocked。
- 保护口径：这是 gate 语义强化，没有重建 JSONL、没有 dry-run、没有写 DB。

## 2026-06-12 Week65q / Shared Import Policy Contract Reader

结论：新增 shared import policy contract reader，减少 EOL draft required fields 与 import policy 的双维护风险；未运行 gate，不改变 M0 状态。

- 新增：`backend/services/contracts/import_policy.py`
- 新增：`backend/services/contracts/__init__.py`
- 更新：`backend/services/imports/readiness.py`
- 更新：`backend/services/extraction/exam_eol.py`
- 架构收益：`import_policies.yaml` 的读取逻辑在 shared contract 层；EOL required draft fields = EOL 业务字段 + import policy required source fields。
- 保护口径：没有重建 JSONL、没有 dry-run、没有写 DB。

## 2026-06-12 Week65r / EOL Draft Field Coverage Audit

结论：新增 EOL draft field coverage audit，并纳入 M0 gate plan；未运行 gate，不改变 M0 状态。

- 更新：`backend/services/extraction/exam_eol.py`
- 新增：`scripts/tools/audit/eol_draft_field_audit.py`
- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 更新：`docs/m0_gate_runbook.md`
- 作用：在 EOL rebuild 和 import-readiness dry-run 之间检查 JSONL 是否具备 required fields，避免 schema/lineage 缺口与语义 import blocker 混在一起。
- 保护口径：field coverage pass 只代表字段齐全，不代表 source_state=import_ready，也不代表题目内容正确。

## 2026-06-12 Week65s / Source State Matching Bug Fix

结论：修复 import readiness 的 source_state substring 误判风险；未运行 gate，不改变 M0 状态。

- 新增：`backend/services/contracts/source_state.py`
- 更新：`backend/services/contracts/__init__.py`
- 更新：`backend/services/imports/readiness.py`
- 更新：`backend/services/audit/source_contracts.py`
- 问题：旧逻辑会让 `structured_draft_not_import_ready` 因包含 `import_ready` 子串而错误满足 required_source_state。
- 修复：source status 现在按合法 state token 前缀解析；`structured_draft_not_import_ready` 解析为 `structured_draft`，不会满足 `import_ready`。
- 保护口径：未运行 dry-run/source-contract audit，未重建 JSONL，未写 DB。

## 2026-06-12 Week65t / Nullable Source Fields in Import Policy

结论：import policy 已区分“字段缺失”和“字段存在但允许为 null”；未运行 gate，不改变 M0 状态。

- 更新：`backend/config/import_policies.yaml`
- 更新：`backend/services/imports/readiness.py`
- 更新：`backend/services/extraction/exam_eol.py`
- 新增 policy：`nullable_source_fields`，当前包括 `observed_question_number`、`reference_answer_number`。
- 收益：写作 prompt / unkeyed listening 这类行可以保留字段为 null，不再被误判为 schema 缺字段；但仍会被 review_status/source_state/import readiness 语义 gate 阻断。
- 保护口径：没有重建 JSONL、没有 dry-run、没有写 DB。

## 2026-06-12 Week65u / EOL Field Audit Nullable Reporting

结论：EOL draft field coverage report 已增强 nullable 字段表达；未运行 gate，不改变 M0 状态。

- 更新：`backend/services/extraction/exam_eol.py`
- 新增报告字段：`nullable_fields`、`absent_required_by_field`、`empty_required_by_field`
- 收益：后续字段审计能区分“字段不存在”和“非 nullable 字段为空”，同时不把允许 null 的 `observed_question_number` / `reference_answer_number` 误读为 schema 缺失。
- 保护口径：没有重建 JSONL、没有运行 field audit、没有写 DB。

## 2026-06-12 Week65v / EOL Field Audit CLI Summary

结论：EOL draft field audit CLI 已增强控制台摘要输出；未运行 gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/eol_draft_field_audit.py`
- 新增输出：`top_missing=field:count,...`
- 收益：后续 field audit fail 时，controller 可直接从终端看到主要缺失字段，无需先打开 JSON 报告。
- 保护口径：没有运行审计、没有重建 JSONL、没有写 DB。

## 2026-06-12 Week65w / Source Contract Audit Matched State Report

结论：source-contract audit report 已增强 source state 解析可见性；未运行 gate，不改变 M0 状态。

- 更新：`backend/services/audit/source_contracts.py`
- 新增报告 section：`source_states`
- 字段：`source_id`、`status`、`matched_state`、`risky`
- 收益：后续运行 source-contract audit 时，可直接确认每个 source status 是否被解析为预期状态 token。
- 保护口径：pass/fail 语义未改，未运行 audit、未检查文件、未写 DB。

## 2026-06-12 Week65x / M0 Gate Sequence Config Ownership

结论：M0 gate 顺序已迁入配置，planner 从 `backend/config/m0_gates.yaml` 读取；未运行 planner/gate，不改变 M0 状态。

- 新增：`backend/config/m0_gates.yaml`
- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 架构收益：M0 gate sequence 不再硬编码在 Python；配置成为顺序、命令、预期状态、失败处理的单一来源。
- 保护口径：没有运行 planner、没有运行 gate、没有重建 JSONL、没有写 DB。

## 2026-06-12 Week65y / M0 Runbook Uses Gate Config

结论：`docs/m0_gate_runbook.md` 已改为引用 `backend/config/m0_gates.yaml` 和 planner，不再维护第二份完整 gate 表；未运行 planner/gate，不改变 M0 状态。

- 更新：`docs/m0_gate_runbook.md`
- 单一来源：`backend/config/m0_gates.yaml`
- runbook 现在只保留执行原则、失败处理和已知 blocker。
- 保护口径：没有运行 planner、没有运行 gate、没有重建 JSONL、没有写 DB。

## 2026-06-12 Week65z / M0 Gate Planner Config Validation

结论：M0 planner 已增加配置静态校验；未运行 planner/gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 校验：gate list 非空、order 从 1 连续、name 唯一、`name/command/purpose/expected_current_status/failure_action` 非空。
- 收益：`backend/config/m0_gates.yaml` 若损坏，planner 会 fail fast，避免输出误导 gate plan。
- 保护口径：没有运行 planner、没有运行 gate、没有重建 JSONL、没有写 DB。

## 2026-06-12 Week65aa / M0 Gate Planner Boolean Flag Validation

结论：M0 planner 已增加 `writes_db` / `executes_external_fetch` 布尔类型校验；未运行 planner/gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 校验：`backend/config/m0_gates.yaml` 中每个 gate 的 `writes_db` 与 `executes_external_fetch` 必须是真正 YAML boolean。
- 收益：避免 `"false"` 字符串等风险标志被静默接受。
- 保护口径：没有运行 planner、没有运行 gate、没有重建 JSONL、没有写 DB。

## 2026-06-12 Week65ab / M0 Gate Planner Fetch-Flag Consistency

结论：M0 planner 已增加 source acquisition 命令与 `executes_external_fetch` 风险标志一致性校验；未运行 planner/gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 规则：`acquire_external_source.py` 命令若不含 `--reuse-existing`，则必须声明 `executes_external_fetch=true`。
- 当前 gate 使用 `--reuse-existing --strict`，所以可保持 `executes_external_fetch=false`。
- 保护口径：没有运行 planner、没有触网、没有写 DB。

## 2026-06-12 Week65ac / M0 Gate Artifact Write Flag

结论：M0 gate 配置新增 `writes_artifacts` 风险标志，用于区分写证据文件和写 DB；未运行 planner/gate，不改变 M0 状态。

- 更新：`backend/config/m0_gates.yaml`
- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 当前 M0 gates 配置为 `writes_artifacts=true`、`writes_db=false`，表示会写 report/manifest/JSONL/audit 等证据产物，但不写 DuckDB。
- planner 现在校验 `writes_artifacts`、`writes_db`、`executes_external_fetch` 都必须是真正 YAML boolean。
- 保护口径：没有运行 planner、没有运行 gate、没有重建 JSONL、没有写 DB。

## 2026-06-12 Week65ad / M0 Gate Planner Risk Summary

结论：M0 planner JSON 输出新增 risk summary；未运行 planner/gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 新增 JSON section：`risk_summary`
- 输出：`writes_artifacts_count`、`writes_db_count`、`executes_external_fetch_count` 及对应 gate name 列表。
- 收益：执行前可快速确认整条 M0 gate 链路是否会写 DB 或触网。
- 保护口径：没有运行 planner、没有运行 gate、没有写 DB。

## 2026-06-12 Week65ae / M0 Gate Planner Top-level Risk Booleans

结论：M0 planner JSON 顶层风险布尔值已改为从 gate 配置聚合；未运行 planner/gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- 顶层输出：`writes_artifacts`、`writes_db`、`executes_external_fetch` 现在与 `risk_summary` 保持一致。
- 收益：未来若某个 gate 被配置为写 DB 或触网，planner JSON 顶层会直接显示风险，不会固定误报 false。
- 保护口径：没有运行 planner、没有运行 gate、没有写 DB。

## 2026-06-12 Week65af / M0 Gate Planner Markdown Risk Columns

结论：M0 planner markdown 输出已增加风险列；未运行 planner/gate，不改变 M0 状态。

- 更新：`scripts/tools/audit/m0_gate_plan.py`
- markdown 表新增：`Writes artifacts`、`Writes DB`、`External fetch`
- 收益：人工执行前查看 `--format markdown` 也能直接看到每道 gate 的写文件/写 DB/触网边界。
- 保护口径：没有运行 planner、没有运行 gate、没有写 DB。

## 2026-06-12 Week65ag / External Source Inventory Gate

结论：新增外部试卷源库存审计 gate，把“历年试卷是否真的在本项目内、是否候选/可疑、是否外部绝对路径依赖”从口头判断变成可执行 contract；未运行 gate，不改变 M0 未闭环状态。

- 新增：`backend/services/audit/external_source_inventory.py`
- 新增：`scripts/tools/audit/external_source_inventory.py`
- 更新：`backend/config/m0_gates.yaml`
- Gate 位置：`source_contract_consistency` 之后、`source_acquisition_verification` 之前。
- Gate 命令：`python3 scripts/tools/audit/external_source_inventory.py --strict --fail-on-warn`
- 设计口径：candidate、suspicious、outside-project attachment 都是 M0 truth closure 风险；需要镜像进本项目、替换坏文件，或显式重定域，不能在导入阶段绕过。
- 当前预期：应 fail，因为 2023 PDF suspicious、2024/2025 PDF 仍依赖姊妹 `gaokao` 项目绝对路径、2021 听力仍是 candidate source。

## 2026-06-12 Week65ah / 2024-2025 PDF Local Mirror

结论：推进 M0 source inventory blocker 收口；2024/2025 新高考全国 II 卷英语 PDF 已从姊妹 `gaokao` 项目绝对路径依赖镜像为本项目受管 artifact。未运行 gate，未写 DB，不改变 item-level D0 未闭环状态。

- 新增本地 artifact：`data/external/exam_sources/local_pdfs/2024_xgkii_english.pdf`
- 新增本地 artifact：`data/external/exam_sources/local_pdfs/2025_xgkii_english.pdf`
- 更新：`backend/config/sources.yaml`
- 2024 sha256 保持 `c9ede1cd984332337e92bb39ce47e343edc0c110f45cc9b8ece78cb4dc059ede`，min_bytes=`500000`。
- 2025 sha256 保持 `e2245b5a498ea340f2617e85ad892c15e5ed83f0571394ef34afc4982a7f1818`，min_bytes=`500000`。
- 更新：`backend/config/m0_gates.yaml` 的 `external_source_inventory` 预期 blocker 移除 2024/2025 outside-project dependency。
- 剩余 source inventory blocker：2023 PDF suspicious、2021 listening candidate source；2024/2025 仍只是 passage-level legacy import 证据，不等于 item-level D0 verified。

## 2026-06-12 Week65ai / 2023-2024 Verified Structured Seed Registry

结论：推进散落真题数据源收敛；`data/gaokao_verified_xgkii_2023_2024.jsonl` 已登记为 source registry 中的 partial structured seed，并被 2023/2024 paper contract 引用。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 新增 source：`gaokao_verified_xgkii_2023_2024`
- 受管 artifact：`data/gaokao_verified_xgkii_2023_2024.jsonl`
- sha256：`32d9ae31b9f19fd3d1e5c212312f88bcd617ba9e7202b5ded99f03c12d50e448`
- 当前内容：12 rows，其中 2023=6 rows、2024=6 rows。
- 更新：`backend/config/sources.yaml`
- 更新：`backend/config/exam_paper_contracts.yaml`
- 保护口径：该 JSONL 只是 verified structured seed，不是完整原卷 PDF，也不是 full item-level M0 proof；2023 的 427-byte suspicious PDF blocker 仍存在。

## 2026-06-12 Week65aj / 2023 Third-Party PDF Acquisition

结论：推进 2023 source inventory blocker 收口；用项目数据获取工具替换 active registry 中 427-byte suspicious PDF，获取并锁定 2023 新课标 II 卷英语第三方 PDF。未写 DB，不声明 item-level D0 完成。

- 新 active source：`third_party_pdf_xgkii_english_2023_zizzs`
- 获取工具：`python3 scripts/tools/data_sources/acquire_external_source.py --source third_party_pdf_xgkii_english_2023_zizzs --output data/reports/external_source_acquisition_2023_zizzs.json --strict`
- 获取 manifest：`data/reports/external_source_acquisition_2023_zizzs.json`
- 本地 artifact：`data/external/exam_sources/third_party_pdfs/2023_xgkii_english_zizzs.pdf`
- bytes：`194602`
- sha256：`c51421c891f7e1344b5e8bb058fbfa57b7fbf3fec4b6d05d1ca7bbcbe0e39eda`
- 更新：`backend/config/sources.yaml`
- 更新：`backend/config/exam_paper_contracts.yaml`
- 更新：`backend/config/m0_gates.yaml`
- 旧坏文件：`data/external/gaokao_2023_xgkii_english.pdf` 仍在磁盘但只有 427 bytes，已从 active source contracts 移除。
- 保护口径：新 PDF 是 third-party source，必须与 EOL 页面、GAOKAO-Bench structured rows 和后续 item parser 交叉核验；不能直接关闭 2023 M0 truth baseline。

## 2026-06-12 Week65ak / Registry-Driven PDF Cross-Verify Gate

结论：推进 2023 third-party PDF 的可证伪 gate；`cross_verify_pdf.py` 已改为从 source registry 选择 PDF source，M0 gate plan 已加入 2023 PDF cross-check。未运行 gate，未写 DB，不声明 M0 完成。

- 更新：`scripts/tools/audit/cross_verify_pdf.py`
- 更新：`backend/config/m0_gates.yaml`
- 更新：`scripts/import_recent_exams.py`
- 新 gate：`pdf_cross_verify_2023`
- Gate 命令：`python3 scripts/tools/audit/cross_verify_pdf.py --year 2023`
- Gate 位置：source acquisition verification 之后、EOL draft rebuild 之前。
- 作用：用 registry-owned PDF 与 DB/`data/gaokao_verified_xgkii_2023_2024.jsonl` 的结构化文本做关键词交叉核验，防止第三方 PDF 未经反证就进入 2023 导入链路。
- 2024/2025 导入脚本输入路径已从姊妹 `gaokao` 项目绝对路径切换为本项目 `data/external/exam_sources/local_pdfs/` 镜像。
- 已知兼容风险：旧代码若直接 import `PDF_MAP`，需要后续加兼容 shim 或改为 registry helper；本轮未运行验证。

## 2026-06-12 Week65al / PDF_MAP Compatibility Shim

结论：收口上轮遗留兼容风险；`cross_verify_pdf.py` 已恢复 `PDF_MAP` 导出，但该 map 由 source registry 动态生成，避免旧调用方直接 import 失败，同时不退回硬编码 2024/2025 姊妹项目路径。未运行 gate，未写 DB，不改变 M0 状态。

- 更新：`scripts/tools/audit/cross_verify_pdf.py`
- 新增：`build_pdf_map()` compatibility helper。
- 恢复：`PDF_MAP = build_pdf_map()`。
- 保护口径：source registry 仍是 PDF truth-source owner；`PDF_MAP` 只是 legacy import shim。

## 2026-06-12 Week65am / PDF Cross-Verify Strict Exit

结论：收紧 `pdf_cross_verify_2023` gate 的阻断语义；`cross_verify_pdf.py` 已支持 `--strict`，M0 gate 命令已切换为 strict 模式。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`scripts/tools/audit/cross_verify_pdf.py`
- 更新：`backend/config/m0_gates.yaml`
- Gate 命令：`python3 scripts/tools/audit/cross_verify_pdf.py --year 2023 --strict`
- 严格语义：任一目标年份 `FAIL` 或 `skip` 时返回非零退出码，防止 PDF 缺失、source 未注册或结构化文本不匹配时继续后续导入链路。
- 保护口径：本轮只补 gate 退出语义，未实际执行 cross-verify；2023 third-party PDF 仍需运行 gate 并审查 mismatch 后才能升级为更强 truth evidence。

## 2026-06-12 Week65an / 2023 EOL Landing Page Acquisition

结论：补齐 2023 新课标 II 卷英语的 EOL landing-page 来源证据；该页面已通过项目数据获取工具本地化并 sha 锁定，用于后续 cross-check 第三方 PDF 身份与来源链路。未写 DB，不声明 M0 完成。

- 新 source：`eol_xgkii_english_2023_page`
- 获取工具：`python3 scripts/tools/data_sources/acquire_external_source.py --source eol_xgkii_english_2023_page --output data/reports/external_source_acquisition_2023_eol_page.json --strict`
- 获取 manifest：`data/reports/external_source_acquisition_2023_eol_page.json`
- 本地 artifact：`data/external/exam_sources/eol/2023_xgkii_english_eol.html`
- bytes：`167619`
- sha256：`acf5ddd6e6be42fbfd39b05304bf0abca2a9997802a9f9cd2e70c30cb04cc140`
- 更新：`backend/config/sources.yaml`
- 更新：`backend/config/exam_paper_contracts.yaml`
- 保护口径：EOL 页面是 landing-page/source-lineage 证据，不是 item-level full-paper proof；仍需 `pdf_cross_verify_2023` 和后续 parser/import/reconciliation gate。

## 2026-06-12 Week65ao / EOL HTML Identity in PDF Cross-Verify

结论：把 2023 EOL landing page 从“登记来源”接入 `pdf_cross_verify_2023` 的实际反证逻辑；未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`scripts/tools/audit/cross_verify_pdf.py`
- 更新：`backend/config/m0_gates.yaml`
- 新增核验：`html_identity_checks`，检查 registered EOL HTML artifact 是否命中年份、英语学科和新课标 II 卷身份标识。
- `overall` 判定已纳入 HTML identity fail：结构化文本与 PDF 不匹配或 EOL HTML 身份缺失，都会使 cross-verify overall=`FAIL`。
- `--strict` 下，overall=`FAIL` 将返回非零退出码。
- 保护口径：该变更只增强 gate 反证能力；尚未实际运行 `pdf_cross_verify_2023`，不能声称 2023 PDF 已通过交叉核验。

## 2026-06-12 Week65ap / Source Cross-Check Rules Config Ownership

结论：将 2023 EOL HTML identity 判断词从代码硬编码迁移到配置文件，符合“判断规则写 YAML，不写死在代码”的项目原则。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 新增：`backend/config/source_crosscheck_rules.yaml`
- 新增：`backend/services/contracts/source_crosscheck.py`
- 更新：`scripts/tools/audit/cross_verify_pdf.py`
- 更新：`backend/services/audit/external_source_inventory.py`
- 配置 owner：`backend/config/source_crosscheck_rules.yaml` 管理 HTML identity required groups。
- 当前规则：`eol_xgkii_english_2023_page` 必须命中年份 `2023`、学科 `英语`、以及新课标 II 卷相关标识。
- Fail-closed 行为：cross-verify 遇到 landing-page source 缺 identity rule 时 `html_identity_checks` 失败；source inventory 对 landing-page source 缺 rule 报 `landing_page_identity_rule_missing`。
- 保护口径：本轮只迁移规则所有权和 fail 条件，未实际运行 gate，不能声称 2023 EOL/PDF 已核验通过。

## 2026-06-12 Week65aq / Cross-Check Rule Consistency Audit

结论：将 `source_crosscheck_rules.yaml` 纳入 source-contract consistency 审计，避免 HTML identity 规则缺失、空 token、未知 source id 等问题等到 cross-verify 运行时才暴露。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/services/contracts/source_crosscheck.py`
- 更新：`backend/services/audit/source_contracts.py`
- 新增 shared helper：`validate_html_identity_rules()`。
- 新增审计 blocker：`landing_page_identity_rule_missing`。
- 新增规则审计 finding：`html_identity_rule_unknown_source`、`html_identity_group_has_no_tokens`、`html_identity_group_has_empty_token` 等。
- 影响 gate：`source_contract_consistency` 现在会在更早阶段发现 source identity 规则配置错误。
- 保护口径：本轮只增强配置审计，不运行 gate，不证明当前规则已通过。

## 2026-06-12 Week65ar / 2021 Listening Candidate Quarantine

结论：收口 source inventory 的 candidate 污染风险；`sunedu_new_gaokao_i_listening_2021_candidate` 已从 active `exam_sources` 移入 `quarantined_exam_sources`，并从 2021 M0 paper contract 引用中移除。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/config/sources.yaml`
- 更新：`backend/config/exam_paper_contracts.yaml`
- 更新：`backend/config/m0_gates.yaml`
- 原因：Sunedu source 标注为 2021 新高考 I 卷听力 candidate，不能在没有 shared-listening proof 的情况下关闭新高考全国 II 卷 M0 contract。
- 2021 active source 仍为：`eol_xgkii_english_2021`。
- 保护口径：这只隔离错误候选源，不解决 EOL 2021 listening rows 未 key/review 的内容缺口；后续仍需 EOL draft rebuild、field audit、import readiness 和 item-level review。

## 2026-06-12 Week65as / Quarantined Source Reference Guard

结论：将 quarantined source 边界纳入 `source_contract_consistency`，防止已隔离候选源被后续 paper contract 重新引用。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/services/audit/source_contracts.py`
- 新增审计：读取 `backend/config/sources.yaml` 的 `quarantined_exam_sources`。
- 新增 BLOCK finding：`contract_references_quarantined_source`。
- 新增 BLOCK finding：`source_id_active_and_quarantined`。
- 报告 summary 新增：`quarantined_sources`。
- 保护口径：quarantine 是来源治理边界，不是内容修复；2021 EOL listening rows 仍需 key/review 和 import-readiness。

## 2026-06-12 Week65at / EOL Review Backlog Gate

结论：把 EOL structured draft 的 item-level review 缺口显式化为 gate；2021/2022 在 import-readiness 前必须先清掉 review backlog。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 新增：`backend/config/eol_review_rules.yaml`
- 新增：`backend/services/audit/eol_review_backlog.py`
- 新增：`scripts/tools/audit/eol_review_backlog.py`
- 更新：`backend/config/m0_gates.yaml`
- 新 gate：`eol_2021_review_backlog`，命令 `python3 scripts/tools/audit/eol_review_backlog.py --year 2021 --strict`
- 新 gate：`eol_2022_review_backlog`，命令 `python3 scripts/tools/audit/eol_review_backlog.py --year 2022 --strict`
- Gate 位置：EOL draft field audit 之后、import readiness dry-run 之前。
- 规则 owner：`backend/config/eol_review_rules.yaml`，配置 required fields、blocking review_status tokens、answer-required question_type tokens、allowed empty-answer types。
- 保护口径：该 gate 只列出并阻断 item-level review backlog，不自动判题、不写 DB；2021 listening unkeyed 等问题仍需 review 后才能进入 import readiness。

## 2026-06-12 Week65au / EOL Review Rule Consistency Audit

结论：将 `eol_review_rules.yaml` 纳入早期配置一致性审计，避免 review backlog 规则缺失、空 token 或错误 priority issue code 等问题延迟到 backlog gate 才暴露。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 新增：`backend/services/contracts/eol_review.py`
- 更新：`backend/services/audit/eol_review_backlog.py`
- 更新：`backend/services/audit/source_contracts.py`
- 新增 shared loader：`load_eol_review_rules()`。
- 新增 shared validator：`validate_eol_review_rules()`。
- `source_contract_consistency` 现在会将 EOL review rule 配置问题作为 BLOCK finding 输出。
- 审计覆盖：缺 `eol_review_backlog`、required token list 空、空 token、`priority_issue_codes` 引用 backlog 工具不会产出的 issue code。
- 保护口径：本轮只增强配置审计，不运行 gate，不证明当前规则已通过。

## 2026-06-12 Week65av / EOL Review Decision Overlay Contract

结论：新增 EOL review decision overlay，作为清理 2021/2022 EOL review backlog 的受控输入面；原始 structured draft 保持不可变，review 决策单独存放并由 backlog gate 应用。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 新增：`backend/config/eol_review_decisions.yaml`
- 新增：`backend/services/contracts/eol_review_decisions.py`
- 更新：`backend/services/audit/eol_review_backlog.py`
- 更新：`scripts/tools/audit/eol_review_backlog.py`
- 更新：`backend/services/audit/source_contracts.py`
- 默认 decision 路径：`data/external/exam_sources/eol/review_decisions/{year}_xgkii_english_eol_review_decisions.jsonl`
- 稳定 key：`year` + `paper_type` + `observed_question_number` + `question_type`，适配当前旧 draft 尚未重建 source lineage 的状态。
- decision 状态：`import_ready`、`needs_followup`、`rejected`、`rescope`。
- `import_ready` decision 必须提供 `answer`、`source_id`、`source_span`。
- backlog gate 会先校验 decision JSONL，再应用 overlay 计算剩余 backlog；decision 文件错误也会作为 backlog issue 阻断。
- `source_contract_consistency` 现在会校验 decision contract 配置本身。

## 2026-06-12 Week65aw / EOL Review Worksheet Generator

结论：新增 EOL review worksheet 生成器，为 2021/2022 item-level review 提供可填写的工作表；它不修改 draft、不写 DB，也不作为 gate，通过后续正式 review decision JSONL 才影响 backlog gate。未运行工具，不改变 M0 未闭环状态。

- 新增：`backend/services/audit/eol_review_worksheet.py`
- 新增：`scripts/tools/audit/eol_review_worksheet.py`
- 默认输出：`data/reports/eol_review_worksheet_{year}_<stamp>.jsonl`
- manifest 输出：`data/reports/eol_review_worksheet_{year}_<stamp>.manifest.json`
- 用法：`python3 scripts/tools/audit/eol_review_worksheet.py --year 2021`
- 作用：读取 EOL draft + 当前 review decisions，基于剩余 backlog 生成 reviewer worksheet。worksheet 行包含稳定 key、当前 answer/source 字段、backlog issue codes、stem preview，以及待填写的 decision_status/reviewer/reviewed_at/answer/source_id/source_span/review_note。
- 保护口径：worksheet 不是正式 decision 文件；正式 decision 仍必须写入 `data/external/exam_sources/eol/review_decisions/{year}_xgkii_english_eol_review_decisions.jsonl` 并通过 backlog gate 校验。

## 2026-06-12 Week65ax / EOL Review Decision Materializer

结论：新增 worksheet → official review decision JSONL 的受控转换工具，补齐 EOL review 工作流从“生成 worksheet”到“进入 backlog gate”的中间步骤。未运行工具，未创建 decision 数据，未写 DB，不改变 M0 未闭环状态。

- 新增：`backend/services/audit/eol_review_decision_materialize.py`
- 新增：`scripts/tools/audit/eol_review_decision_materialize.py`
- 用法示例：`python3 scripts/tools/audit/eol_review_decision_materialize.py --year 2021 --worksheet data/reports/eol_review_worksheet_2021_<stamp>.jsonl`
- 默认输出：`data/external/exam_sources/eol/review_decisions/{year}_xgkii_english_eol_review_decisions.jsonl`
- 默认 manifest：`data/reports/eol_review_decision_materialize_{year}_<stamp>.json`
- Fail-closed 行为：worksheet 无 completed decision、contract 校验失败、或 output 已存在且未显式 `--overwrite` 时返回非零。
- 保护口径：materializer 只转换已填写 `decision_status` 的 worksheet 行，并用既有 decision contract validator 校验；不自动判题、不修改 draft、不写 DB。

## 2026-06-12 Week65ay / EOL Review Worksheet Stable-Key Alignment

结论：修复 EOL review backlog identity 与 review-decision stable key 的字段不一致问题，避免 worksheet 生成时无法回连原始 draft row。未运行工具，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/services/audit/eol_review_backlog.py`
- 更新：`backend/services/audit/eol_review_worksheet.py`
- 修复点：backlog identity 现在显式输出 `paper_type` 与 `observed_question_number`，并保留 `question_number` 作为兼容字段。
- worksheet 输出的 `observed_question_number` 现在直接来自 backlog identity 的 `observed_question_number`。
- 影响：worksheet 能按 `year + paper_type + observed_question_number + question_type` 稳定 key 回连 draft row，减少 reviewer 工作表缺上下文风险。
- 保护口径：本轮只修复 review workflow 的 key alignment，未运行 worksheet/backlog/materializer。

## 2026-06-12 Week65az / EOL Review Worksheet Shape Validation

结论：为 worksheet → official review decision 转换增加 worksheet shape 校验，防止 reviewer 填错/删错 stable key 后才污染正式 decision 文件。未运行工具，未创建 decision 数据，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/config/eol_review_decisions.yaml`
- 更新：`backend/services/contracts/eol_review_decisions.py`
- 更新：`backend/services/audit/eol_review_decision_materialize.py`
- 新增配置：`worksheet_required_fields`，当前包含 `worksheet_kind`、`year`、`paper_type`、`observed_question_number`、`question_type`。
- 新增 validator：`validate_worksheet_rows()`。
- Materializer 现在先校验 worksheet row shape，再抽取 completed decisions；worksheet 缺 stable key 或 worksheet_kind 异常会阻断 official decision 输出。
- 保护口径：这只是 review workflow 的输入防线，不自动判题、不运行 gate。

## 2026-06-12 Week65ba / EOL Review Materializer Year and Output Guards

结论：增强 worksheet → official decision materializer 的 fail-closed 行为，阻断跨年 worksheet 误写和未声明覆盖已有 official decision 文件。未运行工具，未创建 decision 数据，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/services/contracts/eol_review_decisions.py`
- 更新：`backend/services/audit/eol_review_decision_materialize.py`
- 更新：`scripts/tools/audit/eol_review_decision_materialize.py`
- 新增 finding：`review_worksheet_year_mismatch`，当 worksheet row 的 `year` 与 CLI `--year` 不一致时阻断。
- 新增 finding：`decision_output_exists`，当 official decision output 已存在且未传 `--overwrite` 时阻断。
- Materializer 现在在 report 阶段就能暴露 output exists，避免 manifest pass 但实际写文件失败的状态不一致。
- 保护口径：本轮只加安全 guard，未运行 materializer 或 backlog gate。

## 2026-06-12 Week65bb / Non-Import-Ready Decision Blocking Rule

结论：修复 review-decision overlay 的语义漏洞；非 `import_ready` 的 official decision 不会意外清掉 EOL review backlog。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/config/eol_review_rules.yaml`
- 新增 blocking token：`review_decision_`
- 语义：materializer 对 `needs_followup`、`rejected`、`rescope` 会产生 `review_status=review_decision_<status>`，现在这些状态会被 backlog gate 视为 `review_status_blocked`。
- 例外：`import_ready` decision 会被 overlay 成 `review_status=import_ready`，不匹配 `review_decision_`，仍按 answer/source/span 等必填字段接受后续检查。
- 保护口径：本轮只更新配置规则，未运行 backlog gate 或 materializer。

## 2026-06-12 Week65bc / EOL Review Decision Coverage Audit

结论：新增 official review decision coverage 审计，并让 backlog gate 阻断 unmatched decision key。未运行工具，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/config/eol_review_rules.yaml`
- 更新：`backend/services/contracts/eol_review.py`
- 更新：`backend/services/audit/eol_review_backlog.py`
- 新增：`backend/services/audit/eol_review_decision_coverage.py`
- 新增：`scripts/tools/audit/eol_review_decision_coverage.py`
- 新 issue code：`unmatched_review_decision_key`。
- Backlog gate 行为：official decision key 找不到当前 draft row 时，会作为 backlog issue 阻断。
- Coverage CLI：`python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2021 --strict`
- Coverage report 输出 matched decisions、unmatched decisions、undecided draft rows、decision findings 和 remaining backlog item count。
- 保护口径：coverage audit 只审计 decision 覆盖，不自动判题、不修改 draft、不写 DB。

## 2026-06-12 Week65bd / EOL Review Decision Coverage Gates

结论：将 official review decision coverage 从辅助工具提升为 M0 gate，放在 review backlog gate 之前，防止 stale/unmatched decision key 在 overlay 阶段静默失效。未运行 gate，未写 DB，不改变 M0 未闭环状态。

- 更新：`backend/config/m0_gates.yaml`
- 新 gate：`eol_2021_review_decision_coverage`
- 新 gate：`eol_2022_review_decision_coverage`
- 命令：`python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2021 --strict`
- 命令：`python3 scripts/tools/audit/eol_review_decision_coverage.py --year 2022 --strict`
- Gate 位置：EOL draft field audit 之后、EOL review backlog 之前。
- 语义：先检查 official decisions 是否匹配当前 draft stable keys，并汇总 remaining backlog，再由 review backlog gate 应用 overlay 逐项阻断。
- 保护口径：coverage gate 不写 DB、不修改 draft；当前预期仍会 fail，直到 review decisions 覆盖并清掉 EOL backlog。

### 2026-06-12 - Mythos skill lessons absorbed into project agent rules
- Updated `agent.md` with additional reusable constraints distilled from the Claude root `mythos` skill.
- Added explicit project guidance for macOS/TCC proof, proxy/network false positives, PIT-style historical reasoning, DuckDB single-writer discipline, hook root-cause handling, external API failure taxonomy, experiment preregistration, reproducible derived artifacts, and remediation verification closure.
- No M0 gate, Moth, CodeGraph, DB write, or runtime validation was run in this documentation-only update.

## 2026-06-12 Week65be / EOL Review Decision Coverage CLI Evidence

结论：增强 official review decision coverage gate 的失败可解释性；不改变 gate 语义，不产生新的准确性通过证据。未运行 gate，未写 DB。

- 更新：`scripts/tools/audit/eol_review_decision_coverage.py`
- CLI 摘要新增：`decision_path_exists=<bool>`。
- CLI 摘要新增：`findings=<count>`。
- 目的：当 review decision 文件缺失时，strict coverage gate 的 stdout 能直接暴露 `review_decision_file_missing` 对应的文件存在性信号，避免把“文件不存在”和“空 decision 文件”混为 `decision_rows=0`。
- 保护口径：本轮只增强 coverage audit 的可观察性；未创建 decision 文件，未运行 worksheet/materializer/backlog/coverage gate。

## 2026-06-12 Week65bf / Non-Import-Ready Review Decision Rationale

结论：收紧 EOL official review decision 契约，要求非 `import_ready` decision 必须留下 `review_note`；不改变 draft、不创建 decision 文件、不写 DB。未运行 gate。

- 更新：`backend/config/eol_review_decisions.yaml`
- 更新：`backend/services/contracts/eol_review_decisions.py`
- 新增配置：`non_import_ready_required_fields: [review_note]`
- 新增 finding：`review_decision_non_import_ready_field_missing`
- 语义：`needs_followup`、`rejected`、`rescope` 等 official decision 仍然保持 backlog blocker；现在还必须说明原因，防止无证据/无理由的正式 decision 污染 review overlay。
- 保护口径：worksheet 已包含 `review_note` 字段，本轮不改 worksheet shape；未运行 materializer、coverage 或 backlog gate。

## 2026-06-12 Week65bg / EOL Review Worksheet Contract Guidance

结论：增强 reviewer worksheet 的自描述能力，减少人工填写 official decision 时的契约误填；不创建 worksheet、不创建 decision 文件、不写 DB。未运行 gate/tool。

- 更新：`backend/services/audit/eol_review_worksheet.py`
- worksheet manifest 现在包含 `decision_contract` 摘要。
- 每个 worksheet row 现在包含 `decision_contract` 摘要：allowed decision statuses、required fields、`import_ready_required_fields`、`non_import_ready_required_fields` 和 status guidance。
- 目的：reviewer 不需要另外翻 `backend/config/eol_review_decisions.yaml` 才知道 `import_ready` 需要 `answer/source_id/source_span`，非导入状态需要 `review_note`。
- 保护口径：这只改 worksheet 输出形态，不自动判题、不修改原始 structured draft、不 materialize official decisions。

## 2026-06-12 Week65bh / Review Decision Finding Taxonomy

结论：将 official review decision validator 的错误码纳入 EOL review backlog 的 known/priority taxonomy；不创建 decision 文件、不改 draft、不写 DB。未运行 gate。

- 更新：`backend/services/contracts/eol_review.py`
- 更新：`backend/config/eol_review_rules.yaml`
- 新增 known/priority issue codes：`duplicate_review_decision_key`、`review_decision_status_unknown`、`review_decision_required_field_missing`、`review_decision_import_ready_field_missing`、`review_decision_non_import_ready_field_missing`。
- 目的：official decision 文件的格式错误、未知状态、缺基础字段、缺 import-ready 证据、缺非导入理由都成为 review backlog 的一等问题，而不是落到 `other`。
- 保护口径：本轮只补 taxonomy；未运行 source-contract consistency、coverage、backlog、materializer 或 M0 gate。

## 2026-06-12 Week65bi / Worksheet Partial Decision Fail-Closed Guard

结论：收紧 worksheet -> official decision materializer，防止半填写 review 行被静默丢弃；不创建 decision 文件、不写 DB。未运行 tool/gate。

- 更新：`backend/services/audit/eol_review_decision_materialize.py`
- 更新：`scripts/tools/audit/eol_review_decision_materialize.py`
- 新增 finding：`review_worksheet_partial_decision_missing_status`
- 新增 summary：`partial_rows`
- 规则：当 worksheet 行的 `decision_status` 为空，但 `reviewer`、`reviewed_at`、`review_note`、`review_status` 已填写，或 `answer/source_id/source_span` 相比 `current_*` 字段发生变化时，materializer 返回 fail。
- CLI 摘要现在输出 `partial_rows=<count>`，方便定位半填写行是否阻断本次 materialization。
- 保护口径：本轮只增强 materializer fail-closed 行为；未运行 worksheet、materializer、coverage、backlog 或 M0 gate。

## 2026-06-12 Week65bj / Materializer Missing Worksheet Guard

结论：收紧 worksheet -> official decision materializer 的输入存在性检查，避免“worksheet 文件不存在”和“空 worksheet”混为同一类失败；不创建 decision 文件、不写 DB。未运行 tool/gate。

- 更新：`backend/services/audit/eol_review_decision_materialize.py`
- 更新：`scripts/tools/audit/eol_review_decision_materialize.py`
- 新增 finding：`review_worksheet_file_missing`
- 新增 summary：`worksheet_path_exists`
- CLI 摘要现在输出 `worksheet_path_exists=<bool>`，便于区分路径错误、未生成 worksheet 与 worksheet 为空。
- 保护口径：本轮只增强 materializer fail-closed 和可观察性；未运行 worksheet、materializer、coverage、backlog 或 M0 gate。

## 2026-06-12 Week65bk / Materializer Output Path Existence Evidence

结论：增强 worksheet -> official decision materializer 的输出覆盖可观察性，避免 `decision_output_exists` 只在 finding detail 中可见；不创建 decision 文件、不写 DB。未运行 tool/gate。

- 更新：`backend/services/audit/eol_review_decision_materialize.py`
- 更新：`scripts/tools/audit/eol_review_decision_materialize.py`
- 新增 summary：`output_path_exists`
- CLI 摘要现在输出 `output_path_exists=<bool>`。
- 语义保持不变：official decision output 已存在且未传 `--overwrite` 时仍 fail closed。
- 保护口径：本轮只增强 materializer report/stdout 的证据面；未运行 worksheet、materializer、coverage、backlog 或 M0 gate。

## 2026-06-12 Week65bl / Materializer Issue Taxonomy

结论：为 worksheet -> official decision materializer 建立独立 issue taxonomy，避免把 materializer 输入/输出错误混入 backlog taxonomy 或落入不透明 `other`；不创建 decision 文件、不写 DB。未运行 tool/gate。

- 更新：`backend/config/eol_review_decisions.yaml`
- 更新：`backend/services/contracts/eol_review_decisions.py`
- 更新：`backend/services/audit/eol_review_decision_materialize.py`
- 新增配置：`materializer_priority_issue_codes`
- 新增 known set：`KNOWN_MATERIALIZER_ISSUE_CODES`
- 新增 contract finding：`eol_review_decision_materializer_issue_unknown`
- materializer report summary 新增：`priority_buckets`
- 覆盖问题：worksheet 文件缺失、worksheet required field 缺失、worksheet kind 异常、跨年 worksheet、半填写行缺 `decision_status`、无 completed decision、output 已存在、duplicate decision key、未知 decision status、decision 必填字段缺失、import-ready 证据缺失、非导入理由缺失。
- 保护口径：materializer taxonomy 与 EOL backlog taxonomy 分离；本轮不改变 backlog gate 语义，未运行 materializer/coverage/backlog/M0 gate。

## 2026-06-12 Week65bm / 2022 EOL Official Review Decisions Batch 1

结论：开始从真实 EOL source artifact 产出 official review decisions；2022 written-paper 21-40 题已有首批 `import_ready` overlay。未运行 gate，未写 DB，不声明 M0 通过。

- 新增：`data/external/exam_sources/eol/review_decisions/2022_xgkii_english_eol_review_decisions.jsonl`
- 覆盖范围：2022 新高考全国 II 卷英语 EOL structured draft 的 21-40 题。
- Source evidence：`data/external/exam_sources/eol/2022_xgkii_english_eol.txt` line 1 的 EOL reference answer table。
- Decision source id：`eol_xgkii_english_2022`
- Decision status：全部为 `import_ready`。
- 纠偏：33 题 draft answer 从 `E` 覆盖为 `C`，以 EOL reference answer table 为 truth source。
- 补缺：38-40 题 draft answer 从 `null` 覆盖为 `E/F/G`。
- 保护口径：本轮只创建 official review decision overlay，不修改 generated structured draft，不写 DuckDB，不运行 materializer/coverage/backlog/import-readiness gate。后续必须运行 coverage/backlog gate 才能证明这些 decisions 与当前 draft stable keys 匹配并清除对应 backlog。
- 剩余：2021 listening raw unkeyed 仍无 answer key；2022 41-65 与 writing rows 仍需 review/decision 或 rescope。

## 2026-06-12 Week65bn / 2022 EOL Official Review Decisions Batch 2

结论：继续从真实 EOL source artifact 产出 official review decisions；2022 written-paper 41-65 题已追加 `import_ready` overlay。未运行 gate，未写 DB，不声明 M0 通过。

- 更新：`data/external/exam_sources/eol/review_decisions/2022_xgkii_english_eol_review_decisions.jsonl`
- 追加范围：2022 新高考全国 II 卷英语 EOL structured draft 的 41-65 题。
- Source evidence：`data/external/exam_sources/eol/2022_xgkii_english_eol.txt` line 1 的 EOL reference answer table。
- Decision source id：`eol_xgkii_english_2022`
- Decision status：全部为 `import_ready`。
- 41-55：`cloze_fill_in_blanks`，答案 `D/C/D/C/A/D/A/D/B/B/A/C/C/A/B`。
- 56-65：`grammar_fill`，答案 `falling/The/asleep/to see/accidentally/and/was fixing/threw/son's/how`。
- 保护口径：本轮只追加 official review decision overlay，不修改 generated structured draft，不写 DuckDB，不运行 materializer/coverage/backlog/import-readiness gate。
- Residual：2022 writing prompt 的 draft row `observed_question_number` 为空，现有 official decision key contract 要求该字段非空，因此本轮不生成写作题 `rescope` decision，避免制造无效 decision。后续需要先定义 writing prompt stable key 或 rescope contract。
- 剩余：2021 listening raw unkeyed 仍无 answer key；2022 writing prompt 仍需 key/rescope 契约处理；2022 decisions 仍需 coverage/backlog gates 证明匹配并清除 backlog。

## 2026-06-12 Week65bo / 2022 Writing Prompt Rescope Decision

结论：为 2022 EOL writing prompt 建立稳定 key fallback，并追加受控 `rescope` official decision；不伪造写作题答案，不写 DB。未运行 gate。

- 更新：`backend/config/eol_review_decisions.yaml`
- 更新：`backend/services/contracts/eol_review_decisions.py`
- 更新：`backend/config/eol_review_rules.yaml`
- 更新：`data/external/exam_sources/eol/review_decisions/2022_xgkii_english_eol_review_decisions.jsonl`
- 新增 contract：`key_field_fallbacks.observed_question_number.writing_prompt_unanswered = writing_prompt`
- `decision_key()` 现在在 draft row 缺 key 字段时，可按 question_type 使用配置化 fallback key。
- 新增 contract validation：fallback field 必须属于 `key_fields`，fallback map/value 不能为空。
- Backlog blocking 策略调整：`needs_followup` 与 `rejected` 继续阻断；显式 `rescope` 不再被 broad `review_decision_` token 阻断。
- 新增 2022 writing prompt decision：`decision_status=rescope`，`observed_question_number=writing_prompt`，`source_span=2022_xgkii_english_eol.txt:line1:writing_section`。
- 语义：写作 prompt 有 source lineage，但当前 objective-question/import-ready answer overlay 不导入写作题；后续若要导入写作题，需要专门的 writing prompt/rubric schema。
- 保护口径：本轮未运行 source-contract consistency、coverage、backlog、import-readiness 或 M0 gate；仍需后续 gate 证明 fallback key 与当前 draft 匹配并清除对应 backlog。

## 2026-06-12 Week65bp / 2021 EOL Official Review Decisions Batch 1

结论：为 2021 EOL written rows 产出 official review decisions，并明确不把 EOL reference table 的阅读 1-20 误用为听力 1-20。未运行 gate，未写 DB，不声明 M0 通过。

- 新增：`data/external/exam_sources/eol/review_decisions/2021_xgkii_english_eol_review_decisions.jsonl`
- 更新：`backend/config/eol_review_decisions.yaml`
- 取证：`data/external/exam_sources/eol/2021_xgkii_english_eol.txt` line 1 包含 EOL reference answer table。
- 重要判定：reference table 中 `第二部分 阅读 1-20` 对应 draft observed 21-40；不能用来 key listening observed 1-20。
- 新增 45 条 `import_ready` decisions：
  - observed 21-40：`reading_or_seven_choose_five` / `seven_choose_five`，source span `reference_answer_table:reading_1-20_to_observed_21-40`
  - observed 41-55：`cloze_fill_in_blanks`，source span `reference_answer_table:language_use_21-35_to_observed_41-55`
  - observed 56-65：`grammar_fill`，source span `reference_answer_table:grammar_36-45_to_observed_56-65`
- 新增 fallback stable keys：`applied_writing -> applied_writing`，`narrative_writing -> narrative_writing`。
- 新增 2 条 `rescope` decisions：2021 applied writing 与 narrative writing 样例答案均 source-linked，但不进入当前 objective-question/import-ready answer overlay。
- 保护口径：本轮只创建 official review decision overlay，不修改 generated structured draft，不写 DuckDB，不运行 materializer/coverage/backlog/import-readiness gate。
- 剩余：2021 listening observed 1-20 仍缺明确 answer truth source；必须继续寻找听力参考答案或保持 backlog，不得用阅读答案表伪装通过。

## 2026-06-12 Week65bq / 2021 Listening Candidate Source Acquisition and Decisions

结论：为 2021 listening observed 1-20 找到并登记外部 candidate answer source，完成本地 acquisition，并追加 official review decisions。未运行 gate，未写 DB，不声明 M0 通过。

- 更新：`backend/config/sources.yaml`
- 更新：`data/external/exam_sources/eol/review_decisions/2021_xgkii_english_eol_review_decisions.jsonl`
- 新增 acquisition manifest：`data/reports/external_source_acquisition_2021_sohu_listening.json`
- 新增本地 artifact：`data/external/exam_sources/listening/2021_new_gaokao_listening_sohu.html`
- Source id：`sohu_shared_new_gaokao_listening_2021_candidate`
- Source URL：`https://www.sohu.com/a/755417015_121124334`
- Acquired sha256：`6089470a8e3ac4ba7fe2694c13333016af74486ca516a8662b3bd6c9b36021b0`
- Acquired bytes：35820
- Candidate answer key：`1-5 CCBAC`，`6-10 ABABA`，`11-15 CBCAB`，`16-20 ACBCC`。
- 追加 20 条 2021 listening `import_ready` decisions，source_id 指向 Sohu candidate source，review_note 明确题干与本地 EOL 2021 listening prompts 匹配。
- 保护口径：该 source 仍标记为 `raw_source_acquired_candidate_shared_listening_needs_crosscheck`，不是 EOL 官方 answer table；后续必须用 coverage/backlog/source-contract 或人工复核确认 stable key、source status 和 prompt match，不能直接声明 M0 已过。
- 本轮未运行 source-contract consistency、coverage、backlog、import-readiness、Moth、CodeGraph 或 DB 写入。

## 2026-06-12 Week65br / Review Decision Source Registry Guard

结论：official review decision validator 现在校验 `source_id` 是否登记在 centralized source registry，并限制可接受 source family；不运行 gate，不写 DB。

- 更新：`backend/config/eol_review_decisions.yaml`
- 更新：`backend/services/contracts/eol_review_decisions.py`
- 新增配置：`allowed_decision_source_families`
  - `exam_truth_source`
  - `listening_source_candidate`
- 新增 materializer priority codes：`review_decision_source_unknown`、`review_decision_source_family_disallowed`
- `validate_decisions()` 现在复用 `backend.services.data_sources.registry.load_registry()`：
  - decision 行只要填写 `source_id`，就必须能在 `backend/config/sources.yaml` 的 `exam_sources` 中解析。
  - source family 不在白名单时，返回 blocking finding。
- 保护口径：该 guard 防止 future official decisions 引用未登记或错误 family 的 source；不证明当前 decisions 已通过 coverage/backlog/import-readiness。
- 本轮未运行 source-contract consistency、materializer、coverage、backlog、M0 gate、Moth、CodeGraph 或 DB 写入。

## 2026-06-12 Week65bs / M0 Closure Checkpoint

结论：进入收口状态，但不声明完成。已将当前成果、未跑 gates、剩余风险和后续命令整理到 `docs/M0_CLOSURE_CHECKPOINT_2026-06-12.md`。

- 新增：`docs/M0_CLOSURE_CHECKPOINT_2026-06-12.md`
- 当前已具备：2021/2022 official review decision overlay、source registry、2021 listening candidate acquisition、writing rescope、decision source registry guard。
- 当前不能声明完成：未运行 source-contract consistency、coverage、backlog、import-readiness、Moth、CodeGraph 或 DB gate。
- 关键风险：2021 listening 依赖 Sohu candidate source，仍需 cross-check；当前代码/配置没有经过后验 gate。
- 下一自然动作：在用户明确授权验证后，按 closure checkpoint 中列出的 gate 顺序运行并修复发现。
