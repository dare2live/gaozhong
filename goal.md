# gaozhong 项目 — 沈阳/辽宁高中英语教学系统

新 session 接手先读 `CLAUDE.md` + 本文件 + `docs/architecture.md` (八条铁律) + `docs/lessons_learned.md` (16 条).
**SessionStart hook 自动注入铁律 + 近期 lessons + 完成自检**, 不靠人提醒.

**用户身份**: 持牌教育机构 — 合规非阻塞.

---

## 总目标

把"枯燥教材" 拆细打碎重组成"符合年轻人习惯的内容", 不偏离学校 (单词/语法/进度), 围绕**辽宁高考特点** (新课标 II 卷, 听 30+笔 120), 兼顾趣味性, 最终产出**后端 + HTML 前端教学+作业+知识图谱+条件组卷系统**, 推进到**可交付内部运营**.

---

## 当前阶段: 第四阶段 — 真问题修 + 真部署 + 真用

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

## 第五阶段 — 统一教学系统 (用户 2026-05-24 架构重构)

> **诊断**: 我之前错把项目做成 3 个独立 HTML 端 (`/` / `/teacher` / `/student`), 用户原话:
> "应该就是一个教学系统, 用于小班教学, 可以做成不同的标签".
> 删 3 端独立结构, 改 `/app` 单入口 + 内部 tab.
>
> **另一缺口**: 教学内容没真做 — 只有 graph 查询 + 教案 API, 缺**30 节课时的具体课程方案**.

### 5.1 统一 UI 架构 (P0)

| 改 | 当前 | 目标 |
|---|---|---|
| 入口 | 3 个独立 HTML (`/` 概览, `/teacher` 5 tab, `/student` 答题) | 1 个 `/app` SPA 入口 |
| 导航 | 顶部 nav-inline 3 链接, 3 套 css | 左侧固定 sidebar, 7 tab 切换 (复用 teacher 的 sidebar 模式) |
| tab 设计 | 没有 | (见 §5.2) |
| 共享逻辑 | common.js 已做 | 升级为 SPA router (hash-based, 零依赖) |
| 清理 | `/` `/teacher` `/student` 3 路由 | 3 路由保留为别名 (向后兼容), 主入口 `/app` |

### 5.2 七个 tab 设计

| tab | 用途 | 接口 |
|---|---|---|
| **A. 工作台** | 今日待办: 上次进度 / 待批改试卷 / 学生异常预警 / 数据健康 | /api/stats /api/audit /workbench/today |
| **B. 教学** ⭐ | 30 节课程 — 选课节 → 查讲义 / 教材原文 / 课件 / 出题 | /api/course/{list,session,materials} (新) |
| **C. 题库 + 组卷** | 现有 qbank + compose 合并到一 tab | /api/qb/* /api/paper/* |
| **D. 数据管理** | 全部 14 数据集 + 审计 + lineage 编辑 | /api/stats /api/audit /api/manifest |
| **E. 学生档案** | 学生 CRUD + 班级 + 答题历史 + 弱点 | /api/students/* (新) |
| **F. 知识图谱** | force-directed + 热力图 + 趋势 + 跨版本对照 | 现有 graph/recommend/trend |
| **G. 扫描 OCR** | POST 上传 + 显示已上传清单 + OCR review 队列 | /api/scan/* (POST 已通) |

### 5.3 教学内容: 30 节课程方案 (P0, 核心交付) ⭐

**spec**: 高三冲刺 / 高二复习用. 30 节, 每节 2 小时 = 120 min, 总 60 小时.

按高考占比 + 趋势模型 分配:

| 主题板块 | 节数 | 占比 | 趋势依据 |
|---|---|---|---|
| 词汇专题 (高频核心 + HV_extra) | 8 | 27% | vocab_growth +99.57/y, HV_extra 287 词 |
| 语法专题 (按 grammar_exam_4q core 排) | 6 | 20% | 14 顶级语法类目, core 优先 |
| 阅读理解 (主题分群 + 题型) | 6 | 20% | slope +0.028/y, 41% 占比 |
| 完形填空 + 七选五 | 3 | 10% | slope +0.011/y |
| 语法填空 (词形变形 + 时态) | 2 | 7% | slope +0.008/y |
| 应用文写作 (邀请/通知/求职等) | 2 | 7% | 15 分 |
| 读后续写 (叙事性教材文 + 模板) | 2 | 7% | 25 分, 新高考最大 delta |
| 模拟卷讲评 | 1 | 3% | 真题重组 |

**每节课时结构** (120 min):

```
0-20 min   开场 + 上节复习 (5 题 quick check, 抽自 question_bank)
20-50 min  核心教学 (词/语法/篇)
50-70 min  真题溯源 + 趋势提示 (从 lesson_plan API 拉)
70-90 min  课堂练习 (compose 3-5 题, 题型/难度 匹配本节)
90-110 min 重点解析 + 易错点
110-120 min 总结 + 下节预告 + 课后作业 (compose 10 题)
```

### 5.4 课程 schema (P0)

新表:

```sql
courses              -- 30 节课程定义
  course_id (1..30)
  title                  eg "高频核心词冲刺 (1) — A-D 字母段"
  block_kind             vocab|grammar|reading|cloze|gramfill|applied|narrative|mock
  block_order            1..30
  duration_min           120
  target_audience        "高二复习"|"高三冲刺"
  description            老师视角说明

course_materials     -- 每节自动 + 手动 关联 graph 实体
  course_id
  kind                   word|grammar|phrase|exam_question|reading_section
  ref_id                 → nodes.concept_id 或 qb_id
  source                 "auto_from_trend"|"manual"|"from_lesson_plan"
  reason                 eg "近 3 年真题 freq=5, exam_status=core"
  position               (建议讲解顺序)

course_sessions      -- 实际授课记录 (老师标的)
  session_id
  course_id
  class_id
  taught_at
  notes                  老师课后笔记
```

### 5.5 课程内容自动生成 service (P0)

新 service `backend/services/course/`:
- `templates.py` — 30 节课程的硬编码 spec (主题/板块/顺序)
- `materials.py` — 每节自动拉 materials (graph 查 + trend 推 + question_bank 抽)
- `handout.py` — 每节生成讲义 (md + html), 含
  - 核心知识点 (词/语法/句型, 带定义 + 例句)
  - 真题溯源 (近年 N 题, 题号 + 年份 + 题型)
  - 趋势提示 (本知识点 5 年频次曲线)
  - 课堂练习 (compose 3-5 题)
  - 课后作业 (compose 10 题)
- `lesson_plan_full.py` — 升级现有 lesson_plan 支持课程语义

### 5.6 学生档案 tab (P1)

补 4.7.D/E 没做的:
- 学生 CRUD (现 schema 通, 缺 UI)
- 班级 + 学生关联
- 答题历史 timeline
- 弱点 heatmap (按 word/grammar 4 象限)
- 弱点 → 推送 (该学生应该补哪节课的哪段)

### 5.7 验收门

1. ✅ `/app` 单入口, 7 tab 全可点击切换 (向后兼容旧 3 路由)
2. ✅ `courses` 表 30 行真课程 (非测试 stub)
3. ✅ 每节 course_materials ≥ 10 行 (auto + manual 混)
4. ✅ 任一节能生成完整讲义 (md + html, 含真题溯源 + 趋势 + 练习)
5. ✅ 学生档案 tab CRUD 跑通 + 至少 1 个班 5 学生 demo 数据
6. ✅ 0 FAIL audit 持续
7. ✅ 老师双击 `start.command` 30 秒内能看到 7 tab 切换流畅

---

## 后续阶段 (运营稳后, 用户拍前不做)

| 阶段 | 内容 | 触发 |
|---|---|---|
| 6 | LLM 增强 (Claude API): cloze 干扰项升级 / phrase 真考点抽 / 趣味化改写 | 老师反馈"题目质量" 强信号 |
| 7 | 难度梯度 sklearn (基于学生答题日志) | 4.7 student_answers ≥ 1000 行 |
| 8 | 跨学科扩展 (语文/数学) | 英语稳定运营 ≥ 1 学期 |
| 9 | 第二城市 / 多校多班级 | 单校跑稳 |

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
