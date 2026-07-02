# gaozhong 顶层架构设计 — 模块+数据+配置 三层范式 (可扩展可维护)

> 工程层架构权威文档 (架构师协议: 立法→控制→执行). 统合 [docs/architecture.md](architecture.md)(八铁律) +
> [project_architecture.yaml](../backend/config/project_architecture.yaml)(机器契约).
> **产品方向以北极星 [product_master_plan.md](product_master_plan.md) 为准**; 本文只管工程侧"模块+数据+配置三层 + 每类扩展 playbook(§2)"的可操作视图, 不重复 architecture.md/机器契约.
> 沿革: 承接 2026-06-15 三层范式首版立法演进而来 (历史在 git); 2026-06-26 加每类扩展 playbook + 2026 真题入库实证 gap + 中考 forcing-function.
>
> grounding 实证: 39 DuckDB 表 · 28 config yaml · services 13907 行无 god-module(>400) · 8-9 处/加一份卷(2026实证).

---

## 0. 创世层 (Genesis — 不可变, 极少极硬)

**为何存在**: 把"沈阳/辽宁 K12 英语教研真值平台"做成一个 **任意扩展(新卷/新教材版本/新词典源/新KG关系/新分析维度/新前端页/新审计门)都只动「配置+数据+模块」三层、零散落硬编码、自动传导自验** 的可演进系统。教研员的核心竞争力(考点趋势×教材课标关联分析)建在 100% 准的真值地基上, 地基的"加一类东西"成本必须低到不阻碍演进。

**死亡红线 (≤3, stranger-testable)**:
1. **加一类东西手工触碰 >2 处散落真相源 → 判死**(违模块化; 2026真题卷的8-9处是反例, 待治).
2. **判断规则/阈值/分类/基线 硬编码在 service/route 而非 config → 判死**(违数据化 §3.5).
3. **派生事实(考点/热点/基线/越纲/边)多处各算、或新数据落地不自动传导/不自验 → 判死**(违单一计算点 + 感知死).

**判断法典种子** (人话 / 机器话):
- 真相源(教材+课标+真题PDF)≠派生表 / `nodes`/`edges`/`exam_vocabulary` 全可从镜像表+config重算.
- 配置即判断, YAML可改不动码 / 新增判断先问"能进 `backend/config/*.yaml` 吗".
- 模块是薄壳: 读配置、查真相源、算一次入派生 / service 不内联散落 SQL, route 不重算.
- 扩展走注册表非改编排器 / 加一类 = config 加一 entry, 不改 `init_db` 主流程.
- 门自动验不靠人记 / 三门(data_accuracy_check/moth/stop_gate) + 年覆盖 anti-stale.

---

## 1. 三层范式 (模块 / 数据 / 配置)

```
┌─────────────────────────────────────────────────────────────┐
│  配置层 backend/config/*.yaml (28个)  — 判断 + 扩展注册表      │
│    判断规则: stopwords/thresholds/question_types/exam_paper_  │
│              contracts/d0_baselines/political_blacklist...    │
│    扩展注册表: sources.yaml(源) / source_versions(版本) /     │
│              exam_point_taxonomy(维度) / project_architecture │
│    前端镜像: frontend/static/category-config.js (GZ_CAT)     │
└───────────────────────────┬─────────────────────────────────┘
                            │ 模块读配置
┌───────────────────────────┴─────────────────────────────────┐
│  模块层 backend/services/*.py (13907行, 无god-module)         │
│    薄壳单算点: 读config → 查真相源 → 派生一次 → 入表/边        │
│    子域: data_sources(获取/提取) / extraction / imports /     │
│          canonical / links · links_extra(边) / exam_point /  │
│          trend / heatmap / course / recommend / audit / k12  │
│    薄壳API: backend/api/routes/*.py (读service, 0内联SQL重算) │
└───────────────────────────┬─────────────────────────────────┘
                            │ 模块写/读数据
┌───────────────────────────┴─────────────────────────────────┐
│  数据层 DuckDB 单库 gaozhong.duckdb (39表) + data/ 产物       │
│    ① 真相源镜像(一手): cefr_vocab/units/textbooks/exam_       │
│       questions_all/zhongkao_questions/word_glosses/grammar_  │
│       items/unit_vocab_intro/theme_contexts/liaoning_*        │
│    ② 派生(可重算): nodes/edges/exam_vocabulary/question_bank/ │
│       question_tags/course_materials/student_weakness         │
│    ③ 审计/血缘: audit_findings/file_manifest/source_versions  │
│    ④ 学情demo(②③轨, 必空态): students/teachers/classes/      │
│       student_answers                                        │
│  data/ 结构化: checked-in真值源 vs 生成物(应全接init_db)      │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 模块层 — 职责边界 + "什么进这层"
- **铁律**: 薄壳单算点(铁律1). 派生事实只在一个 service 函数算一次. route 纯薄壳(0 内联 SQL 重算 — 实证前端干净, 唯一瑕疵 `stats.py` province GROUP BY 待收口).
- **子域边界**(现状, 健康): `data_sources/`(获取fetcher/acquire + 提取extract, 单一计算点层) → `extraction/`+`imports/`(入真相源镜像) → `canonical`(建PK节点) → `links`/`links_extra`(建边) → `exam_point`/`trend`/`heatmap`/`course`/`recommend`/`k12`(派生分析) → `audit`(自验).
- **进这层的判定**: 是"算法/流程"(怎么提取、怎么派生、怎么校验)→ 模块. 是"判断值/阈值/分类/名单"→ 不进模块, 进配置.
- **反模式禁令**: god-module>400行(现0个, 守住) · CC>15 · 散落重复 SQL(现5条 exam_questions 写路径 = 待收一个 `_upsert_exam_rows` 单点) · 硬编码常量(`cognitive_skill.py` 硬编码 jsonl 名/年份 = 待 glob+config).

### 1.2 数据层 — 三分类 + 命名/血缘约定
- **① 真相源镜像**(一手, 不可由代码生成, 只能从 PDF/官方源提取入库): 命名 = 实体复数(cefr_vocab/units/textbooks). 改它要走 data_sources 提取链 + manifest sha 锁.
- **② 派生**(可从①+config 完全重算, init_db 幂等重建): 命名 = nodes/edges/<entity>_<aspect>(exam_vocabulary/student_weakness). **铁律: 删库重建必须 bit-级可复现, 无链外手工步骤**.
- **③ 审计/血缘**: audit_findings(run_all产) / file_manifest(sha锁) / source_versions(PIT版本).
- **④ 学情 demo**(②③轨, 死红线): students/teachers/classes/student_answers 必空态 + demo banner, 不冒充真实.
- **废表 sunset**(architect-controller 规则6: 长期未用=退役): `papers`/`paper_questions`/`course_handouts` 3 表 0 行, 为未实现负载建的器官 → 标记 deprecated 或删(P2). (`course_sessions`/`scan_uploads` 2026-07-02 已删 — 教师工具下线兑现.)

### 1.3 配置层 — judgment + 扩展注册表
- 28 个 yaml 已相当成熟(配置化做得好). 分两类:
  - **判断规则**: stopwords/thresholds/question_types/exam_paper_contracts/content_gates/political_blacklist/year_weights/word_variants/grammar_topic_map...
  - **扩展注册表**: `sources.yaml`(数据源, 典范) / `source_versions`/`source_states`(版本/状态) / `exam_point_taxonomy`(分析维度) / `project_architecture.yaml`(模块/数据/门契约).
- **前端配置镜像**: `frontend/static/category-config.js`(GZ_CAT: stage/examStatus/skill/dim/glossSource) — 前端的"配置层", 防散落硬编码.
- **进配置的判定**: 是"会变的判断值/会扩的清单"→ 配置. 是"算法"→ 模块.

---

## 2. 扩展 Playbook (核心交付 — 每类扩展 = config+data+module, 目标 ≤2 处)

> 判定每类是否达标: "加一个 X 要改几处" + "是否散落硬编码" + "是否自动传导自验".

| # | 扩展类型 | 现状摩擦 | 目标 playbook (≤2处) | 达标? |
|---|---|---|---|---|
| 1 | **新真题卷**(高考/中考) | 8-9处(2026实证) | ① `sources.yaml` 加 entry(源+sha+provenance) ② 放 structured jsonl(题面+答案) → `init_db` 遍历自动入库+传导+rebaseline | ✗ 真题入库管道 P0 待收口(详 git 历史) |
| 2 | **新教材版本**(某市换版) | 中(canonical已单点) | ① `sources.yaml`+`source_versions` 加版本 ② 放教材PDF → extraction 自动出 units/vocab/sections + canonical 节点 | ~达标(canonical驱动) |
| 3 | **新词典/词汇源** | 中 | ① `sources.yaml` 加源 + `source_crosscheck_rules` 加校验 ② 提取入 word_glosses → exam_vocabulary 单算点自动并 | ~达标 |
| 4 | **新 KG 关系/边类型** | 低-中 | ① 边白名单(relation 加值, 走 `links`/`links_extra` builder) ② 无需改消费方(graph service + 前端浮窗泛读 relation) | ~达标(白名单驱动) |
| 5 | **新分析维度**(考点/认知) | **高**(cognitive硬编码) | ① `exam_point_taxonomy.yaml` 加维 ② 标注产物 jsonl 入仓 → exam_point/cognitive loader 读 config+glob 自动建边 | ✗ cognitive待glob+config |
| 6 | **新前端 tab/卡** | 低(教研室已顺) | ① `nav-config.js` 加 tab ② 新 `<tab>.js` registerTab 读 /api(0 SQL) — 后端有矿口则0后端改 | ✓ 达标 |
| 7 | **新审计门/D0项** | 低-中 | ① `data_accuracy_check` 加 check 函数(或抽 `scripts/lib/d0_*.py`) + `.moth/claims.yaml` 加断言 ② 无数据改 | ~达标(坑17: 双门都加) |

**结论**: 7 类里 **#6前端、#2教材、#3词典、#4关系 已基本达标**(注册表/单算点驱动); **#1真题卷、#5分析维度** 是两个高摩擦项, 治理见 §5 演进(真题管道P0 + cognitive glob+config).

---

## 3. 数据层规整 (truth/derived/audit 三分类落地)

1. **生成物全接 init_db**(消链外手工 — 死红线2): 当前 `vocab_classification.jsonl`、`genre_theme_labels.jsonl` 是链外手工脚本产, 删了得记得手跑 → 接进 init_db Layer(tests_word 边建完后调 build_vocab), 或显式声明 checked-in 源 + 覆盖年校验门.
2. **血缘**: 真相源镜像 file_manifest sha 锁(已有); 生成物对 file_manifest **改"读DB现算"非"sha比对"**(断 vocab 的 ~4次重建连锁).
3. **canonical 化异构**: `exam_questions_all` 的 group/item 粒度 + answer 5格式(`which##that`/`[G,E,B]`/空格/`56.x`/自由文本) → `parse_answer(raw, source_repo)` 单点归一(P1, 第一个答案级消费者出现时落 `exam_answer_canonical` 表).
4. **废表 sunset**: 5 个 0 行空壳表 deprecated/删(P2).

---

## 4. 配置层收口 (散落硬编码 → 注册表 + 单一来源)

1. **硬编码→config 清单**(应数据化却在代码):
   - `cognitive_skill.py` 硬编码 `xgkii_2021_2025_subquestions.jsonl` 名 + 年份白名单 → glob `xgkii_*` + `exam_point_taxonomy` 配置(P0).
   - `scope.py` 常量 `LIAONING_XGKII_2021`/`PAPER_XGKII` 命名债(名带2021却承载2021+全era) → 重命名 `LIAONING_XGKII_NEW_ERA`(P2纯改名).
   - `init_db` 手接每份卷 import → 遍历 `sources.yaml` kind=exam_paper(P1).
2. **配置单一来源**(消重复): `d0_baselines.yaml` 计数 ↔ `.moth/claims.yaml` 同数字 = 双源同事实 → moth 引同查询或删让 d0 单守(P1). 前端 GZ_CAT ↔ 后端 config 的镜像项(stage色等)保持单向派生.
3. **基线 rebaseline 非 derived**: 随卷漂移计数(gaokao/zhongkao total)保留 eq 锚(防漂移核心), 加 `scripts/rebaseline.py`(现算→写回→打印diff→人审), 替"手敲". **不用 derived:SELECT**(会令 expected==actual 永真 = 自废防漂移门 = 假绿).

---

## 5. 治理/自验层 + 演进路线

### 治理(防"加东西破门/绿门假绿")
- **三门**: data_accuracy_check(D0 100%) + moth(声称-实况漂移) + stop_gate(复杂度/inline/架构契约).
- **anti-stale 年覆盖断言**(新增, 死红线3): `exam_questions` 有 (year,province) 行 ⟺ 其应得派生边(tests_word)非空; exam_point/cognitive 维标 unknown 豁免. **抓"入库成功+三门绿+KG空传导"盲区**(2026 exam_point=0 / 2024-25 tests_word=0 都漏过).
- **project_architecture.yaml 契约**: 模块/数据/门契约机器可校验(`map doctor --strict` + stop_gate gate4), 扩展时同步.

### 演进路线 (右尺寸, 中考 forcing function)
- **P0(中考前)**: 真题管道 [P0-1 mirror精确删✓done] · 年覆盖断言 · vocab接init_db · cognitive glob(修高考漏年)+中考标unknown · 中考漂移计数走rebaseline.
- **P1**: sources.yaml 驱动 init_db 遍历(消手接Layer) · exam_point 标注产物入仓+覆盖门 · parse_answer单点 · 配置单一来源(d0↔moth去重) · file_manifest生成物改现算.
- **P2(整洁非阻塞)**: 废表sunset · 命名债重命名 · exam_questions_norm view(grain) · stats.py聚合收口 · exam_answer_canonical表(待真消费者).

> 奥卡姆守门(自带对抗 lens): 辽宁就 2 教材版本 + 卷数个位 + 维度有限 → **不造通用扩展框架**(为想象负载建设施=architect-controller规则6死因). playbook 是**轻量约定**(注册表+薄壳), 不是元系统. sources.yaml驱动遍历(P1)是真收敛但非中考阻塞, 卷数真多了再做.

---

## 6. 可维护性保证 (新 session 接手)

1. **单一入口看状态**: `python3 -m scripts.tools.map doctor`(聚合4真相源: project_architecture模块/数据契约 + m0_gates + moth + DB计数). 新 session 第一步.
2. **真相源文档地图**: README索引 → agent.md(现行规则) → 本文件(顶层范式) → architecture.md(八铁律) → 各扩展 playbook(§2). gaozhong-ops skill = 操作+坑库.
3. **扩展照 playbook**: 加任意一类东西先查 §2 对应行 → 改 config 注册表 + 放 data + (必要时)薄壳 module → 三门+年覆盖断言自验. **不照 playbook 散落改 = 违死红线1, stop_gate/codegraph 应抓**.
4. **防漂移**: 真相变化时同 commit 改 moth 断言(弹仓红=回退); 新数据落地坑17(moth AND data_accuracy_check 双门); 改前 codegraph 查 fan-in.

---

## 验收网格 (controller)

- **组件门**: 每类扩展 playbook 跑通 = 改≤2处 + 三门绿 + 自动传导(年覆盖断言非空). 真题管道是首个验收(中考).
- **系统死亡条款**: 感知死→年覆盖断言; 判断死→config注册表覆盖年门; 谄媚死→不适用(无LLM自评回路, cross_verify skip不假过).
- **最小可逆第一步**: 真题管道 P0-1(mirror精确删, 已done f078046)是地基; 次为年覆盖断言(让盲区可见).

**Verdict: PROCEED**. 本设计是轻量约定层(非大重构): 现状三层范式已 ~70% 达标(配置成熟/无god-module/前端干净/4类扩展达标), 缺口集中在 真题卷(#1)+分析维度(#5)两类高摩擦 + 生成物链外 + 基线手敲. 按 §5 P0/P1/P2 增量收敛, 中考为首个 forcing-function 验收.
