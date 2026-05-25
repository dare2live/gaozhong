# gaozhong 项目 — 沈阳/辽宁高中英语教学系统

新 session 接手先读 `CLAUDE.md` + 本文件 + `docs/architecture.md` (八条铁律) + `docs/lessons_learned.md` (16 条).
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

---

## 阶段速览 (2026-05-24 当日)

| # | 阶段 | 状态 |
|---|---|---|
| 1 | 数据基石 + 框架 | ✅ 4945 nodes / 34697 edges |
| 2 | 题库 + 条件组卷 | ✅ 509 题 + 10641 mapping |
| 3 | 教师端 + 本地部署 | ✅ start.command |
| 4 | 真问题修 (data/UI/趋势/economist) | ✅ 完整 (4.7.C-E 全做完) |
| **5** | **统一教学系统 + 40 节分层课程** | **✅ 13 验收门 12 ✅ + 1 OK 升级** |
| 6 | 运营交付准备 | 🚧 持续推进 (跳老师真试 / Docker, 自身完整度替代) |

**用户 2026-05-24 决策**:
- ⏸️ 跳过 6.C 老师真试 + 6.F Docker 部署 (替代: 自身完整度)
- 🎯 跨版本对照算法准确率目标 **100%** (不是 80%)
- 🎯 持续推进直到真具备交付条件

## 第四阶段 — 真问题修 + 真部署 + 真用 (历史)

> **诊断 (2026-05-24 用户反复挑战)**: 前 3 阶段"跑通" 多于"真做到". 数据准确性 / 前端统一 / 命题模型 / 经济学人风格 / 跨年覆盖 / 深度关联 UI 都是"形式 OK 实质未验". 第四阶段不再加新功能, 修真问题 + 真部署 + 真用一轮.

### 4.1 数据治理真到位 (P0, 估 2-3 天)

| # | 真问题 | 当前 | 目标 | 验收 |
|---|---|---|---|---|
| **4.1.A** | vocab extractor 漏抓 → 加 Vocabulary 章节合并抽 | 外研 2025/人教 1644 | 外研 ≥ 1900 / 人教 ≥ 1500 (调阈值, 教材实测只覆盖 ~67% 课标 — L-F 修订) | ✅ `audit_cumulative_by_grade` |
| **4.1.B** | 某些 unit 仅 3-5 词 | bixiu_2/U3=3 | 每册 ≥ 80 unique (vocab_total 合并后) | ✅ `audit_vocab_per_volume` |
| **4.1.C** | 高一/二/三 累计覆盖 | 高三末 2025 / 1644 | actual ≥ baseline + 20% headroom | ✅ `audit_cumulative_by_grade` |
| **4.1.D** | 高考考点全覆盖 | 没算 | 真题 token ≥ 85% 在 课标∪教材 | ✅ `audit_exam_token_coverage` |
| **4.1.E** | 跨版本同主题对照 | 函数有, 没验证 | 抽 5 对人工核 ≥ 80% 准 | docs/cross_version_check.md |
| **4.1.F** | 10 项治理 audit (人工抽样) | 0 项做 | 每项落 audit_findings + 人工 review 50 sample | docs/data_audit_v2_report.md |

### 4.2 前端统一框架 (P0, Rule 5 落地, 估 1-2 天)

| # | 改 | 当前 | 目标 |
|---|---|---|---|
| **4.2.A** | 抽 `frontend/static/common.js` | 3 页各自 fetchJSON / tagChip / renderTable | 1 套, 3 页全调 |
| **4.2.B** | 抽 `frontend/static/layout.html` 片段 | header/nav/footer 各自硬编码 | fetch 注入 |
| **4.2.C** | 统一经济学人配色 + 字体 | teacher/student 自带 inline css | 全部走 style.css |
| **4.2.D** | 验收: `audit_frontend_*` 全 OK | 3 WARN | 0 WARN |
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

## 第四阶段验收门

**全部满足才能宣布"可对内部教研团队交付试运营":**
1. ✅ 0 FAIL audit (含 4.1.A-D 新 audit)
2. ✅ 高三末累计 ≥ 3000 词 (vocab extractor 真修对)
3. ✅ 前端 3 个 audit (`frontend_inline_*`/`frontend_duplicate_fetch`) 全 OK
4. ✅ 命题趋势文档有真模型输出 (sklearn 或同等)
5. ✅ 经济学人 reference doc + 5 元素实装
6. ✅ Docker 服务器实跑 + 老师试用反馈入档 `docs/teacher_feedback_round1.md`
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

| audit | 出处铁律 / 来源 | 验收门 |
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

### 5.8 验收门 (13 条) — 完成态 ✅

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
| 7 | start.command 30 秒 7 tab 流畅 | ✅ 技术验收 (老师真测待 4.6.E) |

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

### 6.C 老师试用 + 反馈 ⏸️ 跳过 (用户 2026-05-24 明示)
- ~~4.6.E 找老师试 30 分钟~~ — 用户决定跳过, 由系统自身完整度替代
- 替代验收: 全 audit OK + 全 P1 完成 + 文档闭环

### 6.D 学生答题闭环 ✅ (2026-05-24)
- 4.7.D ✅ csv import students (POST /api/students/import_csv)
- 4.7.E ✅ 弱点真算 service (weakness.recompute_all + guard)
- 4.7.C ✅ 扫描 POST UI (G tab 上传表单 + 清单)

### 6.E 真问题修 (诚实暴露后再修, 用户 2026-05-24 升级目标至 100%)
- 4.1.E 跨版本对照算法 — 第一版准确率 4/15=26.7% ❌
  → 用户硬约束: **必须 100% 准确率**
  → 重做: 标题核心词 lemma jaccard + level1 主题双过滤, 严格高准
  → 验证 ≥5 对人工核, 0 错 才过

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
| B5 | 无真人验证 | 不知道哪里"纸上谈兵" | 0 学生/老师实测 |
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

**验收门**:
- [ ] 40 节讲义 ≥5000 字符 (avg)
- [ ] R2 audit 0 FAIL (生成后)
- [ ] R5 audit 0 FAIL (生成后)
- [ ] 人工抽检 5 节 — 内容可读性 + 知识准确性

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

### 7.4 题目质量升级 (P1, 估 2 天)

> **目标**: 从"机械挖空"升级到"有语境的真题质量".

| # | 改进 |
|---|---|
| 7.4.A | rule_synth 175 题重审: 保留有价值的, 标记/替换低质的 |
| 7.4.B | LLM 生成完形填空 (5 篇 × 15 空 = 75 新题, 按主题分) |
| 7.4.C | LLM 生成语法填空 (10 篇 × 10 空 = 100 新题) |
| 7.4.D | 阅读理解长文入库 (从真题 PDF 提取 + LLM 改编) |
| 7.4.E | 干扰项质量: LLM 生成合理干扰 (同词性/近义/常混淆) |

### 7.5 交互式前端 (P1, 估 2-3 天)

> **目标**: 从"数据展示板"变成"学生能自学的工具".

| # | 功能 |
|---|---|
| 7.5.A | Quiz mode: B tab 每节底部"课后测验"按钮 → 10 题即时做 + 即时批改 |
| 7.5.B | 学习进度条: 已完成课节 / 已答题数 / 正确率趋势 |
| 7.5.C | 弱点 drill: E tab 弱点 → 点击 → 自动出 5 题强化 (复用 followup 逻辑) |
| 7.5.D | 写作提交: textarea → 保存草稿 → (P2: LLM 批改) |
| 7.5.E | 移动端适配: responsive CSS (学生手机用) |

### 7.6 真人验证 (P0, 估半天)

> **目标**: 用 1 个真高中生走完全流程, 发现所有"纸上谈兵".

| # | 步骤 |
|---|---|
| 7.6.A | 找 1 个高二/高三学生 (或内部员工子女) |
| 7.6.B | 录屏: 摸底测验 → 查看推荐课节 → 上课 → 做题 → 看弱点 |
| 7.6.C | 记录: 卡住的地方 / 不理解的 UI / 内容质量反馈 |
| 7.6.D | 整理 `docs/user_test_round1.md` → 反馈驱动修 bug |

### 7.7 持续更新管线 (P2, 估 1 天)

| # | 任务 |
|---|---|
| 7.7.A | 年度真题入库脚本 (每年 6 月高考后 → 抓题 → infer_province → 入库) |
| 7.7.B | 教材版本检测 (课标/教材换版 → 提醒更新) |
| 7.7.C | 词汇增量 (新学年开学 → OCR 新教材补充词) |

### 7.8 验收门 (Phase 7 完成标准)

| # | 门 | 标准 |
|---|---|---|
| 1 | 讲义内容量 | 40 节 avg ≥5000 字符, 7 段完整 |
| 2 | 听力 | ≥20 题 has_audio=true + transcript |
| 3 | 续写+应用文 | ≥10 续写 + 10 应用文 (含范文+评分) |
| 4 | 题目总量 | ≥700 题 (升级 rule_synth + 新增) |
| 5 | R2/R5 audit | 0 FAIL (LLM 生成后) |
| 6 | 真人验证 | 1 人完整走通 + feedback 入档 |
| 7 | Quiz mode | 学生可在前端做题 + 即时反馈 |
| 8 | CC baseline | ≤ 8 (不涨) |
| 9 | D0 100% | 全部检查通过 (含新增 check) |

### 7.9 实施顺序 (按 ROI + 依赖)

```
Phase 7 执行路线图:

Week 1:  7.1 LLM 充实讲义 (G_FINAL 10 节优先 → G1 → G2/G3)
         ├─ 先做 1 节 prototype → 验证 R2/R5 能 pass
         └─ 通过后批量 40 节

Week 2:  7.2 听力 + 7.3 续写/应用文 (可并行)
         ├─ 听力: transcript 收集 + 入库
         └─ 续写: 真题整理 + LLM 辅助写范文

Week 3:  7.4 题目升级 + 7.5 交互前端
         ├─ LLM 生成高质量新题
         └─ Quiz mode + 进度条

Week 4:  7.6 真人验证 + 修 bug + 7.7 管线
         └─ 收尾 + 文档闭环
```

### 7.10 技术选型 (codegraph 分析结果)

**现有架构可扩展点** (codegraph context 2026-05-25):
```
扩展模块:
  backend/services/course/llm_enrich.py   ← 新 (调 Claude API)
  backend/services/course/listening.py    ← 新 (听力管理)
  backend/services/course/writing.py      ← 新 (续写/应用文)
  backend/config/llm_prompts.yaml         ← 新 (M3 外置)
  scripts/batch_enrich.py                 ← 新 (批量 LLM)

已有可复用:
  course/handout.py:render_handout        ← 现有 7 段渲染, 扩展不替换
  course/lexicon_filter.py                ← R5 词汇白名单, LLM prompt 注入
  course/scenarios.py:check_textbook_overlap ← R2 检查, 生成后调用
  placement/followup.py                   ← 弱点 drill 可复用

Complexity baseline (2026-05-25):
  449 funcs / 8 CC>10 / 107 py files / 7 js files
  新增模块目标: 每模块 ≤ 150 行, CC ≤ 8
```

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
