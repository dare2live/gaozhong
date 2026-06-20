# 初中/中考入库 — 数据库模块化 + 分层管理设计 (2026-06-20)

> 用户 2026-06-20: "做好规划, 数据库分模块、分层管理"。配 k12_platform_master_design.md(单库决策) + architecture.md(八铁律) 用。
> architect-controller 出, **approve 后才动 init_db**。底图来自 understand 勘探 wf + schema.sql + init_db.py。

## 0. 目标 + 不可违 (Genesis)

把已验证的初中/中考 jsonl (curriculum_vocab 1661 / grammar 71 / hujiao 926 / stage_refined / 中考真题 90) 接进**同一个** `gaozhong.duckdb`, 使 K12 衔接(stage 维 + 中考考点 + 跨阶段边)可查、可服务、可视化。
**死亡线**: D0 100% 准(溯回课标/教材/真题) · 不混口径(沈阳中考≠辽宁高考≠全国; stage 各自 PIT) · 单一计算点(派生只算一次) · **隔离靠门+维度过滤, 非物理分库**(master §4)。

## 1. 数据库模块化 — 单库, 三个"模块判别维"

单库不等于混乱。用**三个正交判别维**把数据切成可独立查询的模块, 边界清晰:

| 判别维 | 列/位置 | 取值 | 隔离作用 |
|---|---|---|---|
| **node_type** | `nodes.node_type` | word / grammar / theme / exam_point / exam_question / word_sense(新) | 实体类型模块 |
| **stage** | `nodes.attrs_json.stage` | 小学 / 初中 / 高中必修 / 高中选修 / 义务教育 | **K12 阶段模块**(核心新维) |
| **exam_type** | `exam_questions.exam_type`(新列) | 中考 / 高考 / 校本测评 | 检验来源模块 |

**模块边界铁律**: 任何"只看初中"/"只看中考"的查询 = `WHERE stage IN ('小学','初中')` 或 `exam_type='中考'`, **不需要也不允许另开库**。跨阶段分析 = 同库 edges 一行(`deepens`/`expands_sense`)。

## 1.5 两大域: 共享知识图谱 vs 多租户学情 (用户 2026-06-20: 不同老师建不同学生档案, 学生各自产数据)

数据库**第一层切分不是初中/高中, 而是"共享 vs 多租户"两域** — 这决定隔离/权限/单算点:

| | **域A 共享知识图谱** | **域B 多租户学情** |
|---|---|---|
| 内容 | 课标/教材/真题/考点/word/grammar/stage (域§1-§2 的 nodes/edges/exam_questions) | teacher → class → student → answer → mistake → weakness |
| 谁拥有 | **全局唯一**, 所有老师共用 | **每个老师拥有自己那份** (按 teacher_id 隔离) |
| 读写 | init_db 建, 老师**只读** | 老师/学生**读写自己的** |
| 表 | nodes / edges / exam_questions / cefr_vocab ... | `teachers` / `classes(teacher_id)` / `students(class_id)` / `student_answers(student_id)` / `student_weakness(student_id)` / mistake(新) |
| 数据来源 | 官方 PDF 提取 (D0 100%) | **学生答题/老师录入** (天然增长, 非提取) |

**所有权链 (已在 schema, 实证)**: `teachers.teacher_id` ← `classes.teacher_id` ← `students.class_id` ← `student_answers.student_id` / `student_weakness.student_id`。即**老师建班→班里有学生→学生产答题/弱点**, 多租户已建模。

**隔离铁律 (新红线)**: 域B 任何查询/API **必带 `teacher_id` 作用域** — 老师 A 永不可见老师 B 的学生/数据。weakness/错题派生只在自己租户内算。**域A 无 teacher_id (全局共享), 域B 必有 (租户隔离)** = 判别一个表属哪域的单一标准。

**域间桥 (单一计算点)**: 域B 的 `student_answers.question_id` → 域A 的 `exam_questions/question 节点` → `tests_exam_point` 边 → **per-student weakness 派生** (`weakness/recompute_all`, 零 orphan)。即"学生错题 ⋈ 共享考点图谱 → 这个学生的薄弱真考点", 算一次入 `student_weakness`(域B)。

**现状 vs 目标**: 表已建, 但 ① 当前仅 5 demo 学生 seed ② API 未按 teacher_id 严格作用域 ③ 数据靠真实学生答题增长(待真实使用)。本设计**先把域A(知识图谱)入库做扎实**(初中/中考), 域B 多租户**作用域加固 + 析生页**待真实学生数据或单独增量(inc6)。

## 2. 分层架构 (6 层 + 3 门, 每层单一职责)

```
L1 真相源 (已验证 jsonl)        data/junior_high/structured/*.jsonl + exams/*/exam_questions.jsonl
      │  ← junior_accuracy_check 门 (F1-F9, 已绿)
L2 加载器层 (新, 模块化单算点)   backend/services/data_sources/extract/junior/   ← 独立子模块, 不混高中 loader
      │     ├ vocab.py    (curriculum_vocab + hujiao → word 节点行 + introduces 边行)
      │     ├ grammar.py  (grammar_items → grammar 节点行)
      │     ├ exam.py     (中考 exam_questions → exam_questions 行, exam_type=中考)
      │     └ stage.py    (stage_refined + 10维蓝图 → 跨阶段 deepens/expands 边行)
L3 Canonical 入库层 (单库)       nodes / edges / exam_questions  ← init_db 新增 "Layer 2x junior"
      │  ← data_accuracy_check._check_11_junior 门 (DB级: orphan/stage一致/exam_type一致)
L4 派生/服务层 (复用+少量新)     exam_point/loader · exam_vocab · trend(泛化按exam_type分段)
      │     + 新 stage.py(stage分布) + 新 k12_blueprint.py(10维蓝图 中考∩高考)
L5 API 层 (新, 薄)              /api/stage/distribution · /api/zhongkao/* · /api/k12/blueprint
L6 前端                        K12衔接页 (stage进度 + 10维语法蓝图矩阵)
门: junior_accuracy_check(L1/L2) ∧ data_accuracy_check._check_11(L3) ∧ moth ∧ stop_gate触发器认 junior 路径(坑21)
```

**分层职责单一**: L2 只产"行"不写库; L3 只写库不算派生; L4 只算派生读 edges; 三层不互相越界(铁律1 单一计算点)。

## 3. Schema 改动 (最小, 零破坏)

| 表 | 改动 | 风险 |
|---|---|---|
| `exam_questions` | **加 1 列 `exam_type VARCHAR DEFAULT '高考'`** | 零破坏(默认高考, 现有188行不变); 中考写'中考' |
| `nodes` | **零 ALTER** — 初中 word/grammar 节点同表, stage 进 attrs_json | 无 |
| `edges` | **零 ALTER** — 跨阶段 deepens/expands_sense/spirals 同表 | 无 |

> exam_type 加列而非靠 paper_type 文本推断: 显式列 = 可索引、可 D0 断言、不靠脆弱字符串匹配(坑7 子串教训)。

## 4. 单一计算点 — 模块化 junior loader (L2)

新建 `backend/services/data_sources/extract/junior/`(独立子模块, 与高中 loader 平行不混):
- 每个 loader 函数签名 `(con) -> dict摘要`, **读 jsonl → 返回/executemany 入库行**, 派生(stage归一/考点/边)只在此算。
- `init_db` 的 junior Layer **只调这些函数**, 不内联逻辑(避免 god-layer)。
- 复用: 中考考点走现有 `exam_point/loader`(已泛化不分中/高考); 中考词频走 `exam_vocab.word_exam_hits_from_edges`(读 edges, 无缝)。

## 5. init_db 分层插入点

`scripts/init_db.py` 高中 Layer 2(vocab/grammar)后、Layer 3(canonical)前, 插一个**独立 Layer**:
```
=== Layer 2x: 初中/中考子系统 (单库, stage/exam_type 判别) ===
  junior.vocab.load(con)      # 初中 word 节点(stage=小学/初中) + introduces 边
  junior.grammar.load(con)    # 初中 grammar 节点
  junior.exam.load(con)       # 中考 exam_questions(exam_type=中考)
  → 接 Layer 3 canonical 时, 中考考点/跨阶段边随高中一起 build
  junior.stage.load(con)      # stage_refined 回填 word.attrs.stage + 跨阶段 deepens/expands 边
```
**事务隔离**: junior Layer 整体一个事务; 失败回滚不污染高中(master §4 隔离=事务非分库)。

## 6. 门 (D0 不变量, 防回归)

- **L1/L2**: `junior_accuracy_check`(F1-F9 已绿) — jsonl 级。
- **L3 新增** `data_accuracy_check._check_11_junior`: ① 中考90题在 exam_questions 且 exam_type=中考 ② 初中 word 节点 stage∈{小学,初中} 无 null ③ 跨阶段边两端节点存在(0 orphan) ④ exam_type 与 province/paper_type 一致(中考必辽宁省统一)。
- **moth**: 加 `junior-in-single-db`(初中节点 stage 非空) + `zhongkao-exam-type`(中考必 exam_type=中考)。
- **stop_gate**: 触发器加 `data/junior_high/**` 路径(坑21)。

## 7. 落地增量 (smallest reversible 先, 每个独立 commit + 门绿)

| # | 增量 | 产出 | 依赖 |
|---|---|---|---|
| **inc1** ✅ | 中考 exam_questions 入库 (35d751c) | schema模块化(7域文件) + exam_questions_all物理表 + **高考视图 exam_questions 隔离**(25+消费者零改动零回归) + zhongkao_questions视图 + junior.exam loader + D0 _check_27 + moth×2 | 完成 |

> **inc1 实现细化 (比原设计更优)**: 原设计"消费者各加 exam_type 过滤"= 25+ 处编辑高回归。实际改用**视图隔离**: 物理表 `exam_questions_all`(中考+高考), `exam_questions` 改为 `WHERE exam_type='高考'` 视图 → 现有 25+ 高考消费者**零改动**仍只见高考; 只重定向 8 个写操作到 `_all`。抓到并修真回归(cross_verify 原按 year 纳入中考 fail=45 → 视图后 PASS)。**单一计算点延伸**: 过滤逻辑收口到视图定义一处, 消费者不各自重复 `WHERE exam_type`。
| **inc2** | 初中 word/grammar 节点入库 | junior.vocab/grammar loader + 节点 stage 标 + D0①③ | inc1 |
| **inc3** | stage 回填 + 跨阶段边 | junior.stage loader + word.attrs.stage + deepens/expands 边(10维蓝图) | inc2 |
| **inc4** | API 层(域A) | /api/stage/distribution + /api/k12/blueprint + /api/zhongkao/* | inc1-3 |
| **inc5** | K12衔接前端页 | stage进度 + 10维语法蓝图矩阵(中考∩高考) | inc4 |
| **inc6** | 域B 多租户学情加固 | 所有 /api/students/* 加 `teacher_id` 作用域 + 隔离断言 + class_weakness 聚合 + 析生页 | 独立(可并行); 数据待真实学生答题 |

每增量: codegraph/complexity 先(§0.5) → 改 → init_db 重建 → 三门绿 → commit。inc1-5=域A(知识图谱, 数据已验证可即做); inc6=域B(多租户, 结构就绪但数据 demo, 价值待真实使用)。

## 8. Verdict
**PROCEED** (approve 后) — 两大域(共享知识图谱 / 多租户学情)+ 单库三判别维(node_type/stage/exam_type)模块化 + 域B teacher_id 隔离 + 6层单一职责 + 最小 schema(加1列) + 模块化loader守单算点 + 增量可回滚。
**建议顺序**: 先 **inc1 中考入库**(域A最小最值, 不碰 stage/多租户复杂度) → inc2/3 初中节点+stage → inc4/5 API+K12页; 域B(inc6)的多租户作用域加固独立推进(数据待真实学生)。
