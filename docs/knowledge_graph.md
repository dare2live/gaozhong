# 知识图谱设计 (gaozhong knowledge graph v1)

> 配 `architecture.md` 的 Rule 3 "Edges 是一等公民" 落地. 后续教学/作业系统都基于本图.

---

## 1. 节点类型 (node types)

每个 `nodes` 行 = 一个 concept. PK = `concept_id` (`<type>:<natural_key>` 形式, 全局唯一).

| 节点类型 | concept_id 模式 | 自然键源 | 数量级 (预估) |
|---|---|---|---|
| `word` | `word:<lowercase>` | cefr_vocab.word | ~3000 |
| `grammar` | `grammar:<hier_id>` | grammar_items.grammar_item_id (eg `三.10.3.a`) | ~80 |
| `theme` | `theme:<level1>[/<level2>]` | theme_contexts | ~13 |
| `volume` | `volume:<version>/<volume_key>` | textbooks 14 行 | 14 |
| `unit` | `unit:<version>/<volume>/U<n>` | units | ~14 × 6 = ~85 |
| `section` | `section:<unit_id>/<kind>/<idx>` | sections | ~85 × 6 = ~500 |
| `phrase` | `phrase:<sha8>` | phrases.canonical 的 sha1 前 8 | ~?000 (STEP 2 输出) |
| `question` | `question:gb/<file>/<index>` | GAOKAO-Bench example.index | ~hundreds |
| `exam_year` | `exam_year:<YYYY>` | year | ~15 |
| `publisher` | `publisher:<short>` | 外研版 / 人教版 / ... | 8 |
| `city` | `city:<name>` | 辽宁 14 地市 | 14 |
| `cefr_level` | `cefr_level:<级别>` | 义教/必修/选必 | 3 |

特殊"标签型"节点 (cefr_level / theme / exam_year) 用来做 group-by 维度.

---

## 2. 边类型 (relation types)

每个 `edges` 行 = `(src_id, dst_id, relation, weight, evidence_json)`. 双向语义自定义 (大部分单向, 必要时反向 edge 单独建).

### 2.1 课标侧 (master 关系, 由 P0 + STEP 2 P0.4 计算)

| relation | src → dst | 语义 | weight 含义 |
|---|---|---|---|
| `cefr_level` | `word` → `cefr_level` | 词的课标级别 | 恒 1.0 |
| `cefr_level` | `grammar` → `cefr_level` | 语法点的级别 | 恒 1.0 |
| `cat_of` | `grammar` → `grammar` (parent) | 层级父子 (一.10 ← 一.10.3.a) | 1.0 |
| `theme_of_unit` | `unit` → `theme` | 单元主题 (来自教材或人工标) | 主题相关度 0-1 |

### 2.2 教材侧 (STEP 2 输出)

| relation | src → dst | 语义 | weight |
|---|---|---|---|
| `in_volume` | `unit` → `volume` | 单元属哪册 | 1.0 |
| `vol_in_ver` | `volume` → `publisher` | 册属哪版 | 1.0 |
| `introduces_word` | `unit` → `word` | 该 Unit 首次引入此词 | 0-1 (主词/复现) |
| `uses_grammar` | `unit` → `grammar` | Unit 中出现该语法点 | 出现次数 normalized |
| `contains_phrase` | `section` → `phrase` | 出处证据 | 1.0 |
| `intro_in_section` | `word` → `section` | 词在哪个 section 引入 | 1.0 |

### 2.3 辽宁选用侧

| relation | src → dst | 语义 | weight |
|---|---|---|---|
| `city_uses` | `city` → `publisher` | 14 地市 → 2 版本 | 1.0 |
| `allowed_in_ln` | `publisher` → `subject:英语` | 辽宁省允许 | 恒 1.0 (省级) |

### 2.4 真题侧 (STEP 3 输出)

| relation | src → dst | 语义 | weight |
|---|---|---|---|
| `tests_word` | `question` → `word` | 题目考词 | 相关度 |
| `tests_grammar` | `question` → `grammar` | 题目考语法 | 相关度 |
| `tests_theme` | `question` → `theme` | 题面主题 | 相关度 |
| `in_year` | `question` → `exam_year` | 题年份 | 1.0 |
| `question_type` | `question` → `tag` | 完形/阅读/语法填空/读后续写 | 1.0 |

### 2.5 衍生 (links/build.py 计算, 不手填)

| relation | src → dst | 语义 | weight |
|---|---|---|---|
| `co_occurs` | `word` ↔ `word` | 同 Unit 共现 | min-max normalized |
| `topic_aligned` | `unit` ↔ `unit` (跨版本/跨册) | 主题对齐度 | cosine |
| `exam_freq` | `word` → `exam_year` | 词在真题中出现频次 | count |
| `priority_for_city` | `word` → `city` | 该地市学生应重点学的词 (依据使用版本 × 真题频次) | 计算 |

---

## 3. DB 实现

```sql
CREATE TABLE nodes (
  concept_id VARCHAR PRIMARY KEY,
  node_type  VARCHAR NOT NULL,
  label      VARCHAR NOT NULL,
  attrs_json VARCHAR              -- 额外属性 (eg pos for word, ipa, page for unit)
);
CREATE INDEX idx_nodes_type ON nodes(node_type);

CREATE TABLE edges (
  edge_id      BIGINT PRIMARY KEY,
  src_id       VARCHAR NOT NULL,
  dst_id       VARCHAR NOT NULL,
  relation     VARCHAR NOT NULL,
  weight       DOUBLE,
  evidence_json VARCHAR,           -- 来源/原句/页号等
  UNIQUE (src_id, dst_id, relation)
);
CREATE INDEX idx_edges_src ON edges(src_id, relation);
CREATE INDEX idx_edges_dst ON edges(dst_id, relation);
CREATE INDEX idx_edges_rel ON edges(relation);
```

---

## 4. 典型查询 (走 graph service, 不要在 endpoint 写)

### Q1: 沈阳学生学到必修一 Unit 3, 推荐复习哪些词?
```
Step1: city:沈阳 -[city_uses]-> publisher:外研版
Step2: publisher:外研版 ← volume ← unit (volume_key ∈ [bixiu_1], unit ≤ 3)
Step3: unit -[introduces_word]-> word, distinct
Step4: 与 exam_freq 高的词交集排序
```

### Q2: 高考最近 5 年考"读后续写"考过哪些主题?
```
question -[in_year]-> exam_year (2021..2025)
question -[question_type = 读后续写]
question -[tests_theme]-> theme
GROUP BY theme COUNT(*)
```

### Q3: 必修一 Unit 1 出 5 道完形填空候选题, 单词必须在已学范围内
```
Step1: 已学单词集 S = unit_id ≤ B1_U1 → introduces_word → word
Step2: 候选题 Q = question[question_type=完形] WHERE all tests_word ⊆ S
Step3: 按 difficulty (待加) + 主题匹配排序, 取 5
```

### Q4: 跨版本同主题对齐 (人教 vs 外研 哪些 Unit 教同一主题?)
```
unit_A -[theme_of_unit]-> theme
unit_B -[theme_of_unit]-> 同 theme
WHERE unit_A.version != unit_B.version
RETURN pairs ordered by theme weight similarity
```

---

## 5. 物化视图 (Layer 2 "预计算" 给 API 用)

| view | 计算逻辑 | 服务 |
|---|---|---|
| `v_word_full` | word + cefr_level + 教材首次引入 unit + 真题频次 | 词卡详情 |
| `v_unit_full` | unit + theme + 词数 + 语法点数 + 真题对齐题数 | 单元卡 |
| `v_city_curriculum` | city → 版本 → 所有 unit + 推荐学习路径 | 城市页 |
| `v_question_full` | question + 考点 word/grammar + theme + 难度 | 题目卡 |

物化视图由 `services/links/build.py` 末尾 refresh, 不在 API 内 compute.

---

## 6. 演进 (后续可加 / 不破坏现有)

- v2: 加 `similar_to` (word↔word, 由 embedding 算), `prereq_of` (grammar→grammar 学习顺序)
- v3: 学生侧节点 `student`, 关系 `learned`/`weak_at`/`mastered`
- v4: 题目难度模型: `difficulty_for_level` (question→cefr_level)
- v5: 教师/教研侧: `recommended_by` (lesson_plan→teacher)
