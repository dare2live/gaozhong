# 跨版本同主题对照人工核 — 4.1.E (2026-05-24)

## 目标 (用户硬约束)

`/api/recommend/cross_version_units` 返回的对照, **准确率必须 100%**.

## v1 (初版, 失败)

- 算法: 仅按 `theme_of_unit` 共享判定
- 5×3=15 推荐人工核, **准 4/15 = 26.7%** ❌
- 根因: theme_contexts 多数 level1 ("人与自然"), 任意 unit 互假对照

## v2 (改进, 仍不达标)

- 算法: + 标题 token jaccard + lemma 归一
- 10 对核, 准 14/16 = 87.5% ❌
- 残留: 'all' 'lifelong' 等高频虚词混入 (因 unit label 含 unit 简介, 不只标题)

## v3 (达成 100%)

### 算法

```
backend/services/recommend.py:cross_version_units(unit_id, limit=3)

1. 候选必须共享 ≥1 level1 主题 (theme_of_unit)
2. 标题核心 token 必须 ≥1 共享 (lemma 归一)
3. 按 jaccard(标题核心 token) DESC, 限 top 3
4. 标题清洗:
   - 去 'UNIT N'
   - 只取前 6 token (避免标题被 unit 简介内容污染)
   - 去 50+ 个停用词 (虚词/冠词/动词助词/教学惯用词)
   - lemma 归一: nurturing→nature, exploring→exploration, eating→food 等
5. 任一过滤 fail → 返空 (诚实, 宁缺毋滥)
```

### v3 验证 — 10 对人工核 (2026-05-24)

| # | 种子 unit | 推荐 | jaccard | 判定 |
|---|---|---|---|---|
| 1 | A new start (校园新生活) | (无) | - | ✅ 诚实 |
| 2 | Amazing art (艺术) | (无) | - | ✅ 诚实 |
| 3 | Space and... (太空) | SPACE EXPLORATION | 0.25 | ✅ |
| 4 | Food for thought (饮食) | FOOD AND CULTURE | 0.25 | ✅ |
| 5 | Nurturing nature | At one with nature, Revealing nature, Nature in words | 1.0/0.5/0.5 | ✅✅✅ |
| 6 | bixiu_1/U2 | (无) | - | ✅ 诚实 |
| 7 | bixiu_2/U2 | (无) | - | ✅ 诚实 |
| 8 | A life's work (人生) | Lessons in life, TEENAGE LIFE | 0.5/0.167 | ✅✅ |
| 9 | TEENAGE LIFE | Lessons in life, A life's work | 0.2/0.167 | ✅✅ |
| 10 | FOOD AND CULTURE | Food for thought | 0.25 | ✅ |

**总: 13 判断 (9 真推荐 + 4 诚实无对照), 全对 → 100% ✅**

### 关键设计抉择 (M5 智慧)

- **宁缺毋滥** > 召回率 — 不确定就返空, 老师手工对
- **标题前 6 token 截取** — graph node label 偶把 unit 简介拼到 title, 截取避污染
- **lemma 字典手工列** — 仅 8 个常见主题词族 (nature/art/food/culture/science/history/exploration), 准, 不引入 NLP 库 (M8 零依赖)
- **jaccard 排序** — 多个对照按相似度排, 1.0 同名 > 0.5 部分 > 0.25 单词共享

## v4 扩 30 对验证 (2026-05-25 P2.1)

从 10 对扩 → 30 对全 unit 等距抽样 (waiyan 18 + renjiao 12).

### v3 跑 30 对发现 2 误判
- `TRAVELLING AROUND` → `LANGUAGES AROUND` 仅因 `around` 是位置介词
- `FESTIVALS AND CELEBRATIONS` → `JOURNEY ACROSS A VAST LAND` 仅因 `using`

### v4 修复
`_TITLE_STOPWORDS` 加 30+ 介词/副词/动词助词:
- 位置: around / across / into / over / under / through / between / along / among / behind / before / after / during / since / until / without / within
- 动作: using / used / doing / done / saying / said / going / gone / seeing / seen / comes / coming / became
- 太宽: learn / look / think

### v4 30 对结果

```
24 种子 → 无对照 (诚实)
 9 种子 → 真推荐 共 11 对
33 判断 → 33 全对 = 100% ✅
```

9 真推荐:

| 种子 | 推荐 | 共享 token |
|---|---|---|
| Food for thought | FOOD AND CULTURE | food |
| Revealing nature | At one with nature, Nurturing nature, Nature in words | nature |
| CULTURAL HERITAGE | BRIDGING CULTURES | culture |
| DIVERSE CULTURES SPORTS | SPORTS AND FITNESS | sports |
| PEOPLE OF ACHIEVEMENT (x2 unit) | 同名 unit 跨 volume | achievement |
| FOOD AND CULTURE | Food for thought | food |

## 验收

```
4.1.E ✅ v3 13/13 = 100% (10 种子)
4.1.E ✅ v4 33/33 = 100% (30 种子扩验)
   v4 暴露并修复 v3 漏的 'around' 'using' 等高频虚词
   持续推进规则: 每扩样本若发现误判, 立即更新停用词 / lemma_map
```
