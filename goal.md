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

### 5.0 模块化 / 可扩展 / 可维护 原则 (用户 2026-05-24 硬约束)

> 与 `docs/architecture.md` 8 条铁律 互补. 第五阶段所有新代码必须落到位.

| # | 原则 | 实现 |
|---|---|---|
| M1 | **三层严分** service / api / db, 不跨层调 | route 只接 qs + 调 service, service 只接 con + 返 dict, db 只放 schema 与 RW helper |
| M2 | **插件式 dispatch** block_kind / audit / scenario_kind / question_type 都用注册表 (dict[str, callable]), 禁 `if/elif` 长链 | `registry.register("vocab", handler)` + import 触发注册 |
| M3 | **数据外置** 30 节 templates / 主题池 / audit 阈值 / hook 阈值 → yaml/json, 不硬编 .py | `backend/config/{course_templates,theme_pool,audit_thresholds}.yaml` |
| M4 | **稳定 API** 字段不删不重命名, 加功能加新 endpoint | 已发 `/api/*` 进 `docs/api_contract.md` 锁住 |
| M5 | **每模块单测** service / audit / template 都带 `tests/` 同名文件 | smoke test 200 + 关键 assert ≥ 1 |
| M6 | **CC ≤ 10 默认** 新代码任一函数 CC>10 = Stop hook 阻塞 (当前 baseline 12, 不许涨) | `scripts/lib/complexity_check.py` 已集成 |
| M7 | **fan-in ≤ 5 默认** service 被引用 >5 处 = 拆 | codegraph audit (PreToolUse hook 已扫) |
| M8 | **零新增依赖** 全 stdlib + duckdb + pypdf + yaml; 引新库要 doc 解释为什么 | requirements.txt 锁定 |

**Baseline (2026-05-24, 改前)**: backend 17 file / 262 func / 12 CC>10 残留. 第五阶段结束应**不涨**.

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
| **C. 题库 + 组卷** | 现有 qbank + compose 合并到一 tab; **听力题统一入此 tab** (transcript + audio_id 字段) | /api/qb/* /api/paper/* /api/listening/* |
| **D. 数据管理** | 全部 14 数据集 + 审计 + lineage 编辑 | /api/stats /api/audit /api/manifest |
| **E. 学生档案** | 学生 CRUD + 班级 + 答题历史 + 弱点 | /api/students/* (新) |
| **F. 知识图谱** | force-directed + 热力图 + 趋势 + 跨版本对照 | 现有 graph/recommend/trend |
| **G. 扫描 OCR** | POST 上传 + 显示已上传清单 + OCR review 队列 | /api/scan/* (POST 已通) |

### 5.3 教学内容: 30 节课程方案 (P0, 核心交付) ⭐

**spec**: 高三冲刺 / 高二复习用. 30 节, 每节 2 小时 = 120 min, 总 60 小时.

#### 5.3.0 4 条铁律 (用户 2026-05-24 追加)

| 铁律 | 含义 | 实现 |
|---|---|---|
| **R1 知识点关联** | 每节讲完, 该词/语法 在 graph 中要联通 ≥3 个其他知识点 (同义/反义/词族/搭配/近义语法/相邻话题) | `course/relations.py` 自动从 nodes+edges 抽 + 写进讲义"关联拓展"段 |
| **R2 不抄教材** | 例句 / 阅读篇 / 情景 主题**不与教材重复**, 用真实/年轻话题 (见 §5.3.A) | `course/scenarios.py` 主题池 + audit 校验"无教材原句重叠" |
| **R3 多场景** | 同一知识点至少在 **3 个不同场景** 出现 (eg "describe" 出现在: 体育解说 / vlog 评论 / 求职 self-intro) | `course/scenarios.py` 给每个知识点配 ≥3 场景 |
| **R4 作业 ↔ 知识点闭环** | 每节 10 道作业题, **100% 命中本节知识点** (作业题 tag ⊆ 本节知识点 tag) | `course/homework.py` + `audit_homework_alignment` 阻塞 |

#### 5.3.A 30 个新鲜主题池 (替代教材原主题, 教育/学术/正向导向)

> 用户 2026-05-24: "短视频啥的不要设计". 删娱乐流量类 (短视频/网红/弹幕/虚拟偶像/翻译梗), 换学术/科普/职业/社会议题, 贴合高考阅读的真实选材风格.

| 类别 | 主题 (5 个) |
|---|---|
| 科技 | AI 辅助科研 / 自动驾驶伦理 / 量子计算入门 / 脑机接口 / 5G 农业应用 |
| 学术 | STEM 跨学科 / 田野调查方法 / 学术写作规范 / 学科前沿讲座 / 学术诚信 |
| 环境 | 海洋塑料治理 / 城市绿地 / 碳中和路径 / 候鸟迁徙 / 极地冰川变化 |
| 社会 | 老龄化社会 / 乡村振兴 / 极地科考 / 全球公共卫生 / 一带一路合作 |
| 心理 | 时间管理 / 高考压力调节 / 友谊重构 / 学习动机 / 拖延克服 |
| 文化 | 国潮汉服 / 博物馆热 / 非遗传承 / 跨文化交流 / 茶道与礼仪 |
| 职业 | 青年企业家 / 数字游民 / 远程办公 / 实习生日记 / 人机协作 |
| 旅行 | 露营复兴 / city walk / 哈尔滨冰雪季 / 沙漠星空 / 游学之旅 |
| 体育 | 电竞奥运 / 滑板入奥 / 女足世界杯 / 户外攀岩 / 体育精神 |
| 校园 | 选科困惑 / 走班制 / 社团竞选 / 自习室文化 / 校园食安 |

> 每节课从对应主题池抽 1 主选 + 2-3 副选 (R3 多场景). 教材的 unit 主题作为"参考来源", 不直接 copy.
> 主题池外置 `backend/config/theme_pool.yaml` (M3), 不硬编码.

#### 5.3.B 每节课时结构 (120 min)

```
0-15 min   开场: 趣味 hook (短视频/新闻片段/段子 — 主题导入)
15-25 min  上节复习: 5 题 quick check (抽自上节作业的同 tag)
25-50 min  核心教学: 词/语法/句型 (主场景 + 关联拓展 ≥3 个相关点 = R1)
50-70 min  真题溯源: 近 5 年真题中该知识点 N 题 + 趋势曲线
70-90 min  场景练习: 同知识点 3 个不同场景 (R3) 各 1-2 题 (compose)
90-105 min 重点解析 + 易错点 (从历史 student_weakness 抽)
105-115 min 总结 + 下节预告 (主题预告, 制造期待)
115-120 min 课后作业: 10 题, tag ⊆ 本节 (R4 强校验)
```

#### 5.3.C 30 节课程编排 (示例 5 节, 其余落外置 yaml)

| # | 主题板块 | 核心知识点 | 主选场景 | 关联拓展 (≥3) |
|---|---|---|---|---|
| 1 | 词汇·高频形容词 1 | adequate, ambiguous, arbitrary, authentic | AI 辅助科研结果是否 authentic | adj 词族 (-ly 副词) / 反义 (genuine/fake) / 搭配 (an ~ source) |
| 2 | 语法·宾从陈述 vs 疑问 | that/whether/if + 时态呼应 | 青年企业家访谈引述 | 主从复合句联通 / 名词从语类 / 间接引语 |
| 3 | 阅读·议论文 main idea | 论点-论据-反驳结构 | 乡村振兴政策辩论 | 完形议论篇 / 续写转折 / 应用文倡议书 |
| 4 | 完形·语境推断 | 上下文同义/反义提示 | 极地科考长文 | 阅读细节题 / 七选五连贯 / 词汇辨析 |
| 5 | 续写·情绪转折 | so... that / 倒装强调 | 滑板入奥失败到逆袭 | 倒装语法 / 情绪词族 / 叙事时态 |

完整 30 节: `backend/config/course_templates.yaml` (M3 数据外置), 含 course_id/title/block_kind/themes/related_concepts/homework_tags/listening_required.

### 5.4 schema (P0)

#### 5.4.A 课程 3 新表

```sql
courses              -- 30 节课程定义 (源自 course_templates.yaml, init_db 灌)
  course_id (1..30)
  title                  eg "高频核心词冲刺 (1) — A-D 字母段"
  block_kind             vocab|grammar|reading|cloze|gramfill|applied|narrative|mock|listening
  block_order            1..30
  duration_min           120
  target_audience        "高二复习"|"高三冲刺"
  listening_required     bool          -- 含听力练习的节
  description            老师视角说明

course_materials     -- 每节自动 + 手动 关联 graph 实体 / 题
  course_id
  kind                   word|grammar|phrase|exam_question|reading_section|listening_clip
  ref_id                 → nodes.concept_id 或 qb_id
  source                 "auto_from_trend"|"manual"|"from_lesson_plan"|"from_scenario"
  reason                 eg "近 3 年真题 freq=5, exam_status=core"
  position               (建议讲解顺序)

course_sessions      -- 实际授课记录 (老师标的)
  session_id
  course_id
  class_id
  taught_at
  notes                  老师课后笔记
```

#### 5.4.B question_bank 扩字段 (听力题统一入题库, 不另起表)

```sql
ALTER TABLE qb_questions ADD COLUMN has_audio       BOOLEAN  DEFAULT false;
ALTER TABLE qb_questions ADD COLUMN audio_id        VARCHAR;          -- "audio:2024/A/Q1" lineage
ALTER TABLE qb_questions ADD COLUMN transcript      TEXT;             -- 听力文字稿 (必填 if has_audio)
ALTER TABLE qb_questions ADD COLUMN audio_speakers  JSON;             -- [{"id":"M","label":"男1"}, ...]
ALTER TABLE qb_questions ADD COLUMN audio_duration  INTEGER;          -- 秒
-- 题型扩枚举: listening_short | listening_dialog | listening_passage
```

audit:
- `audit_listening_transcript_required`: 凡 has_audio=true 必须 transcript ≥ 50 字符
- `audit_listening_in_qbank`: 不存在"独立听力表", 全 join qb_questions

### 5.5 课程内容自动生成 service (P0)

新 service `backend/services/course/`:

| 模块 | 作用 | 对应铁律 |
|---|---|---|
| `registry.py` | 插件式 dispatch (block_kind / scenario_kind / audit_kind 注册表) | M2 |
| `loader.py` | 从 `backend/config/*.yaml` 加载 templates/theme_pool/thresholds | M3 |
| `templates.py` | 30 节 spec 验证 + 暴露 (实数据走 yaml) | — |
| `relations.py` | 每节核心知识点 → 联通 ≥3 个其他 (从 nodes+edges) | **R1** |
| `scenarios.py` | 主题池 + 每知识点 ≥3 场景 + 教材原句重叠 audit | **R2 R3** |
| `materials.py` | 综合 (graph + trend + question_bank + scenarios) 生成 materials | — |
| `homework.py` | 抽 10 题作业, 强校验 题目 tag ⊆ 本节知识点 tag | **R4** |
| `handout.py` | 生成讲义 (md + html), 含 7 段: hook / 复习 / 核心 / 关联拓展 / 真题溯源 / 场景练习 / 作业 | — |
| `lesson_plan_full.py` | 升级现有 lesson_plan API 支持课程语义 (route 改一下) | — |

新 audit (Stop hook 加入):
- `audit_course_relations`: 每节关联 ≥3 (R1)
- `audit_course_no_textbook_copy`: 例句/阅读篇 与教材原句无 ≥10 词连续重叠 (R2)
- `audit_course_scenarios`: 每核心知识点 ≥3 场景 (R3)
- `audit_homework_alignment`: 每节作业 tag 100% ⊆ 本节 (R4)

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
4. ✅ 任一节能生成完整讲义 (md + html, 含 hook/复习/核心/关联/真题/场景/作业 7 段)
4a. ✅ R1: 每节关联 ≥3 (audit_course_relations)
4b. ✅ R2: 与教材无 ≥10 词连续重叠 (audit_course_no_textbook_copy)
4c. ✅ R3: 每核心知识点 ≥3 场景 (audit_course_scenarios)
4d. ✅ R4: 每节作业 tag 100% ⊆ 本节 (audit_homework_alignment)
4e. ✅ 听力题入 qb_questions (扩字段), 凡 has_audio=true 必有 transcript (audit_listening_transcript_required)
4f. ✅ 主题池 / templates / 阈值 全外置 yaml (M3), 0 硬编码
4g. ✅ CC>10 函数数 ≤ baseline 12, fan-in ≤ 5 (M6 M7)
4h. ✅ 每新模块带 `tests/test_*.py` smoke 200 (M5)
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
