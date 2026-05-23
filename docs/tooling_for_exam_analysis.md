# 高考英语精细化学习与趋势工具选型 (2026-05-23)

> 用户 2026-05-23: "不一定非的是 Optuna, 你可以先研究一下哪些工具更适合本项目的这个精细化学习高考试卷然后进行预测的功能".

## 核心问题

不是"押题预测" (gaokao 项目宪法 §3.3 banned), 是:
1. **历年趋势识别** — 词/语法/主题/题型在历年真题中的频次和变化
2. **教学优先级建议** — 基于"已学 + 高频考点" 给学生个性化路径
3. **作业组合参数** — 单元/阶段/模拟卷的题型分布、难度梯度组合

---

## 工具栈选型 (按必要性排序)

### A. 已用 / 必要 (本项目核心)
| 工具 | 用途 | 备注 |
|---|---|---|
| **DuckDB** | 主存储, JOIN, 聚合 | 单文件, 跨平台, 与 gaokao 独立 |
| **pypdf** | PDF 文本 + outline 抽取 | 实测两版教材均可文本化, 不需 OCR |
| **stdlib (re/json/ast/http.server)** | 文本处理 / API / 复杂度审计 | 0 新增依赖 |

### B. 趋势统计 (推荐扩, 低门槛)
| 工具 | 用途 | 装or不装 |
|---|---|---|
| **scikit-learn** | TF-IDF 文本特征 / 简单线性回归 / 朴素贝叶斯分类 | 推荐 — 题型分布年趋势 / 词频排名 |
| **statsmodels** | 时间序列 (ARIMA 等) | 可选 — 13 年数据短, 简单移动平均够 |
| **numpy + pandas** | 矩阵 + DataFrame | 推荐 — DuckDB 替代 + 兼容 sklearn |
| **rapidfuzz** | 模糊字符串匹配 | 可选 — 题面找同义词 / 主题词关联 |

### C. 知识图谱 / 图算法
| 工具 | 用途 | 装or不装 |
|---|---|---|
| **networkx** | community detection / centrality / shortest path | 推荐 — 找"知识枢纽词" |
| **igraph** | 同上 但更快 | 不需 — 我们 < 10k 节点 networkx 够 |
| **Neo4j / Cypher** | 大规模图查询 | 不需 — DuckDB + edges 表已胜任 |

### D. 题难度 / 学生模型 (STEP 6)
| 工具 | 用途 | 装or不装 |
|---|---|---|
| **pyirt / py-irt** | Item Response Theory (题难度 + 学生能力) | 推荐 — 但需先收集学生答题日志 (M5+) |
| **简单 logistic 回归** | 题答对率 ~ 词频/语法点级别 | sklearn 已含 |

### E. LLM (合成题 / 抽考点, S3+/S4) — 待用户授权
| 工具 | 用途 | 备注 |
|---|---|---|
| **anthropic Claude API** | 抽题考点 / 合成趣味题 / 越纲判 | 需 API key 用户授权 |
| **dual-model 投票** | 两个 LLM 抽, 取交集 ≥ 0.7 κ | docs/step2_extraction_plan.md P5 |

### F. **不建议装** (避免过度工程)
| 工具 | 理由 |
|---|---|
| **Optuna** | 本项目寻优场景简单, scipy.optimize 够; Optuna 适合 ML 超参 (eg 学生模型调参), 现阶段没那种场景 |
| **PyTorch / TF** | 没本地训练需求 |
| **spaCy** | 英文 token 简单 regex 已够, 引入 ~ 500MB 模型不值 |
| **gensim** | 词向量 word2vec 可用 sklearn TruncatedSVD 替代 |

---

## 项目当前实现 vs 上述工具的 fit

| 已实现 (零依赖) | 替代方案 (若用上述工具) |
|---|---|
| `backend/services/trend.py` 词频统计 | sklearn CountVectorizer (相同结果) |
| `backend/services/audit/exam_coverage.py` 4 象限 | sklearn `intersection` (同)  |
| `backend/services/graph.py` BFS expand | networkx `single_source_bfs` (更快) |
| `scripts/lib/complexity_check.py` ast CC | radon (相同结果) |
| 干扰项随机抽 (`exercise/poc.py`) | scipy.optimize 多约束组合 (更优) |

→ MVP 阶段**全部用 stdlib + duckdb + pypdf**, 性能 OK, 可解释性最强.
   当数据量 / 复杂度增长 (eg M5 学生模型 + 个性化路径), 才引 sklearn + networkx + pyirt.

---

## 外部资料源 (用户 2026-05-23: 结合官方+非官方解读)

| 来源 | 类型 | 说明 |
|---|---|---|
| **教育部考试中心** | 官方 | 《中国高考报告》《高考评价体系说明》(年发) |
| **教育部 ictr.edu.cn** | 官方 | 课程标准 + 解读 (已入仓课标 22 PDF) |
| 辽宁省教育研究院 | 官方 | 辽宁卷年度命题分析 (需逐年抓) |
| 学科网 zxxk.com | 商业 | 真题 + 命题解读 (注意版权) |
| 中国教育在线 / 新东方 | 民间 | 每年高考分析文章, 趋势提示 |
| 知乎专栏 高考英语 | 民间 | 教师 / 学者自发解读 |
| 北师大 flts.bnu.edu.cn | 学术 | 《中小学外语教学》(月刊), 命题研究论文 |

**入仓策略**:
1. 官方 PDF (考试中心) — 入 `data/curriculum/official_interpretation/`
2. 学术论文 (PDF/HTML) — 入 `data/curriculum/academic_interpretation/`
3. 民间专栏 (HTML) — 入 `data/curriculum/community_interpretation/`, 标 lineage L2-L3
4. **不直接采用 "押题"** 类内容 — banned

后续可加 `backend/services/audit/interpretation_alignment.py` 检查"教学侧设计 ↔ 官方解读" 是否一致.

---

## 推荐下一步

1. **暂不装新工具** — 继续 stdlib + duckdb 完成 M3/M4/M5
2. **加 5 个官方+学术 PDF 入仓** (跨年度命题解读), 作 STEP 3.5 任务
3. M5+ 引入 sklearn/networkx 时再装, 写入 requirements.txt
