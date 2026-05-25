# 模型驱动内容生成 — 项目设计宪法

> **地位**: 本文件是项目内容生成的最高设计原则. 任何题目、教案、教程的编写/生成/修改都必须遵守.
> **核心命题**: 不是"人写内容 → 模型检查", 而是"模型分析真题 → 输出指导 → 据此生成内容 → 模型审计验证".

---

## 第一原则: 真题是唯一真理源

一切内容的合法性来自**高考真题**, 不来自教材、不来自教参、不来自任何人的"感觉".

| 来源 | 权威层级 | 用途 |
|---|---|---|
| 近 5 年高考真题 (2021-2025 新课标 II 卷) | **S 级 (唯一真理)** | 命题模型的训练数据, 一切对齐的基准 |
| 课标 (2017 年版 2020 年修订) | A 级 | 词汇范围约束、主题语境框架 |
| 教材 (外研/人教) | B 级 | 词汇来源、教学进度参考 |
| Claude/LLM 生成内容 | C 级 | **必须经模型审计后才能入库** |
| 人工编写内容 | C 级 | 同上, 不享受免审特权 |

**推论**:
- 任何"我觉得这道题不错" 不如 "模型显示这道题的考点分布/难度/句长与真题偏离度 < 5%"
- 教师经验有价值, 但必须可量化验证, 不接受"感觉对齐"

---

## 第二原则: 模型先行, 内容后行

```
真题 PDF → 入库 → 特征提取 (exam_pattern_extractor)
                    ↓
              趋势分析 (trend_engine)
                    ↓
              命题模型 (exam_patterns.json + trend_analysis.json)
                    ↓
              ┌─────────────────────────┐
              │  内容生成指令 (model output)  │
              │  - 考点权重分配             │
              │  - 难度目标分布             │
              │  - 句长/词汇级别约束         │
              │  - 提问模式比例             │
              │  - 话题对齐要求             │
              └────────────┬──────────────┘
                           ↓
              内容生成 (LLM / 人工 / rule_synth)
                           ↓
              模型审计 (alignment_checker + ground_truth_validator)
                           ↓
              ┌─── pass ──→ 入库
              └─── fail ──→ 拒绝 + 反馈原因 → 重新生成
```

**禁止**: 跳过模型分析直接生成内容 ("先写了再说" = 违宪)

---

## 第三原则: 细颗粒度建模

不是"阅读理解 32 题"这种粗统计, 而是:

### 3.1 考点维度 (纵向 — 每个考点独立建模)

| 考点 | 建模内容 |
|---|---|
| 细节理解 | 提问句式分布 (What/Where/How/...) + 选项设计模式 (正面/反面/混淆) + 定位线索类型 |
| 推理判断 | 推理类型 (因果/态度/弦外之音) + 干扰项设计 (过度推理/偷换主语/以偏概全) |
| 词义猜测 | 上下文线索类型 (同义复现/反义对比/定义解释/因果推导) + 目标词难度分布 |
| 标题选择 | 全文结构类型 (总分/递进/对比) + 干扰项设计 (太宽/太窄/偏离) |
| 七选五 | 衔接信号词分类 (however/therefore/for example/...) + 空位类型 (段首/段中/段末) |
| 语法填空 | 有提示词 vs 无提示词比例 + 具体语法点频次 + 词性转换模式 |
| 完形填空 | 文体 (记叙/说明/议论) + 考查维度 (逻辑/搭配/词义辨析) |
| 续写 | 段落开头句模式 + 情节转折类型 + 情绪词分布 + 环境描写比例 |
| 应用文 | 类型分布 (邀请/建议/...) + 格式要素 + 高分表达库 |

### 3.2 时间维度 (横向 — 年份趋势)

每个考点按年份计算:
- **频次** (绝对出现次数)
- **权重** (占该年总题量的百分比)
- **斜率** (线性回归, 上升/下降/稳定)
- **预测** (明年预估权重 = 近 3 年加权平均 + 斜率外推)

### 3.3 关联维度 (交叉 — 考点之间的共现/互斥/依赖)

- **共现**: A 和 B 在同一套卷中同时出现的概率
- **互斥**: A 出现时 B 通常不出现
- **依赖链**: 学了 A 才能做 B (eg 学了定语从句才能做七选五中的关系代词填空)
- **教学推荐**: 基于共现 + 依赖链, 推荐"学完 X 后该学什么"

---

## 第四原则: 模型审计闭环

### 4.1 内容生成前审计 (pre-generation audit)

生成任何内容前, 必须查询模型输出:
```python
from scripts.tools.alignment.trend_engine import analyze
from scripts.tools.alignment.exam_pattern_extractor import extract

# 1. 当前应该生成什么?
trends = analyze(con)
rising = [t for t in trends["trends"] if t["direction"] == "rising"]
# → 优先生成上升考点的题目

# 2. 生成参数应该是什么?
patterns = extract(con)
target_difficulty = patterns["global_sentence"]  # 句长 avg 12 词
target_skills = patterns["reading"]["skill_distribution"]  # 细节 87% / 推理 37% ...
# → 注入生成 prompt
```

### 4.2 内容生成后审计 (post-generation audit)

每批内容生成后, 必须跑全套审计:
```bash
# 对齐度 (8 维度)
python3 scripts/tools/alignment/exam_alignment_checker.py --json

# 结构校验 (题面/答案/解析 完整性)
python3 scripts/tools/audit/ground_truth_validator.py --json

# 回归检测 (是否比上批更差)
python3 scripts/tools/audit/batch_regression_test.py

# 趋势符合度 (新题是否覆盖上升考点)
python3 scripts/tools/alignment/trend_engine.py  # 检查新题命中了哪些上升考点
```

通过全部 → 入库. 任一 fail → 拒绝 + 反馈原因.

### 4.3 模型能力审计 (model capability audit)

定期审计模型自身的分析能力:

| 审计项 | 方法 | 频率 |
|---|---|---|
| 特征提取准确度 | 人工抽 10 道真题, 核对模型提取的考点是否正确 | 每次新数据入库 |
| 趋势预测回测 | 用 2017-2022 数据预测 2023, 与实际对比 | 每年真题入库后 |
| 考点覆盖完整度 | 检查 EXAM_POINTS 列表是否遗漏真实考点 | 每次新数据入库 |
| 关联分析有效性 | 检查推荐的"下一步该学"是否教学合理 | 教师 review |
| 词频模型准确度 | 对比模型 top50 词与真题 top50 词的重叠率 | 每次更新 |

### 4.4 工具模块职责

```
scripts/tools/
├── alignment/
│   ├── exam_pattern_extractor.py   # 提取 → exam_patterns.json
│   ├── trend_engine.py             # 分析 → trend_analysis.json
│   ├── exam_alignment_checker.py   # 评分 → 8 维度 0-100
│   ├── topic_gap_analyzer.py       # 缺口 → 主题覆盖矩阵
│   └── difficulty_profiler.py      # 对比 → 难度曲线
├── generation/
│   ├── optuna_optimizer.py         # 搜索最优生成参数
│   └── llm_question_gen.py         # 按模型输出生成内容
├── audit/
│   ├── model_capability_audit.py   # 审计模型自身准确度
│   ├── ground_truth_validator.py   # 审计生成内容结构
│   ├── batch_regression_test.py    # 审计批次回归
│   └── content_drift_detector.py   # 审计内容漂移
└── monitor/
    ├── quality_dashboard.py        # 仪表盘 (趋势+告警)
    └── optuna_reporter.py          # Optuna 进度报告
```

---

## 第五原则: 持续学习

模型不是一次性产出, 而是**每年自动更新**:

1. **6 月高考后**: 新真题 PDF → 提取 → 入库 → re-run pattern_extractor + trend_engine
2. **模型更新**: exam_patterns.json + trend_analysis.json 自动刷新
3. **内容淘汰**: 与更新后模型偏离度 > 阈值的旧题自动标记 "待重写"
4. **新题生成**: 根据新趋势自动推荐需要补充的考点方向
5. **教案更新**: 40 节讲义中引用的趋势数据自动更新

```
每年循环:
  6 月 → 新真题入库 → 模型刷新 → 审计旧内容 → 淘汰/重写 → 生成新内容 → 审计 → 入库
```

---

## 第六原则: 输出格式标准化

模型的每个输出都必须是结构化 JSON, 可被其他工具消费:

```json
{
  "model": "trend_engine",
  "version": "1.0",
  "timestamp": "2026-05-25T19:00:00",
  "recommendations": [
    {
      "point": "词义猜测",
      "action": "increase",
      "reason": "slope=+0.179, 近3年16次",
      "target_count": 5,
      "constraints": {
        "difficulty": "hard",
        "avg_sentence_words": 12,
        "context_clue_types": ["同义复现", "反义对比", "因果推导"]
      }
    }
  ]
}
```

每个生成的内容也必须带 metadata 标明它是由哪个模型版本的哪条 recommendation 驱动的:
```yaml
- id: "reading/vocab_guess/001"
  _generated_by:
    model: "trend_engine v1.0"
    recommendation_id: "词义猜测_increase"
    alignment_score: 84.6
```

---

## 违宪行为清单

| # | 违宪行为 | 正确做法 |
|---|---|---|
| V1 | 跳过模型分析直接写题 | 先查 trend_analysis.json + exam_patterns.json |
| V2 | 凭感觉决定考点权重 | 用模型计算的 slope + frequency |
| V3 | 生成后不跑审计 | 每批必过 alignment_checker + ground_truth_validator |
| V4 | 忽略审计 fail 强行入库 | fail = 拒绝, 无例外 |
| V5 | 用旧模型指导新内容 | 每次新数据入库后必须 re-run 模型 |
| V6 | 人工内容免审 | 人写的题也必须过模型审计 |
| V7 | 估算考点分布 | 一切分布从真题计算, 不估算 |
| V8 | 独立出题不引用关联 | 每个考点必须输出关联考点 (同现矩阵) |
