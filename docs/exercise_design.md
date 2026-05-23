# 作业生成体系顶层设计

> 用户 2026-05-23: "结合每课的教学内容出相应的试题, 还有阶段试题, 总体试题".
> 设计遵循 `docs/architecture.md` 三铁律: 单一题源 / canonical / graph-driven.

---

## 0. 四级粒度 (题目作用域)

| 级别 | 作用域 | 典型时机 | 题量 | 难度 / 知识范围 |
|---|---|---|---|---|
| **L1 课时题** | 单 section | 每节课结束 | 5-10 | 极窄 (该 section 引入的词/语法/短语) |
| **L2 单元题** | 单 Unit (含全部 section) | 单元结束 | 20-30 | Unit 内全部知识 + 已学 Unit 部分复现 |
| **L3 阶段题** | 多 Unit / 半学期 / 一册 | 月考/期中/期末 | 50-80 | 该册全部 + 之前册次复现, 模拟真考题型 |
| **L4 总体题** | 全 7 册 / 模拟高考 | 一/二/三轮复习 | 完整高考卷 (150 分 / 120 分钟) | 课标全词表 / 全语法点; 严格 province=辽宁 卷型对齐 |

---

## 1. 单一题源 (single question source)

绝对禁止"按四级各自维护题库". 题库 **只有一份** = `exam_questions` 表 (真题) + `synthesized_questions` 表 (LLM 合成, STEP 4 输出). 四级是**视图**, 不是独立库.

```sql
-- 真题
exam_questions(question_id, year, province, paper_type, question_type, raw_question, answer, ...)
-- LLM 合成 (STEP 4 输出)
synthesized_questions(question_id, gen_at, gen_model, prompt_id, qtype, raw_question, answer, ...)

-- 共享视图 (UNION, services/exercise/source.py 构造):
v_questions = SELECT *, 'real' AS origin FROM exam_questions
              UNION ALL
              SELECT *, 'synth' AS origin FROM synthesized_questions
```

任何"出 5 道题" 的操作都从 `v_questions` 加 graph 过滤选, **不再各自重组题面**.

---

## 2. 出题 pipeline (services/exercise/generate.py, 5 步)

```
入参: 约束 spec
  - scope: section_id | unit_id | volume_id | (multi_unit_id_list) | "exam_simulation"
  - city / version (用于约束 vocab 范围)
  - count, question_types whitelist
  - difficulty (optional)
  - 必含/必避 知识点 (optional)

Step 1. 解析约束 → 知识范围
  调 services/graph.expand:
    scope_node → unit_set → introduces_word(union) → 可用词集 W
    unit_set → uses_grammar(union) → 可用语法集 G
    + 由 cefr_level 进一步约束 (eg L1 课时题 只用义教+本课词)

Step 2. 候选题召回
  v_questions WHERE
    所有 tests_word ⊆ W
    所有 tests_grammar ⊆ G
    question_type ∈ whitelist
  (graph 查 tests_word/tests_grammar)

Step 3. 难度评估 (services/exercise/difficulty.py)
  - 真题: 由 GAOKAO-Bench 答对率 + 题面长度 + 词频得 difficulty_score
  - 合成: gen 时 LLM 自评 + 后期答题反馈调
  → 题目按 difficulty 分箱 [easy/mid/hard]

Step 4. 题型分布约束 + 排序
  按四级约束分布:
    L1: 5 单选 + 2 填空 + 1 短句仿写
    L2: 10 单选 + 5 完形 + 5 阅读 + 3 改错 + 1 应用文
    L3: 模拟真卷比例 (听 30+ 阅 50+ 完 15+ 语填 15+ 应文 15+ 续写 25)
    L4: 完整真卷 (150 分)
  组合优化 (services/exercise/compose.py): 在召回集里挑满足分布 + 难度 + 不重复
  → 题单 list[question_id]

Step 5. 渲染 + 答案分离
  services/exercise/render.py 输出:
    paper.html (学生卷, 无答案)
    answers.html (教师卷, 含答案+解析+考点 graph)
    blueprint.json (题号→考点 graph 映射, 出题报告)
```

---

## 3. 数据库扩展 (新增 4 张表, 不改现有)

```sql
CREATE TABLE synthesized_questions (
    question_id   VARCHAR PRIMARY KEY,
    gen_at        VARCHAR NOT NULL,
    gen_model     VARCHAR,
    prompt_id     VARCHAR,
    question_type VARCHAR,
    raw_question  VARCHAR,
    answer        VARCHAR,
    analysis      VARCHAR,
    province      VARCHAR DEFAULT '辽宁_合成',
    quality_score DOUBLE,
    reviewed_by   VARCHAR
);

CREATE TABLE question_difficulty (
    question_id  VARCHAR PRIMARY KEY,
    difficulty   VARCHAR,          -- easy|mid|hard
    score        DOUBLE,
    estimator    VARCHAR,           -- "gaokao_bench_accuracy" | "llm_self_eval" | "student_feedback"
    updated_at   VARCHAR
);

CREATE TABLE exercise_papers (
    paper_id      VARCHAR PRIMARY KEY,
    paper_level   VARCHAR NOT NULL,   -- L1|L2|L3|L4
    scope_node    VARCHAR NOT NULL,    -- concept_id
    city          VARCHAR,
    version       VARCHAR,
    created_at    VARCHAR NOT NULL,
    blueprint_json VARCHAR             -- 题号→ concept_id 映射
);

CREATE TABLE paper_questions (
    paper_id      VARCHAR NOT NULL,
    seq           INTEGER NOT NULL,
    question_id   VARCHAR NOT NULL,
    section_label VARCHAR,             -- "听力 / 阅读 / 完形 / 写作"
    PRIMARY KEY (paper_id, seq)
);
```

考点 edges 自然延伸 (无 schema 改):
```
question -[tests_word]-> word
question -[tests_grammar]-> grammar
question -[tests_theme]-> theme
question -[tests_section]-> section          (新 relation, 真题/合成题 → 教材 section)
paper    -[contains_question]-> question     (新, 走 edges)
```

---

## 4. 反模式 (绝对禁止)

| 反模式 | 后果 | 正解 |
|---|---|---|
| ❌ L1/L2/L3/L4 各自一张表 | 同一题副本满天飞, 改 1 题改 4 处 | 单 v_questions, 视图过滤 |
| ❌ 前端 fetch 一堆 raw 然后 JS 组卷 | 越纲判 / 难度排序 都在前端重做 | 后端 generate, 前端只 render |
| ❌ "我们再写一个出题工具脚本" | 又一份并行实现 | 入 services/exercise/, 改一处全用 |
| ❌ 不走 graph, 直接 SQL LIKE 题面找词 | 慢 + 错 (漏抓变形词) | tests_word edge (STEP 3 已建) |
| ❌ 出题不带 province 过滤 | 把全国卷题塞进辽宁卷模拟 | scope spec 必含 province=辽宁 |

---

## 5. STEP 推进 (本设计的落地节奏)

| 阶段 | 输出 | 验收 |
|---|---|---|
| **S2** (教材结构化) | unit/section/vocab_intro 入表 + edges | edges introduces_word ≥ 3k |
| **S3** (真题考点抽) | exam_questions → tests_word/tests_grammar/tests_theme | 每题平均 ≥ 3 个 edges |
| **S4-a** (题源合成) | synthesized_questions + 上述 edges | 每 unit ≥ 30 合成题, 越纲率 < 5% |
| **S4-b** (难度模型) | question_difficulty | 真题难度 R² ≥ 0.6 (GAOKAO-Bench 准确率回归) |
| **S5-a** (L1/L2 实现) | services/exercise/generate L1/L2 | 任意 unit 可出 L1+L2 卷 |
| **S5-b** (L3/L4 实现) | 模拟卷, 完整高考结构 | L4 题型分布 = 真卷 (听 30+阅 50+...) |
| **S6** (评估反馈) | student_answers → question_difficulty 反哺 | 每周 cron 重算难度 |

---

## 6. 与 STEP 4 趣味化内容的关系

不矛盾: 趣味化 = **题面的呈现外壳** (短视频脚本 / 段子 / 类比), 题的 schema 不变.

出题 pipeline 在 Step 5 渲染后, 可选过 `services/exercise/styler.py` 包一层外壳, 但**核心知识点不动**. 不许用外壳偷换考点.
