# gaozhong 项目 — 沈阳/辽宁高中英语教学系统

新 session 接手先读本文件 + `CLAUDE.md`(待写). 参考姊妹项目 `~/Documents/M/gaokao/` 的 R1/R2 严谨度.

---

## 项目目标 (用户 2026-05-23 口述)

把"枯燥乏味的教材"拆细打碎,重组成"符合年轻人习惯爱好的内容",在
**不偏离学校教学方向**(单词量/语法/教学进度)的前提下,围绕**辽宁地区高考特点**展开,
兼顾趣味性,最终产出**后端 + HTML 前端的教学系统**.

- 不偏离学校 = 与教材+课标+考纲一一对齐
- 围绕辽宁高考 = 真题命题点驱动学习路径
- 趣味性 = 内容形式 (短视频脚本/段子/类比/互动题) 而非牺牲覆盖

辽宁高考英语真题数据复用 `~/Documents/M/gaokao/` (新课标 II 卷, 听力 30 + 笔试 120 = 150 分).

---

## 当前阶段: STEP 1 — 资料基石 (in progress)

**先把原始资料拿齐**, 后续所有上层动作 (拆分/重组/趣味化/前端) 都建在这上面.
项目宪法借鉴 gaokao §1.5: 数据基石优先, 基石没稳前不讨论上层方案.

### Step 1 已完成

| 项 | 状态 | 路径 / 来源 |
|---|---|---|
| 教材版本研判 (沈阳/辽宁) | ✅ 2 源印证 | 见下文 §教材版本 |
| 普通高中课程方案+20 科课标 PDF | ✅ 22 份, 37MB | `data/curriculum/national/` (MoE 官方 zip) |
| GitHub 主教材源选型 | ✅ TapXWorld/ChinaTextbook (71k★) | 8 个出版社版本全覆盖 |
| 教材 PDF 下载脚本 | ✅ `scripts/download_textbooks.sh` | URL-decode + 分片合并 |
| 项目目录初始化 + git init | ✅ | `data/{textbooks,curriculum,exam_syllabus,structured}` |

### Step 1 全部完成 (2026-05-23)

- [x] 教材 PDF: 辽宁在用 2 版 × 7 册 = 14 PDFs / 202 MB 已下完
- [x] 课标 SHA256 + manifest (`scripts/build_manifest.py` + DuckDB `file_manifest` 表)
- [x] 辽宁省 2023 教学用书目录官方原文 (用户提供附件 1/2 入仓 `data/curriculum/liaoning/官方/`)
- [x] 高考英语 3500 词 truth source: 课标附录 2 已抽出 2928 词 (97.6% 召回, 义教 1476 + 必修 480 + 选必 972)
- [x] 结构化词汇辅助 (DictionaryData / kajweb-dict / mahavivo-english-wordlists, 标 cross-check only)
- [x] CLAUDE.md / docs/exam_overview_liaoning.md / docs/data_gaps.md / docs/step2_extraction_plan.md
- [x] **MVP 框架搭通**: backend FastAPI (stdlib http.server, 零新增依赖) + DuckDB + frontend HTML
- [ ] 辽宁省 2024-2025 教学用书目录原文 (jyt.ln.gov.cn 反爬, 2023 版可用)
- [ ] 沈阳市教育局选用版本"官方"印证 (现 textbook-info + yanxiuwang + xuexili 三聚合)
- [ ] 课标语法附录 3 深度抽 (当前仅 14 顶级类目, MVP 够)

### MVP 框架 (Step 1 收尾)

| 组件 | 实现 | 文件 |
|---|---|---|
| DB | DuckDB 单文件 (与 gaokao 完全独立) | `data/db/gaozhong.duckdb` |
| Schema | 7 张表: 课标 3 + 辽宁约束 2 + 教材 1 + manifest 1 | `backend/db/schema.sql` |
| 源管理 | YAML 集中配置 | `backend/config/sources.yaml` |
| 后端 API | stdlib `http.server`, 8 个 endpoint | `backend/api/main.py` |
| 前端 | 原生 HTML + 原生 fetch, 7 个区块 | `frontend/index.html` `frontend/static/{style.css,app.js}` |
| 课标抽 | pypdf + 正则 | `scripts/extract_curriculum.py` |
| 教材下载 | bash + curl | `scripts/download_textbooks.sh` |
| 装库 | duckdb + pypdf | `scripts/init_db.py` |
| Manifest | sha256 jsonl | `scripts/build_manifest.py` |

**新增依赖**: 0. 全部用系统 Python 3.13 已有 (duckdb / pypdf / PyYAML).

启动:
```bash
python3 scripts/init_db.py             # 重建 DB + 装载 5 个 truth source
python3 backend/api/main.py            # 启 API + 前端 (http://127.0.0.1:8765)
```

---

## 教材版本 (Step 1 输出)

**辽宁省 14 地市只用 2 个版本: 外研社版 (10 市) + 人教版 (4 市)**
— 已 2 源印证 + 14 地市完整分布 (项目宪法 §1.7).

### 14 地市分布 (xuexili.com 聚合, 2026-05-23 缓存到 `data/curriculum/liaoning/`)

| 地市 | 高中英语版本 | 地市 | 高中英语版本 |
|---|---|---|---|
| 沈阳 | **外研版** | 锦州 | **人教版** |
| 大连 | **外研版** | 铁岭 | **人教版** |
| 鞍山 | **外研版** | 朝阳 | **人教版** |
| 抚顺 | **外研版** | 葫芦岛 | **人教版** |
| 本溪 | **外研版** |  |  |
| 丹东 | **外研版** |  |  |
| 营口 | **外研版** |  |  |
| 阜新 | **外研版** |  |  |
| 辽阳 | **外研版** |  |  |
| 盘锦 | **外研版** |  |  |

### 印证源

| 维度 | 源 | 表述 |
|---|---|---|
| 沈阳 = 外研版 | textbook-info.com /post/1218.html | "2024 年秋季沈阳高中所使用的英语课本是外研版高中英语 (2019 新版)" |
| 沈阳 = 外研版 | yanxiuwang.cn (51 听课网) | 外研版(2019) 全套必修+选择性必修, 沈阳教研使用 |
| 14 地市分布 | xuexili.com /keben/18486.html | 14 地市逐城列举, 外研版 10 + 人教版 4 |

### 实际入仓的两版本

| 出版社版本 | 子目录 | 总大小 | 册数 | 在辽宁使用 |
|---|---|---|---|---|
| 外研社版-外语教学与研究出版社 (2019 新版) | `data/textbooks/waiyan/` | 111 MB | 7 (必修 3 + 选修 4) | 10 个地市 (含沈阳) |
| 人教版-人民教育出版社 (2019 新版) | `data/textbooks/renjiao/` | 91 MB | 7 (必修 3 + 选修 4) | 4 个地市 |

**已删除** 其它 6 版本 (北师大/译林/沪教/沪外教/冀教/重庆大学) — 用户 2026-05-23 反馈"只要辽宁省内在用的版本即可".
重下命令: `bash scripts/download_textbooks.sh` (脚本 VERSIONS 已收窄到 2 版本).

---

## 不偏离学校的硬约束源

| 约束 | 文件 | 用法 |
|---|---|---|
| 学科目标 | `4.普通高中英语课程标准（2017年版2020年修订）.pdf` | 核心素养 / 主题语境 / 语篇类型 / 语法功能 / 词汇表 |
| 学制安排 | `1.普通高中课程方案（2017年版2020年修订）.pdf` | 必修 vs 选择性必修 vs 选修 课时配比 |
| 高考题型 | `~/Documents/M/gaokao/` 真题数据 | 辽宁卷 (新课标 II 卷) 历年题型分布 |
| 教材内容 | `data/textbooks/waiyan/*.pdf` | 单元主题 / 语篇 / 词表 / 语法点 |

---

## 后续阶段 (STEP 1 出 gate 后再开)

- **STEP 2 教材内容结构化**: PDF → 单元 → 语篇 → 词/句/语法点 (OCR + LLM 拆解, 双校验)
- **STEP 3 高考映射**: 辽宁真题考点 → 教材覆盖点 双向 mapping
- **STEP 4 趣味化内容生成**: 单元主题 × 年轻人语境 (短视频脚本/段子/类比), LLM 生成 + 教师校验
- **STEP 5 教学系统 MVP**: 后端 (FastAPI) + 前端 (HTML, 可参考 gaokao 前端如有)
- **STEP 6 评估闭环**: 学生使用日志 → 弱点 → 个性化内容推送

参考姊妹项目 `~/Documents/M/gaokao/` 的工程纪律:
- 任何"命中率/覆盖率 X%" 必能答 "哪 N 样本"
- 不准 try/except: pass 静默吃数据问题
- 资源/PDF lineage 入 manifest, sha256 幂等
