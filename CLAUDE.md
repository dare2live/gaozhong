# CLAUDE.md — gaozhong 项目工程规则

> 配 `goal.md` 使用. 新 session 先读 goal.md + 本文件.

沈阳/辽宁高中英语教学系统. 当前阶段: **STEP 1 资料基石** (后续 STEP 全部 blocked by 基石 gate).

参考姊妹项目 `~/Documents/M/gaokao/` (辽宁高考真题研判) 的工程纪律, 部分原则继承.

---

## 0. 顶层架构与"单一计算点"铁律 (硬约束)

任何代码 PR 都先读 `docs/architecture.md` §0-§4 + `docs/knowledge_graph.md`. 三条铁律:

- **Rule 1 单一计算点**: 派生事实只在 `backend/services/` 算一次入表 / view. **API / 前端 / 脚本不准重写同样的 JOIN/agg**.
- **Rule 2 Canonical Model First**: 任何 entity 先有 PK 表, 再谈关联.
- **Rule 3 Edges 是一等公民**: N:M 关系全走 `edges` 表 + `services/graph/`, 不塞 JSON 字段, 不到处写 SQL JOIN.

违反 = 拒收. 任何"为了快 inline 一下" = 后期重构债.

## 0.5 改代码前先 codegraph + complexity (用户 2026-05-23 硬约束)

- 项目装了 PreToolUse hook (`scripts/precode_review_hook.sh`, 注册在 `.claude/settings.local.json`).
- 改 `backend/services/*` `backend/db/*` `backend/api/*` `scripts/init_db.py` `scripts/extract_*.py` 前, hook 会 stderr 提醒文件复杂度 + fan-in + 阈值.
- 当 hook 输出 `>> 建议先跑 /codegraph-architecture-audit`, 必须先跑再继续改.
- 触发阈值: 行数 >250 / 函数+类 >15 / fan-in >3.
- 全局 codegraph skill (`/codegraph-architecture-audit`) 不可用时降级 rg + import 扫描 (skill 自带 fallback).
- complexity-optimizer 用 stdlib ast 自实现 (`scripts/lib/complexity_check.py`, 零新增依赖), 算 cyclomatic complexity. hook 已集成 — CC>10 函数 ≥ 3 个会强提示 codegraph. 单独跑: `python3 scripts/lib/complexity_check.py <file.py>`.

不要等"重构完再 review", 要"改前先 review", 避免后期大规模重构.

## 1. 思维原则 (继承 gaokao §1)

### 1.1 数据基石优先
- STEP 1 (教材+课标+真题对齐) 前**任何模型/RAG/前端/趣味内容生成都是降级话题**.
- "上 LLM 多快" 的冲动 = 违反基石, push back 回资料源.

### 1.2 不偏离学校 (项目硬约束)
- 用户原话: "单词量、语法、教学方向等不要偏离学校的方向, 因为毕竟是要参加高考的".
- 任何 STEP 4 趣味化内容必须能反证 "词量在 ≤ 已学单元 + 课标 3500 词" + "语法点在 ≤ 已学单元".
- 任何"创新教法" 推荐前先答: "这破坏了教材进度对齐吗? 偏离了考点吗?"

### 1.3 真实数据 / 不估算
- 任何"覆盖率/匹配度 X%" 必能答 "哪 N 单元 / 哪 N 真题".
- 不准 "差不多" "应该" "估计" — 答不出就标 `unknown`, 不硬填.

### 1.4 基础事实显式 verify (继承 gaokao §1.7)
- 教材版本 / 卷型 / 题型分值 必须 ≥ 2 独立源, 单源不入 goal.md.
- 反例参考: gaokao 2026-05-22 假设辽宁用新高考 I 卷, 实际是 II 卷, 5 个 session 白跑.

### 1.5 失败先承认
- 拿不到的官方源明说 (e.g. jyt.ln.gov.cn 反爬), 不"估计"凑数.
- 不靠 try/except: pass 静默吃错误.

---

## 2. 接手前 First Actions

1. 读 `goal.md` + 本文件.
2. `git status --short` (项目已 git init).
3. 跑 `find data -type f | head -20` 看资料基石现状.
4. 大改前 commit 当前 state.

---

## 3. 资料管理红线

### 3.1 PIT (Point-in-Time) 对齐
教材版本会换 (2019 新版前是 2003 旧版). 任何"对齐高考真题" 的分析必须按**那一年生效的教材版本**对齐, 不能拿 2024 新版对齐 2018 真题.

| 错例 | 正解 |
|---|---|
| 用 2019 新版教材对齐 2017 真题 | 2017 真题对齐 2003 旧版人教 |
| 全量真题混合分析 | 按教材换代节点分段 (2003 旧版 / 2019 新版) |

### 3.2 来源可信度分层

| 层 | 来源 | 用法 |
|---|---|---|
| Truth (S) | 教育部 MoE / 辽宁省教育厅 公告 + 官方 PDF | 最终校验 |
| High (A) | TapXWorld/ChinaTextbook (人教/外研社原版 PDF 扫描) | 主用 |
| Mid (B) | 沈阳市教育局公告 + 民间教材聚合 (textbook-info) | 辅助 |
| Low (C) | LLM 拆出来的"知识点" | 必经教师/双模型校验 |
| Banned | 模拟题 / 押题 / 教辅"猜题" | 不入仓 |

### 3.3 文件命名 + lineage
- 教材 PDF: `data/textbooks/<版本短名>/{bixiu_N,xuanze_N}.pdf` (e.g. `waiyan/bixiu_1.pdf`)
- 课标 PDF: `data/curriculum/national/...` (MoE 官方 zip 解压, 21 学科 + 课程方案)
- 任何下载文件必须能从 manifest 倒查回原始 URL + sha256 (待写 `scripts/build_manifest.py`)

### 3.4 git LFS
- 单文件 > 100 MB → git LFS, 不直接 commit (GitHub raw 上限).
- 当前北师大版分了 .pdf.1 .pdf.2, 下载脚本已 cat 合并, 但本仓 commit 时仍要走 LFS.

---

## 4. 辽宁主用版本 (锚定)

辽宁省 14 地市只用 2 个版本, 其它版本不入仓.

| 版本 | 文件 | 在辽宁使用 |
|---|---|---|
| 外研社版-外语教学与研究出版社 (2019 新版) | `data/textbooks/waiyan/` | 10 市 (含沈阳/大连/鞍山等) |
| 人教版-人民教育出版社 (2019 新版) | `data/textbooks/renjiao/` | 4 市 (锦州/铁岭/朝阳/葫芦岛) |
| 全国课标 | `data/curriculum/national/.../4.普通高中英语课程标准（2017年版2020年修订）.pdf` | 全国 |
| 真题来源 | `~/Documents/M/gaokao/` (新课标 II 卷) | 辽宁 |

不入仓: 北师大/译林/沪教/沪外教/冀教/重庆大学 (用户 2026-05-23 明确"只要辽宁在用").

跨版本对照 (外研 vs 人教 同主题) 是 STEP 3 的事, 不在 STEP 1 范围.

---

## 5. STEP 1 验收门 (gate)

全绿才能开 STEP 2:
- [ ] 8 个版本教材 PDF 全下完 + sha256 manifest
- [ ] 21 科课标 + 课程方案 PDF 完整 (英语必到)
- [ ] 辽宁省 2024-2025 教学用书目录原文 (jyt.ln.gov.cn) 至少 1 份缓存
- [ ] 沈阳市教育局官方选用版本印证 ≥ 1 (现仅民间聚合)
- [ ] 高考英语命题概览 (题型/分值/年代变化) 入 `docs/exam_overview_liaoning.md`
- [ ] 结构化词汇/课文资源至少 1 个 repo 入仓
- [ ] git init + 完整 commit + README/goal.md

---

## 6. 与姊妹项目 gaokao 的边界

- `~/Documents/M/gaokao/` 负责 **真题侧**: 题型分布 / 命题点 / 答题数据 / PIT 对齐.
- `~/Documents/M/gaozhong/` (本项目) 负责 **教材侧**: 课文拆解 / 词表 / 语法点 / 趣味化.
- 两边交汇点: **知识点 ↔ 真题考点 映射表** (STEP 3, 双向引用).
- 不要在本项目重复抓真题 PDF.
- **DuckDB 完全独立**, 不 ATTACH 不混用 (用户 2026-05-23 硬约束).

## 7. 辽宁卷锚定 (用户 2026-05-23 再次强调)

- 本项目真题数据范围 = **辽宁卷** (新课标 II 卷, 2021 起辽宁正式启用).
- 早期真题 (2010-2020) 辽宁卷型在 GAOKAO-Bench 不一定显式标省, 镜像后必须 **加 province 过滤层** (`backend/services/extraction/exam.py` 输出 province / 卷型 元数据, 入 `exam_questions.province` 字段).
- 不直接拿"全国卷"分析当成"辽宁卷分析" — 见姊妹项目 gaokao R2 反例 (2026-05-22 假设辽宁用 I 卷, 实际是 II 卷, 5 个 session 白跑).
- 任何"题型分布 / 命题点" 报告必须先 province=辽宁 / 卷型 ∈ {新课标 II 卷, 2020 前对应辽宁实际卷型} 过滤.

---

## 7. 待写 / 占位

- [ ] `scripts/build_manifest.py` (sha256 + URL lineage, 借 gaokao `pull_official_pdfs.py` 风格)
- [ ] `scripts/extract_textbook_taxonomy.py` (PDF → 单元/语篇/词表)
- [ ] `backend/config/sources.yaml` (集中管 PDF + repo 源)
- [ ] STEP 2 设计文档 (PDF 拆解的双校验策略)
