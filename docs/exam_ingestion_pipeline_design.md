# 真题入库管道 — 架构优化设计 + 2026经验教训 (中考为 forcing function)

> 立法→控制→执行 (架构师协议). 诊断3维并行Workflow + 对抗critic + controller实证核验 (2026-06-26).
> Forcing function: 中考英语卷几天后上线 = 目标"一条命令 + 三门自动绿 + KG/考点/热点自动传导(能传的)".

---

## 0. 一手经验教训 (2026新高考II卷英语入库实证)

**根因不是入库逻辑差**(xgkii2026_import 本身干净: 复用父连接/幂等/provenance诚实/scope单点),
**而是"加一份卷"未被抽象成单一参数化入口** — 散落在 8-9 处独立真相源, 经约4次全量重建才三门绿:

| # | 痛点 | 根因类别 | 证据 |
|---|---|---|---|
| 1 | 加一份卷手工触碰 **8-9 处** | 设计缺口 | sources.yaml + import模块 + init_db层 + d0_baselines + moth + vocab重生成 + codequality + cross_verify |
| 2 | 同一事实"+8 group"在 **4 处手敲数字** | 手工漂移 | d0_baselines×2(466→474/182→190) + moth×2(镜像同数字) + codequality(12→13) |
| 3 | vocab_classification.jsonl 非init_db重生成却被file_manifest逐文件sha → **重建连锁(~4次主因)** | 传播断点 | 重建→tests_word边变→手跑build_vocab→jsonl的sha变→file_manifest失配→再重建 |
| 4 | cross_verify 假设PDF有文字层, 扫描图触发skip被--strict当fail | 假设过强 | 2026扫描图0文字层 |
| 5 | 常量命名债 `LIAONING_XGKII_2021`/`PAPER_XGKII` 被2026复用(名带2021语义却承载2021+全年) | 命名债 | scope常量 |

**架构耦合 (codegraph实证)**:
- **5 条独立写 exam_questions_all 路径**(mirror/eol/xgkii2026/import_recent/junior中考), 各自手写 DELETE+INSERT。
- **高危: `extraction/exam.py:103` `DELETE WHERE exam_type='高考'` 谓词过宽**(无 source_repo) → 单独重跑会**静默清空 EOL+2026 真值**, 仅靠 init_db 层序侥幸不踩雷, 无防护无断言。
- **build_*_structured.py 在 init_db 链外**(PDF→jsonl), 删了得手工重跑才能 init_db = 不可复现(坑11/22重现)。
- answer 字段 **5 种互不兼容格式**(`which##that` / `[G,E,B,C,F]`list-repr / `D B A`空格 / `56.entirely`编号 / 自由文本), 答案级分析须按源 special-case。

---

## 1. KG/考点/热点传导 — 实证现状 (controller核验 2026-06-26 live DB)

> 你的核心问题"考点、热点变化怎么传导到知识图谱/关联图谱"。实证答案: **半自动, 三处对新卷断**。

| 派生维 | 新卷自动传导? | 2026实证 | 中考预期 |
|---|---|---|---|
| question 节点 / in_year / province / era | ✅ 自动(canonical+links泛读表) | ✓ | ✓ 自动 |
| **tests_word 边**(词→考过) | 代码✅但有洞 | 2026=853✓ 但 **2024/2025=0**(真洞) | 取决于词节点 |
| **tests_exam_point 边**(考点) | ❌ 静态artifact | **2026=0**(genre_theme_labels止于旧年) | ❌ 同断 |
| **cognitive_skill**(设问类型) | ❌ 双重硬编码 | 仅2015-20+2023; `_SUBQ`硬编码`xgkii_2021_2025`不读2026 + 缺2026 anchor | ❌ 锁`exam_type=高考` |
| cooccur/关联图谱(考点共现) | 机制✅上游空 | 2026无(下游exam_point空) | ❌ |
| 越纲率/词汇热力(vocab超纲) | ❌ 链外手工 | 2026手工重生成过(142→157) | ❌ 须记得手跑 |
| trend/scope 分布(题型/热点) | ✅ 干净(直读表) | ✓ 2026自动进2021+era, 样本护栏正确判<10题非slope | ✅ |

**结论**: 题型分布/趋势/in_year **自动传导**; **考点(exam_point)/cognitive/超纲分层 三维对新卷结构性归零**, 且**三门测不出**(无年覆盖断言=感知死盲区)。

---

## 2. 目标架构 (创世层 + 6层设计, controller采纳critic修正)

### 创世层 (死亡红线 ≤3, 不可变)
1. **派生事实禁手敲**: 随卷漂移的计数若仍以 `op:eq` 硬编码散落 d0/moth/codequality, 管道判死。→ 但**用 rebaseline+人审diff, 非 derived:SELECT**(critic: derived 令 expected==actual 永真 = 自废防漂移门 = 坑1假绿)。
2. **链外手工步骤禁存在**: "加一份卷"若需 init_db 之外先手跑 build_*.py 才能复现真值, 管道判死。→ build产物接进 init_db 或显式声明 checked-in 源。
3. **年覆盖不一致禁放行**(感知死): exam_questions 有 (year,province) 行但其应得派生边缺失而三门仍绿 → 判死。必须有 anti-stale 年覆盖断言。

### 设计要点
1. **统一入库**: 向最干净的 `junior/exam.py`(中考)模板收敛 — config-driven/12列模板/`INSERT OR REPLACE`幂等/exam_type判别。抽**唯一 `_upsert_exam_rows(con, rows, *, year, source_repo, exam_type)`** 单点(DELETE按三元组精确), 5路径收编。
2. **数据存储**: 主表 `exam_questions_all` 不动(改它引爆全链); 加 `parse_answer(raw, source_repo)` 单点归一5格式(收编 import_recent 的 `_row_contrib/_fmt_group`)。`exam_answer_canonical` 表 = **镀金缓做**(critic: 当前无答案级分析消费者, 为想象负载建设施)。
3. **基线**: eq锚保留(防漂移核心价值), `scripts/rebaseline.py` 把"手敲"换"现算→写回→打印diff→人确认"。**非 derived**。moth 去重抄(引同一查询或删让 d0 单守)。
4. **KG传导接链**(把三断点接进 init_db):
   - vocab_classification → init_db Layer3末(tests_word边建完后)调 build, jsonl输出**排序确定化**消sha抖, file_manifest对它**改读DB现算非sha比对**(断重建连锁)。
   - cognitive `_SUBQ` glob `xgkii_*_subquestions.jsonl`(修**高考**漏年2024/2025/2026) + anchor门改 **UNKNOWN不剔**(诚实分层)。**中考cognitive≠高考taxonomy → 标unknown不产边, 不杜撰**([[feedback-taxonomy-anchor-not-invent]])。
   - exam_point genre_theme_labels 改 **checked-in源 + init_db校验"artifact覆盖年 ⊇ exam_questions年"缺则FAIL**; 新卷考点需双模型标注产物入仓(死红线2: 链外步骤显式化为"准备源")。
5. **前后端分层**: 前端已干净(JS 0 SQL)。唯一瑕疵 `stats.py:30` 内联 province GROUP BY → 收口 service。**新卷自动上驾驶舱=0前端改动**(全走/api下游派生表, 铁律1红利)。
6. **sources.yaml驱动Layer编排** = **镀金缓做**(critic: 辽宁就2高考版+1中考, 卷数个位且增长极慢; "为加卷=加1行"重构编排器=为想象的"很多卷"建设施)。手接1行import调用 O(1) 即可。

---

## 3. 实施优先级 (controller终裁, 右尺寸非大重构)

### P0 — 中考前必做 (没有=中考重蹈2026覆辙)
| 项 | 为何中考必做 | 风险 |
|---|---|---|
| **P0-1 修 `extraction/exam.py:103` 过宽DELETE → (year,source_repo,exam_type)三元组 + 抽 `_upsert_exam_rows` 单点** | 消灭"单独重跑清空真值"高危; 最小可逆第一步; 不依赖其余 | 低(精确删更安全) |
| **P0-2 年覆盖一致性断言**(死红线3, 进 data_accuracy_check) | 抓陈旧快照+传导漏年(当前三门最大盲区, 2026 exam_point=0 + 2024/25 tests_word=0 都漏过) | 低(加门; 须列已知豁免: 中考cognitive/扫描图) |
| **P0-3 vocab_classification 接进 init_db + 排序确定化** | 中考新词进超纲分层; 断~4次重建连锁 | 低(file_manifest改现算拆P1) |
| **P0-4 cognitive `_SUBQ` glob(修高考漏年) + anchor改UNKNOWN不剔** | 高考2024/25/26补cognitive; **中考维诚实标unknown不杜撰** | 中(诚实分层语义review) |
| **P0-5 中考相关漂移计数走 rebaseline**(zhongkao_total等) | 中考卷zhongkao_total 90→135不必手敲 | 中(一次性对账) |

### P1 — 紧随 (传导完整)
- exam_point genre_theme_labels 年覆盖门 + 2026/中考考点标注产物入仓(需双模型, 标方向性参考)。
- file_manifest 对生成物改"读DB现算"。
- `parse_answer` 单点 + `_row_contrib` 收编。
- gaokao侧漂移计数也走 rebaseline(非中考阻塞)。

### P2 — 收尾 (整洁非阻塞)
- `exam_questions_norm` view(grain标注) · stats.py聚合收口 · 常量重命名 LIAONING_XGKII_2021→_NEW_ERA · sources.yaml编排器(卷数真多了再做) · `exam_answer_canonical`表(第一个答案级消费者出现再建)。

---

## 4. 中考就绪 checklist (卷来时 ≤2 步)
1. **准备源**: `data/junior_high/exams/2026_liaoning/exam_questions.jsonl`(extract_zhongkao产) + 若需考点维则 genre/theme 双模型标注产物入仓。门: 源jsonl行级self-check(列/answer可解析/exam_type=中考)。
2. **`python3 scripts/init_db.py`**。门: 三门自动绿 + **年覆盖一致性断言**(中考有行⟺tests_word边非空; exam_point/cognitive 标unknown豁免)。

> 前提: P0-1/2/3/4 须**先于中考卷落地**, 否则中考重演2026三断点。中考能达成"一条命令+三门绿+in_year/qtype/tests_word自动传导"; **考点(genre-theme)/cognitive两维对中考是结构性空白, 须诚实标unknown不假装传导**(需中考自己的标注源, 非接线可解)。

---

## 5. critic 终裁要点 (controller采纳)
- **基线用 rebaseline 非 derived**: derived 自废防漂移门(假绿), 踩 [[feedback-strong-validation]]。
- **cognitive glob ≠ 给中考长维**: glob修高考漏年(真); 中考cognitive标unknown(中考taxonomy≠高考, 杜撰违 [[feedback-taxonomy-anchor-not-invent]])。
- **sources编排器 + answer-canonical表 = 镀金**: 移出中考关键路径, 待真消费者/真多卷再做。
- 落地顺序: line103 → 年覆盖断言 → vocab接链 → 中考维unknown标注 → rebaseline替代手敲。
