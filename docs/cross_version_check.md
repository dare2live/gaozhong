# 跨版本同主题对照人工核 — 4.1.E (2026-05-24)

## 目标

`/api/recommend/cross_version_units?unit=<id>` 返回的"跨版本同主题对照 unit" 列表, 抽 5 对人工核, **目标准确率 ≥ 80%**.

## 算法

`backend/services/recommend.py:cross_version_units()`:
1. 给定 unit, 查它的 `theme_of_unit` edges → themes
2. 找其他 unit 也指向同一组 themes 的, 排除自己 → 候选

> 注: themes 来自 `theme_contexts` 表 (课标 3 级主题).
> 当前问题: theme 粒度大多到 level1 (人与自我/社会/自然), level2/3 稀疏 → 同一高层主题下 unit 互相"假对照".

## 5 对抽样核 (2026-05-24)

| # | 种子 unit | 推荐对照 | 人工评判 |
|---|---|---|---|
| 1 | 外研·必1·U1 **A new start** (校园新生活) | (a) 外研·必2·U6 Earth first (环保)<br>(b) 外研·必3·U4 Amazing art (艺术)<br>(c) 人教·选必3·U4 ADVERSITY AND COURAGE (励志) | ❌ ❌ ⚠️  →  **0/3** |
| 2 | 外研·必3·U4 **Amazing art** (艺术) | (a) 外研·必2·U6 Earth first<br>(b) 人教·选必3·U4 ADVERSITY<br>(c) 人教·选必3·U5 POEMS (诗歌) | ❌ ❌ ⚠️  →  **0/3** (诗歌算半相关) |
| 3 | 外研·选必4·U6 **Space and...** (太空) | (a) 人教·选必4·U3 SEA EXPLORATION<br>(b) 人教·必3·U4 SPACE EXPLORATION<br>(c) 人教·选必1·U2 LOOKING INTO THE FUTURE | ❌ ✅ ⚠️  →  **1/3** |
| 4 | 外研·必2·U1 **Food for thought** (饮食) | (a) 人教·必1·U0 WELCOME UNIT<br>(b) 人教·选必1·U5 WORKING THE LAND<br>(c) 外研·选必3·U2 A life's work | ❌ ❌ ❌  →  **0/3** |
| 5 | 外研·选必1·U6 **Nurturing nature** (自然) | (a) 外研·必1·U6 At one with nature<br>(b) 外研·选必3·U6 Nature in words<br>(c) 外研·选必1·U5 Revealing nature | ✅ ✅ ✅  →  **3/3** |

**准确率: 4/15 = 26.7%** (目标 80% 不达标)

## 根因分析

1. **theme_contexts 粒度太粗** — 大多只 level1 ("人与自然"), 同一 level1 下 N 多 unit 互相"假对照"
2. **算法未加 unit 标题 jaccard 兜底** — eg "Food for thought" 跟 "WELCOME UNIT" 完全不相关, 仅因共享 level1 主题就被推
3. **theme_of_unit edges 当前未细分** — `backend/services/links.py` build 时只挂 level1, level2/3 没拿来

## 修复建议 (推迟 P2)

| 选项 | 描述 | 工作量 | 收益 |
|---|---|---|---|
| A | 加 unit 标题 jaccard 相似度 (≥0.3) 二筛 | 0.5h | ⭐⭐⭐ 简单粗暴, 立竿见影 |
| B | links.py 重建 theme_of_unit edges 用 level3 | 1-2h | ⭐⭐ 需 unit 标题→level3 映射, 缺数据 |
| C | 引 LLM 算 unit 标题语义相似 | 2-4h | ⭐⭐⭐⭐ 最准, 但需 LLM (违反 M8 零依赖) |

**当前状态**: P1.3 真做了, 准确率不达标. 老师试用阶段告知"对照功能仅作初步参考", 推迟到第 7 阶段修. 不阻塞运营交付.

## 验收状态

```
4.1.E ✅ 文档落地, 5 对人工核完成
4.1.E ❌ 准确率 26.7% < 80% 目标 (真实数据暴露算法缺陷)
   → 升级为 P2 待修, 记入 lessons_learned (L-?: 假关联问题)
```
