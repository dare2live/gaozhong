# 数据可视化 + 前端方案 — 「考点驾驶舱」教师工作台 (2026-06-19)

> 由 understand+design 工作流 wf_dfcae67c (4底图×3视角, 3提案独立收敛) + architect-controller 综合定稿。
> 配 `tutorial_consumer_spec.md`(消费者立法) + `k12_platform_master_design.md`(stage维) 用。

## 0. Genesis (立法层 — 不可动)

- **为何存在**: 把课标(脊柱)+教材(实现)+真题(检验)的 K12 知识图谱, 渲染成**教师备课/讲课/分析学生**三段工作流的可决策视图; 用大数据把"好老师画重点/析趋势"做得更准更全。
- **主消费者 = 教师**(立法锁死, `tutorial_consumer_spec.md`)。学生 = 被分析的**数据脊柱**(错题库/档案), **不是**自助刷题门户。
- **死亡条款(可视化感知死)**: ① 前端重算 JOIN/agg(违铁律1) ② 取历史平均冒充趋势(掩盖命题迁移) ③ 样本不足画实斜率线/押具体题=fraud ④ 答不出"老师哪一步用"=为分析而分析。

## 1. 信息架构 (IA) — 在现有 vanilla-JS SPA `app.html` 上扩展

```
考点驾驶舱 (app.html SPA 壳, hash 路由, 侧边栏 register(name,mount))
├── 🎯 备课工作流 (默认落地页)
│    ├── A 考点分布卡   (era 分层堆叠: genre/theme_l2课标10群/设问7技能/语法9类)
│    ├── B 考点迁移对比 (era→era delta, 翻转高亮; 前端仅对两段distribution做差展示)
│    ├── C 命题趋势带   (折线+reliable护栏; 不可信→灰显"样本不足(分布可用)")
│    └── E 词汇4象限热力 (core/standard/HV/LV × 首字母; 标"词频热力"非考点)
├── 📖 讲课工作流
│    └── D 概念浮窗 4路追溯 (任一 .gz-concept 一键调出 真题↔考点↔课标↔教材; 已成形 graph_popup.js)
│         + 考点关联网络 C' (同题共现 force/弦图)
├── 👥 分析学生工作流
│    ├── F 班级学情热力 (class × exam_point 矩阵; demo seed→显式banner)
│    └── 错题→真考点溯源清单 (每行 .gz-concept 接浮窗)
└── 🔗 K12 衔接 (stage)
     └── G 10维语法蓝图矩阵 (中考∩高考=最高优先级地基; deepens跨阶段边; N=2静态快照不画趋势)
```

跨切面: **概念浮窗(D)** 是全局原语 — 任一视图里的词/语法/考点节点渲染成 `.gz-concept[data-concept]` 即免费接入浮窗(common.js.conceptLink + graph_popup.js)。

## 2. 视图清单 × 单一计算点 × 服务的决策

| 视图 | 可视化型 | 数据来源(现有 API, 前端禁重算) | 教师决策 |
|---|---|---|---|
| A 考点分布 | era分层堆叠条 | `GET /api/exam_point/distribution` → exam_point/loader | 本单元练哪类题型/哪主题群权重最高 |
| B 考点迁移 | delta对比条+翻转箭头 | 同A两段era差值(展示层做减法) | 复习重心往哪迁(记叙↔说明翻转/人与自然8.5→19.5%) |
| C 命题趋势 | 折线+斜率带+reliable灰显 | `/api/trend/{summary,question_type_trend,vocab_growth}` | 题型/词量长期走向; 辽宁N<10→灰显不画slope |
| C' 考点关联 | force图/弦图/共现矩阵 | `/api/exam_point/cooccurrence` | 哪些考点常同题(co_n)→组合训练 |
| D 概念浮窗 | 结构化清单 modal | `/api/graph/popup` (已成形) | 当堂4路追溯, 词/语法关联到真题与课标 |
| E 词汇热力 | CSS heat-grid+drill | `/api/heatmap/{vocab,words_by_status}` | core/standard/超纲分布→词表教学边界 |
| F 班级热力 | class×考点矩阵 | **缺** `/api/students/class_weakness` (聚合下沉weakness service) | 全班共性薄弱考点→补什么/推哪课 |
| G 10维蓝图 | 静态网格+deepens边 | stage_refined.jsonl(**需先入库+API**) + alignment.md | K12衔接: 初中学牢/高中深化 |

## 3. API 缺口 (薄转换, 计算仍留 service — 守铁律1)

1. `/api/exam_point/cooccurrence_graph` — 把 cooccur pairs 转 `{nodes,edges}` 喂 force图 (薄转换)。
2. `/api/students/class_weakness?class_id=` — 班级 class×exam_point 聚合 (聚合下沉 weakness service)。
3. (K12) stage_refined.jsonl → DuckDB 入库 + `/api/stage/*` (G 视图依赖; 较重, 后置)。
> 1+2 可即做(service 已有派生逻辑); 3 需先建初中库。其余视图**零新建直 fetch**。

## 4. 交互 + 跳转规范

- **壳**: 侧边栏 4 工作流分组(备课/讲课/析生/衔接), hash 路由 `#/beike/distribution` 等, `mount()` 切换不刷新。
- **筛选条(全局)**: 顶部 sticky — 卷制 era(2015-2020/2021+) · province=辽宁(锁定显示, 不可改) · 维度(genre/theme/设问/语法)。改筛选 → 重 fetch 当前视图, 不重算。
- **样本量护栏(强制)**: 每个趋势/分布图右上角 `reliable` 角标 — 绿"分布可用" / 灰"趋势样本不足"; N<阈值时趋势线灰显 + banner。读 `trend/scope.diagnose` 真相, 前端不自判。
- **下钻**: 分布条/热力格 click → drilldown 同视图展开该维度明细 (E 已有 words_by_status); 不跳页。
- **概念浮窗(跨视图)**: 任一 `.gz-concept` click → 全局 modal 4路追溯; modal 内节点可递归点(BFS expand); 不离开当前页。
- **工作流跳转**: 析生清单某错题 → "在分布里看" → 跳备课A并高亮该考点(query带 highlight=考点id)。
- **demo数据诚实**: 班级/学生热力(F)顶部红条 banner "示例数据 · 待真实答题量", 不伪装满看板。

## 5. 技术约束 (贴现有栈)

- **纯 vanilla JS 零框架零构建** (现状: app.js 自实现 simForce / heat-grid / ep-bar CSS条)。新视图 = 独立 `frontend/static/<feature>.js` + register 进 SPA。
- **取数全走 `GZ.fetchJSON`**; 概念走 `GZ.conceptLink`; 经济学人配色(#0a4d75蓝/#c1272d红)。
- **可视化升级建议**: 当前手搓 CSS-div 条 / HTML-table 趋势较原始。**可引一个轻库**(如 ECharts/Chart.js, 走 CDN 允许列表)做 era 分层堆叠 + 趋势带 + force图, 但**仅渲染层**, 数据仍 service 单算。**待用户拍板是否引库** (零库=贴现状但viz糙; 引库=viz精但加依赖)。
- **前端铁律**: inline `<script>`≤80行 / `<style>`≤30行, 大块抽 common.js/css (stop_gate 守)。**前端绝不重算**(出现对 edges/exam_questions 的 JOIN/agg = 违铁律1 拒收)。

## 6. 落地顺序 (smallest reversible 先)

1. **备课页(A/B/C/E)** — 全部现有 API, 零后端, 直接搭(最高ROI, 地基全就绪)。
2. **讲课页(D + C')** — D 已成形复用; C' 加 1 个薄 cooccurrence_graph API。
3. **析生页(F)** — 加 class_weakness API(聚合下沉) + demo banner。
4. **K12衔接(G)** — 需先 stage_refined 入库 + API(最重, 后置)。

Verdict: **PROCEED** — 备课页地基100%就绪可即搭; 析生/衔接有明确薄缺口; 全程守 D0/分层/单一计算点/样本量诚实。
