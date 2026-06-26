# RESUME — 断点续传 (新 session 先读这个)

> 配 goal.md + CLAUDE.md + docs/architecture.md 用。本文件 = 最近进度 + 下一步, 更新于每个大节点。
> 🏛️ **平台级最高设计 = `docs/k12_platform_master_design.md`** (第一性原理顶层, 统一高中八铁律+初中子系统+核心竞争力)。新方向先读它。
> ⚖️ **本文件本地立法 (2026-06-26): 禁固化会漂的计数/状态** —— 真题数/图谱规模/moth断言数/词典量等一律**只写"见 `moth assert` + `python3 -m scripts.tools.map doctor` + `backend/config/d0_baselines.yaml`"**, 不在叙事里 hardcode 裸数(否则下个 sprint 必陈旧 = 坑1/坑2 陈旧快照)。历史 session 段里的过程性数字是当时快照, 接手取真值走 live 工具。

## 🎯 交付就绪度裁决 (2026-06-26 复评 — 接手先看这个)
> 详 `docs/delivery_readiness_assessment.md` 顶部"2026-06-26 复评"(2026真题+P0 sprint 后 live 实测 + 5镜头workflow + 对抗critic)。**三场景全 HOLDS, 交付门一格未动**; 计数已刷 live(详该文档计数校正表, 不在此 hardcode)。
- **① 单老师30min桌面pilot = READY**(三门全绿: D0 exit0/stop_gate exit0/moth PASS 0fail; 前端单一入口已收敛✅; 两金矿nav可点渲真数据)。**唯一硬阻塞=动员1名辽宁老师真用**(Rule10, AI做不了)。软阻塞: backup 首份已实跑(`data/db/backups/` 已建); launchd 日备份**用户2026-06-26决定暂不装**(现价值low: DB可复现+学情全合成; pilot真学情落库前再议)。
- **② 多校运营 = NOT-READY**: B1鉴权红线(jwt/bcrypt真实现=0, get_teacher直读query可枚举他人学生PII; 收口点`_tenant.get_teacher`) + B2 Docker/HTTPS/nginx=0。**但用户2026-06-26已主动降多校为"刻意非目标"** → 此为"按决策延后"非阻塞。
- **③ 公开 = NOT-READY**: 学情整条全合成(student_answers全demo seed) + OCR图片链路pending(scan.py仅GET stub) + genre/theme dual_model**零核验**(坑16, 维持方向性标LLM) + 题库薄。**别再无限建KG维度**(核验型机会经2026-06-26实测已基本榨干/证伪)。
- **诚实分**: 真值可卖=题型presence结构迁移+词汇热力四象限+cognitive_skill技能侧(explicit_label)+考试词典(第一手源最值钱); LLM方向性参考(必标)=genre/theme题材分布(零核验, **不可用 tests_exam_point 真值边数顶替这条 caveat**); demo壳(必空态)=学情整条。
- **⚠ 叙事纠偏(critic抓我自己的乐观)**: cognitive_skill "推断28%→47%" 工程诚实层到位(三处标样本量, cognitive边100条全explicit_label), 但**新era 15边100%来自2023单年**(distribution_reliable=False), 是 **1卷1年方向性信号非era迁移结论** — 引47%必同句带"n=15方向性", 别narrate成"命题迁移真值"。
- **门覆盖(2026-06-26 实证, 反坑17)**: `d0_exam_point_check` 有**全局 provenance 不变量**(所有 tests_exam_point 边 provenance∈{dual_model_agree,explicit_label}, 按边属性非按年)→ 2026 新边自动入 D0; 加端点有效+计数门+moth(exam-point-edges-present/xgkii-2026-truth-imported/exam-year-coverage-no-stale)。**新卷传导连门禁都自动覆盖**, 这是中考一键传导的门侧保证。

## 最近 session (2026-06-26 文档对齐): 实际状态对账 + 文档刷 live + 前进计划 (用户: "中考不等了, 更新文档, 结合项目实际制定计划推进")

> 5镜头并行评估workflow(门/文档漂移/工程债/价值核验/交付) + 综合 + **谄媚死对抗critic(REVISE)** + 主线 live 实测裁决。核心发现: **卡点不在"建新东西", 在文档集体滞后一个sprint + README/agent 硬自相矛盾(说"RESUME已删"但它是活跃主交接)**; 价值已不在新增KG维度(核验型机会经实测榨干/证伪)。

**真值快照 (2026-06-26 主线实测, 供文档引用; 数字真相源=d0_baselines+moth+map doctor)**:
- 三门全绿(D0 exit0/stop_gate exit0/moth PASS 107-0); 架构契约 block=0 warn=1。
- exam_questions 474(辽宁190) · question_bank 190 · 考试词典 4396 · student_answers 920(全合成) · nodes 5959/edges 41996 · unit 78 · tests_exam_point 593 · cognitive边100(全explicit_label)。
- **CC裁决(纠 critic 与 eng-debt agent 之争)**: CC>15=**12 = stop_gate baseline 12(贴界未破)**, CC>10=37=baseline。stop_gate exit0 正因 `=` 非 `>`。**CC减债=恢复余量(nice-to-have)非"门已破"**。
- **坑17反查=无缺口**: exam_point D0 check 有全局 provenance 不变量 → 2026 dual_model边自动入门(详顶部"门覆盖")。
- backup 首份已实跑(46MB); 前端单一入口 live 确认收敛(main.py 302)。

**已落地 (本轮 AI 自主, 全可逆文档/校验)**:
- 消硬矛盾: README:5/8 + agent.md:113 "RESUME已删" → "RESUME=断点续传叙事交接(数字引真相源)"; README current law 加 RESUME + d0_baselines 两行。
- delivery_readiness_assessment 加"2026-06-26 复评"段(三场景HOLDS+每条live实证+计数校正表+诚实分层校正); RESUME 顶部刷 live-引用 + **加本地立法"禁固化漂计数"**; goal.md 漂移点引真相源(见下条goal session)。
- **保留诚实caveat不动**: genre/theme"零核验"不换593; cognitive 47%带n=15方向性。

**前进计划裁决 (critic REVISE 后, 价值排序: 交付软阻塞>核验加固>工程债>新建≈不做)**:
- **明确不做(KG-creep红线, 全实测无源)**: cog n=15→60升真值(2022=甲乙卷/2024-25 analysis全空/2021=甲卷冒辽宁) · cog×genre跨era桥(新建维度+两侧不可信) · genre/theme升真值(教研解析无体裁/主题显式标签) · 2026补cognitive(官方评析未出版) · ②鉴权/Docker(用户降多校为非目标) · ③OCR(公开轨L级)。
- **待用户**: 动员真辽宁老师跑pilot(①唯一硬阻塞)。
- **已决**: backup launchd=**暂不装**(用户2026-06-26; 现价值low, pilot真学情落库前再议; 首份手备份已建)。
- **下轮可做(非阻塞)**: 见末尾 backlog。

## 最近 session (2026-06-26 续): 真题入库管道架构优化 + 顶层设计 + 2026考点双模型标注

> 用户: "引入最新高考题后从系统/流程/架构/存储/分析层面优化, 中考几天后来" → "用架构师skill做全局顶层设计, 模块+数据+配置, 可扩展可维护" → "按方案推进/继续/并行"。架构师协议(立法→控制→执行) + 诊断Workflow + 对抗critic + controller实证核验。

**两份设计文档(立法层, 新session先读)**:
- `docs/toplevel_architecture_design.md`: **全局顶层** — 模块+数据+配置三层范式 + **7类扩展playbook(目标≤2处)** + 创世层3死红线 + 治理/演进。实证: 39表/28config/无god-module; 4/7类扩展已达标(前端/教材/词典/KG关系), #1真题卷+#5分析维度高摩擦。承接 top_level_..._20260615 演进。
- `docs/exam_ingestion_pipeline_design.md`: **真题入库管道** — 2026入库经验教训(加一份卷8-9处/4处手敲基线/~4次重建级联) + KG传导gap + P0/P1/P2(中考forcing)。

**P0 落地(7 commit, 全程三门绿)**:
- ✅ P0-1 (f078046) mirror `DELETE WHERE exam_type='高考'`过宽 → 按source_repo精确删(拆"单独重跑清空EOL/2026/中考真值"地雷)。
- ✅ **Layer2a3层序修** (0f844ea) import_pdfs前移(原Layer4g在边构建后)→ **2024/2025 tests_word 0→886/883**(传播洞修复, 真题进KG)。
- ✅ **P0-2 年覆盖断言** (1920d58) moth exam-year-coverage-no-stale: 有辽宁真题文本年份必有tests_word边, 对抗验证真抓漏年。**抓"入库成功+三门绿但KG空传导"盲区**。
- ✅ **P0-3 vocab接init_db** (41c7e3a) build_vocab抽build(con)复用写连接 + init_db Layer3w自动调 + file_manifest排除生成物 → **多次重建级联根治**(中考一键传导)。
- ⏳ P0-4 cognitive漏年 (22a356c 实证裁定=**缓做**): 简单`all→any`有坑3风险(2021唯一marker'Spot'常见词→甲卷假阳性) + 2025/2024大半数据阻塞(源无设问类型解析)。安全路径见doc。
- ✅ **2026考点双模型标注** (f235d73) Workflow 2独立模型标genre+theme → reconcile → genre_theme_labels.jsonl +8条 → **2026 tests_exam_point 0→12**(填exam_point=0缺口; 边界主题adjudicated诚实不建边)。

**中考就绪 = 核心达成**: 加中考卷 = `sources.yaml`一entry + 一次`init_db` → tests_word/vocab/越纲率/考点全自动传导(P0-3后无手工regen+无多次重建), 年覆盖门锁回归。**中考卷到直接走管道**。

**剩余 backlog (2026-06-26 复评后, 全非阻塞; 价值排序+去伪)**:
- ① 2026 cognitive设问类型 = **等外部源**(官方教研评析未出版, group级无subquestion节点; 非AI现可达)。
- ② 2021 cognitive救(补唯一专名marker入truth_anchors避坑3) = **高风险缓做**(2021唯一marker'Spot'是常见词→甲卷假阳性; P0-4已裁缓做)。
- ② -bis **BLOCKED-no-source (2026-06-26实测证伪, 别再挂此项空耗)**: "2022/24/25真辽宁设问标注升新era n→~60" 不可达 — 2022=全国甲乙卷(非辽宁II卷), 2024/25 subquestions analysis字段全空 → 无第一手显式标签源。
- ③ P1 sources.yaml驱动Layer编排(降 init_db.main CC=13 WARN; fan-in近零=重构安全) = 可做, 非中考阻塞。
- ④ rebaseline工具(先给d0_baselines加query字段) = 等"下一张卷"才兑现; 收尾人审diff(非derived防坑1假绿)。
- ⑤ CC>15减债(现 **12=baseline 贴界未破**, 恢复门余量) = nice-to-have非紧急; 拆 readiness._assess_row/eol_review_decisions.validate_decisions(纯校验逻辑) 后降 baseline。
- ⑥ structural-share占比(已验证 structural_truth 再聚合, **非新维度**) = 可做; 前提=分母用真题数/分值真值非presence集合(坑12)+按era分层+配D0/moth(坑17)。
- ⑦ (later)goal.md结构精简: Week65 ledger 迁 analysis/project_state_ledger; RESUME 历史段过程性计数清理。

**工具**: codegraph **1.1.1**(query/callers/impact/affected; 索引最新) · complexity-optimizer skill可用。sprint收尾codegraph审计干净(无CC>15/无坏耦合)。

## 最近 session (2026-06-26): 2026新高考II卷英语真题入库 + 多校轨收口

> 用户: "2026高考英语题出来了, 获取并解析使用; 数据源 t.urongda.com/regions/liaoning; 从数据模块用专用工具非临时脚本" + "多校/多教研员先停在这里收口, 不用管枚举, 先有一个教研员".

**2026 真题全链路 (commit 4c8c854 获取转录 + bff9651 入库)**: EOL官方2026未发布 → 锦宏 jhgk.cn(项目既有 local_pdf 同家族)直链 PDF。
- 获取: sources.yaml `local_pdf_xgkii_english_2026` → `acquire_external_source.py`(fetcher+sha256+manifest, 专用工具非临时脚本)。题面14.7MB扫描图 + 答案493KB有文字层。卷型三源核验=新高考全国II卷(辽宁§7锚定)。
- 题面转录: 12页扫描图 **双通道 ocrmac(macOS Vision)×视觉精读裁决**(坑23), 抓多处单词级分歧(cold≠cool/polite≠busy/完形subject≠account, 均OCR对我初读错)。落 `2026_xgkii_english.txt`(137行)。
- 入库: `xgkii2026_import.py` group级8组(听力/阅读ABCD/七选五/完形/语法; 写作主观题不入=跨年一致) → exam_questions, init_db Layer 2a2 可复现。canonical建10节点+links建边。
- 传播: vocab_classification.jsonl 重生成(真超纲·辽宁考过 142→157, +15合法超纲考点词 breakthrough/cable/determination/steward… 无专名噪声); 越纲率/词汇热力/主题(课标三大主题语境)/答案分布 自动含2026。
- 门: cross_verify_pdf 加扫描图skip(题面真值=双通道转录, D0/moth守, 非假过); 基线 辽宁190/高考474; moth 106/0 + D0 + stop_gate **三门绿**。诚实分层: source_repo=jhgk(tier-B转印官方评分参考, 待官方评析交叉核验); 无逐题cognitive-skill解析不臆造。

**多校/多教研员轨收口 (用户决策)**: `_tenant.py` 记录决策 — 当前=单教研员内网工具(不管枚举); 隔离骨架(owns_student/owns_class+单一执行点 get_teacher)保留作扩展接口, 接鉴权时唯一改 get_teacher 从session派生; 未做(刻意): 登录/JWT/枚举防护/Docker。恢复多校从这几项起。

## 最近 session (2026-06-25/26): 教研室17项 punch-list 全清 — 断链矿口接通 + 全量收敛单一入口

> 用户决策: "先不引入单/多老师验证(②③轨), 把教研室(单用户内网教研员)功能做好做完善" + "全量收敛单一入口"。
> 真相源 = `docs/jiaoyanshi_completion_plan.md`(创世层3死亡红线 + 判断法典 + 17项punch-list + §进度)。
> 性质 = 把"数据算好+API live却前端断链/无矿口/无导出/困legacy"打磨成"主入口app.html一处可达可导出"。**全程三门绿+sherpa GO+verify-the-verifier**。

**高价值批 (#1-5)**: #1词典徽章85%裸码→GZ_CAT.glossSource单点 · #2 exam_point浮窗真题断链(加tests_exam_point+子题分支) · #3考点图可点弹浮窗(GZ.openPopup) · #4浮窗渲attrs教学元数据 · #5 shared导出/打印(exportChartPNG/CSV跨7区)。
**诚实/减债批 (#11/12/14/16/17)**: #11 D区新era视觉降级(灰虚线+方向性叙事) · #12 blueprint练习卷接矿口 · #14 F卡era锁徽章 · #16题库详情内联modal+删死options分支 · #17侧栏live audit。
**收敛批 (#6-10/#13, 全量收敛)**: #6自定义组卷进SPA · #7单元备课tab · #8课节materials矿口(按reason分3层, stage/cefr_level图谱管道滤掉) · #9中考语篇填空逐空考点表(_kaodian_pivot单点+修blueprint senior drop真bug) · #10 word_sense跨阶段多义全链路(/api/word_detail新路由+dict点展开, J4必标"方向性参考") · #13教材浏览tab(14册77单元+PDF+城市版本+跨版本对照, 56单元无匹配诚实空)。
**legacy下线**: /teacher /legacy /index.html → 302收敛到/(Handler._REDIRECTS, ?moved=X前端movedBanner提示); 旧html保留可逆; /student未动。

**verify-the-verifier 抓的真问题**: #2子题EN-XGKII不在qbank需独立分支 · #8 stage/cefr_level纯图谱节点漏滤 · #9 blueprint高中侧p.senior被drop(71对深化全看不见) · #13 cross_version param是unit非unit_id + nav误删teaching行。
**门**: moth 79→104断言(+教研室15条: exam-point-popup/export-print/blueprint/cog-newera-honest/lesson-compose-in-spa/course-session-materials/k12-pivot/word-detail/textbook/legacy-converged等)。新增前端tab: lesson/textbook; 新路由: /api/word_detail · /api/recommend/cities。
**净影响**: 教研员可用性大升(矿口接通+导出+单一入口), 但**②③轨交付门(auth/Docker/真老师/学情真数据)按用户决策刻意未碰** — 交付裁决(①pilot READY/②③NOT-READY)不变。

## 最近 session (2026-06-22 续): 硬编码全局收口 campaign — 两轮 11 commit + 穷尽扫描补漏

> 用户硬约束: "硬编码应从全局移除, 都用模块+数据+配置文件实现." 全程 verify-the-verifier + 行为等价验证 + 三门绿 + moth锁.
> **性质 = 内部重构 (可维护性/架构), 非功能建设; 交付门(auth/Docker/真老师)未动 — 见交付裁决.**

**第一轮 (backlog 驱动, 7 commit)**: `docs/hardcode_removal_backlog.md`. G1 年份权重→year_weights.yaml · G2 卷制era边界→scope单点 ·
  G3 辽宁卷province标签5处→scope(codegraph驱动REVISE: exam_paper fan-in会越线→改scope常量hub) · G4 _SKILL_MAP→taxonomy.yaml(坑16真值验) ·
  G5 stage/类目色→category-config.js · G6 GAOKAO_STRUCTURE→question_types.yaml(weight派生现算) · P2 slope±50真重复→scope.VOCAB_SLOPE_SIGNIFICANT.
  **verify-the-verifier 拦下 5 个 backlog 误判**(不做防过度config): cooccur min_co非bug(explore-vs-persist) / scope-MIN已单点 /
  junior-baselines范围verifier字面 / R3核心map已单点 / VERSION_LABEL刻意语境形式.

**第二轮 (ultracode 穷尽扫描补漏, 4 commit)**: 5-lens Workflow 全新扫全仓 + 对抗式裁决 → 13候选全genuine(backlog漏掉的):
  批A(19e4bda) era_old+paper_type→scope · 批B(deeb15f) 出版社/版本短名→canonical · 批C(c56c39d) 前端维度标签5散落→GZ_CAT.dim+修teacher.html ·
  批D(2cf1800) 6个坑21孤儿config+get_threshold抽中立leaf(backend/services/thresholds.py)+stage_labels单点.
  **抓出2个backlog单审计漏掉的真bug**: ① thresholds.yaml vocab容差漂移(YAML 50/200 vs 代码 100/300, 零消费故没人发现) ②
  前端theme_context标签5文件分叉(主题语境/课标主题语境/主题). 都靠穷尽扫描+漂移检测才现形.

**新增基础设施**: `backend/services/thresholds.py`(中立阈值leaf, 解question_bank/exercise/audit→course层级倒置) · `backend/services/stage_labels.py`(cefr_level→stage标签单点).
**门**: moth 79→89断言(+10: year-weights/skill-map/gaokao-structure/liaoning-label/vocab-slope/paper-type/publisher-version/dim-label/orphan-thresholds/stage-label). 三门全程绿.

## 最近 session (2026-06-22 最新): 命题趋势驾驶舱 v1→v3 — "怎么考"第二轴跨era演变 (核心竞争力)

> 主题: 用户纠偏"课标/真题命题趋势是可感知的真值, 万变不离其宗, 你的作用是总结分析" → 顶层设计 `docs/exam_trend_design.md`
> (改造优先非新建)。三轮递进, **全程三门绿 + commit**(起点接上一 session 真值体系)。

**v1 (题型presence)**: `trend/raw.py::question_type_era_presence` — 题型×卷制era presence矩阵(provenance=structural_truth,
  **粒度无关**避2021/22子题坑)。骨架(阅读/完形/七选五/语法填空两era皆在) + 退场(短文改错末2020) + 登场(听力2021/续写2024)。
  内容门 question_type_era_structural_truth + 前端 beike C面板(题型×year presence热力)。

**v3 (跨era设问演变, c048e5f) = 本 session 主交付**: 第二轴 `cognitive_skill` 从单年(2023 15子题)扩到**跨两卷制era 100边**,
  解锁核心竞争力"命题哲学迁移"真值: **推断 28.2%(旧课标全国II 2015-20) → 46.7%(新高考全国II 2021+)**, 细节 54.1%→40% 下行
  = 新高考重高阶推断。
  - **改造优先零新表**: `cognitive_skill.py` 加 `_legacy_reading_rows` 第二真值源(2015-20 reading 子题前导题型, 两格式
    `_FA`/`_FB`); 抽 `_emit_subq` 公共入图(load CC↓)。真值门 = exam_questions **refine后 province**(辽宁新课标II,
    坑3 provenance-aware 单点真值 — 区别 subq jsonl 误标风险故不另设anchor)。变体题型只映射明确同义, 模糊3子题诚实skip 防臆造。
  - **诚实护栏**: `cognitive_skill_distribution` 加 reliability 每-era标记(复用 scope.MIN_DISTRIBUTION_SAMPLE 不hardcode):
    旧era 85≥30分布可靠 / 新era仅2023 n=15<30 **方向性非精确**。前端 D面板双era分组条形 + caveat。
  - **门**: D0 `d0_cognitive_skill_check` 重写(100/85/15/源年集/迁移真值/explicit_label/血缘) + content gate
    `cognitive_skill_era_shift_truth`(交叉相乘锁推断新>旧, 对抗验证非假绿) + moth 跨era改写 + d0_baselines 3基线。
  - 验证: init_db 全量重建 100边复现; 三门全绿(D0 exit0 / moth PASS 74-0-0 / stop_gate exit0); preview D面板渲染正确0 error。

**v3后续 (同session, 勘测workflow驱动)**: 5路并行验真相源 + 架构师裁决 → 选最高价值增量, 改造优先落地:
- **#1 设问技能×题材/主题 交叉 view** (048d996): 复用跨era cognitive_skill(explicit_label真值)×genre/theme(passage级)
  → **应用文100%找信息(0推断)/文学艺术100%找信息 vs 说明文42%推断** = 老师"哪类语篇考哪种思维"分流决策。
  `cognitive_skill_by_content(con,by)` 单一计算点; **最小验证抓到关键对齐**(passage_label裸qid vs genre边'question:'前缀,
  字面join 0/85→规范化后74/85)。异质provenance诚实分层(技能=真值/题材=模型推断, 非真值交叉); era锁2015-20(2021+桥缺失);
  粒度=子题数+thin格<10护栏。D0项31 + moth + 前端F区(100%堆叠条+genre/主题切换)。**诚实不建**: 干扰项(辽宁仅1篇)/跨era交叉/信息位置。
- **#3 raw_question 页中水印清洗** (bae72b7, 坑18续): local_pdf 2024-25 锦宏/学科网 mock-PDF 每页页脚(公众号/客服/页码)
  mid-passage注入污染15行(4下游)。`extract/pdf.py::_strip_watermark` 按行剥(正文0丢失, 仅删水印微信号'jh') + D0 + moth; rebuild自动清。

**v2 题型presence提取完整性掩码** (51778ed, 坑12诚实修正, backlog#2): v1 把听力/续写"提取年"误当"登场年"(artifact)。
v2 加卷改结构真相源 `backend/config/exam_structure_eras.yaml`(canonical题型+extraction_gap掩码 by era, §3.5数据化),
signal 改由**卷面结构**(非数据presence)定: 短改=真退场/听力=skeleton+缺源(≠登场2021)/续写应用文=真登场+缺源(登场年不可信)。
`raw.py::_era_structure`单点+`_qt_signal`; D0项23 + moth + C面板缺源格淡色虚线。

**待办 backlog (2026-06-26 复评纠偏)**: ~~cog×genre 跨era版(补passage_label桥)~~ **删除** — 新建跨era交叉维度违"别建KG维度"红线, 且新era侧 genre/theme 未核验(坑16)+n=15, 交叉=方向性×方向性不可下结论(与本节"诚实不建跨era交叉"自洽) · ~~2022/24/25真辽宁设问标注~~ **BLOCKED-no-source**(2022甲乙卷/2024-25 analysis全空) · **structural-share占比 = 唯一可做项**(structural_truth再聚合非新维度, 见顶部 backlog⑥) · 旧口径收口。

### 三路并行推进 (2026-06-22, 6-agent勘测workflow + verify-the-verifier 驱动)
> 用户"都推进": 防御性内容核验 + 交付收口 + 采集可行性 三路并行验后 inline 执行。**全程 verify-the-verifier**(agent输出=证据非定论)。

- **采集 (C1) — 诚实天花板**: 2024 cog "可本地采"是**坑3陷阱**(gaokao_bench_2024="Harvard"=全国I卷, 非辽宁II"Carlow"; smoking-gun救场, 我原判断对); 2022/25 教研解析确无前导题型。新era cognitive_skill 数据封顶2023, 扩量需外部辽宁II卷教研解析采集(授权)。
- **防御核验 A1 (2e5b44d)**: phrases.sentence_pattern 32%污染(进lesson_plan老师可见) — regex .*+DOTALL跨段 + such as/形式主语/so that误命中。修: 去DOTALL+负向断言+evidence=匹配span+'强调句'据实改'It is…that句型'(229→65, 0误命中); D0 `d0_phrases_check`(项32, **phrases此前零D0=坑17盲区补**) + moth。
- **防御核验 A4 (20fccdb)**: renjiao变体拼写词丢失(organise等12词) — 纠agent误诊("加列裁剪"已有), 真因=**变体标注'(NAmE -ize)'夹词与IPA间** `_ENTRY_HEAD_RE`失配。修: 允许可选变体标注(2206→2214 +8词, 0回归); content gate `renjiao_variant_words_present`。**诚实残留**: gloss bleed 194→187(短语'X high school'+页眉吸入未修, 需per-unit dry-compare careful, 精确flag).
- **交付收口 B1 (f29ccec)**: exam_vocabulary金矿(4186词)有API无前端→ 新建 `frontend/static/dict.js` 考试词典tab(前缀检索+阶段过滤+provenance徽章[教材/中考/COCA]+辽宁高考命中真值), app.html加📕入口。preview验4186词可检索(organise可见).
- **未验**: A2(KG边语义)/A3(答案逐题)agent ECONNRESET挂未出结论, 不算clean, 待补。

全程三门绿(D0 exit0 / moth PASS 78 / stop_gate exit0), 全推 origin/main。

---

## 最近 session (2026-06-21): 真值校验体系 + 内容门框架 + 5大交付数据钉PDF + no-hardcode

> 主题: 根治"为啥每次检查都发现新问题" = 旧三门只验**自洽**(计数==快照)不验**真值**(内容==第一手源),
> 自洽棘轮把内容偏离锁成绿。本 session 建真值校验体系 + 内容门框架, 把"只计数验过"的盲区逐一对第一手源核完。
> **全程三门绿, 全推 origin/main。** 起点接 KG 层(上一 session)。

**① 真值校验体系 (根因根治, 模块化)**:
- `backend/services/truth_baseline/` (CHECKERS dispatch + TruthChecker ABC + self_test 对抗自测) + `truth_anchors.yaml`
  (锚=第一手源指纹, lifecycle active/no_anchor, ≥2源才立锚) + `truth_check` CLI + 接 D0 门 `_check_truth_anchors`。
- 标准文档 `docs/truth_anchor_protocol.md` (方案→标准→验证→持续完善)。释义PUA清洗(保守 _clean_zh_def) + GlossaryTruthChecker。

**② 颠覆性发现: 杜撰课标"第三级"theme_l3 已废** (34c55d9): 亲验课标PDF表2 — 官方主题语境**仅L1(3)+L2(10)可枚举**,
  "第三级"是32条段落式内容要求(非词条)。库内35个theme_l3=杜撰(extract `_reader`不读PDF直接塞 + dual_model贴标签) +
  131条边/35节点。删源重建(6-agent workflow穷尽血缘) + truth_anchors theme域 + ThemeTruthChecker + D0/moth 防回归锁。
  教训: **真相源双用途 — 向下校验对错 AND 向上对标天花板; taxonomy 必锚第一手源最深可枚举层, 不发明子分类追ceiling**。

**③ 内容门数据驱动框架 (回应用户3次"模块化可扩展可复用")**: `backend/config/content_gates.yaml` + `ContentGateChecker`
  单引擎。**加内容门 = 加一行YAML(query+op+expect+源)**, 自动接D0+CLI(单一真相, 不再D0 AND moth各写一遍)。
  ⚠ 对抗救场: 框架初版`_GATES`路径错→`load_gates()`返空→引擎跑0门却报"0偏离"=**框架自己犯绿门假绿**, 对抗注入才暴露 → self_test加"注册表非空"锁。

**④ 5大教学交付数据钉PDF (穷尽内容核验sweep → 逐项修+内容门)**:
| 偏离 | 修 (单一计算点) | 内容门 |
|---|---|---|
| in_curriculum 假源列(硬编码True谎报越纲47%) | run_vocab 从cefr现算 | content_gates |
| cleaned_judged LLM覆盖交付级词典 | word_sense 去覆盖, 退回真值源 | content_gates |
| 13 waiyan标题截断 / 81垃圾义项(`（`碎片) | _scan_scope_page续行join / _clean_zh_def去前导语法括号 | verify_titles_vs_pdf / GlossaryTruthChecker |
| COCA 84专名噪声 / cefr 44级别错 / grammar 4截断 | _strip_coca_pn / 全行捕星 / _merge_continuations | content_gates 3条 |
| **renjiao 1957→2206**(召回88.5%→99.7%) | _PHRASE_HEAD_RE短语词条 + 双栏reflow头前词派生回填 | renjiao_phrase_present |
  途中内容门**当场抓住3个自引入回归**(PUA fallback/框架空路径/污染门假阳性) — 对抗验证不能省。

**⑤ no-hardcode (用户指令)**: renjiao首单元号硬编码`1`→派生回填; **22个D0计数基线**(cefr3052/grammar108/高考466/182/中考90…)
  收进 `backend/config/d0_baselines.yaml` + `B('key')`读取。改基线=改一行yaml。

**坑15流程修**: junior_accuracy_check 锁容错(DRY抽共享 `scripts/lib/db_lock.py`, init_db重建时不假失败)。

---

## ⏭️ 优化后的计划 (2026-06-21, 接手先看这个)

> 大局: "数据100%准"地基这一 session 从"计数自洽"升到"内容钉第一手源"。**核心竞争力地基与时间跨度的结构性矛盾**
> 已识别(能跨11年的genre/theme全是LLM推断) → 核心竞争力对外口径 = "**分卷制分布迁移 + 命题模式识别 + 教材对齐**"
> (样本量逼出的诚实结论, 非逐年微观趋势)。
> ⚠ **2026-06-22 更新**: "唯一真值锚cognitive_skill单年n=15" 已**部分突破** — v3 用 exam_questions refine省份门 把 cognitive_skill
> 扩到跨era 100边(旧课标II 85 + 新高考II 15), **推断28→47%迁移**已是带门真值结论(structural_truth级)。新era仍n=15方向性,
> 但"考查方式跨era演变"不再是纯LLM/单年 — 这是核心竞争力第一个真值跨era信号。

**A. 真值诚实标注 (防"又一个theme_l3")**: genre/theme_context/theme_l2 481边=dual_model推断, 无第一手源 →
   前端/分析层标 `LLM辅助分类·非考纲官方`(不做命中率未知的"交叉验仪式"=过度工程)。

**B. 内容核验下一层 (sweep已列, 有限可枚举, 非黑箱)**: phrases表 / KG边语义 / qbank停用词残留 / weakness派生(真实答题0条) /
   course audits内容 / **raw_question题干**(只核了answer列, 坑18题干可能bleed卷尾) / 2015-2020+2023-2025答案逐题核 /
   其余6册unit_vocab逐册 / renjiao残留污染(（-起首短语/表头噪声)。每项: 对第一手源核 → 内容门(加content_gates一行)。

**C. no-hardcode 续**: extractor 页范围/正则 + 其余阈值(orphan_ratio/CC baseline)增量迁配置。

**D. 交付收口冲刺 (delivery_readiness_assessment.md, 仍是最高杠杆)**: 统一前端入口 + 金矿(词典/word_sense)接前端 +
   学情空态引导 + Docker+最小鉴权 + **1名辽宁老师30分钟真试用**(唯一独立真相源, 别让"还能建更多"无限延迟它)。

**E. 真实答题入口 (战略, 压后)**: 全平台0条真实学生作答(student_answers全md5合成) → 学情/弱点/热力/推荐全demo空壳(已诚实标)。
   要真交付学情需 答题卡OCR / 在线作答 / 成绩单导入。

---

## 最近 session (2026-06-20 最新): KG 层大建 (设计→P0→词典→word_sense→关联性) + 交付就绪度评估

> ⚠️ **下一步 = 收口冲刺 (operational sprint), 不是继续建 KG 维度**。详 `docs/delivery_readiness_assessment.md`。

**KG 层从设计到落地** (11 commit, 全推 origin/main, 全程三门绿; `docs/kg_layer_design.md` 设计定稿):
- **设计** (cf5a421): 3 轮 workflow → amend master design。用户 2 决策: 两腿并行 + 消费产物。
- **P0 横切地基** (13c0d0b): `source_versions` PIT 注册表(键=kind,variant) + `effective_version` 单一PIT点 + **`stamp` 写边即带血缘**(不回填) + 数据驱动 dispatch (D0 407→358)。
- **A1 设问类型金矿** (1529b4f + 前端 82b5e7a): cognitive_skill 子题级"怎么想", **推断50%** 对账教研解析(驳 inference 错估15%, 坑16); 上备课驾驶舱 D 区。
- **B轨 verify-the-verifier** (1d5d2de): 红队"DB粗分阶红线"误读 — at_stage 边早已细(3095词0错指), 否决错误回填, 锁 correctness 门。
- **考试词典** (3198cb7+b0763f1): `exam_vocabulary` **4186词99%释义**, 课标∪教材真超纲(最小无注水), 三源溯源, 释义=教材生词表→中考词汇表→COCA兜底交叉引用。
- **word_sense 本体** (bb09878, master A1): 404候选→21-agent workflow(锚定释义判断+对抗验证过度检测305→142)→ **142真多义** word_sense节点+has_sense+expands_sense (ceiling→上限/china→瓷器)。修词典OCR污染142词。
- **关联性** (50fa9c5+c9d8cd3): co_occurs 考点共现(记叙文×人与社会46) + characterizes_theme 主题特征词(plastic→环境49)。
- D0 28→36项, moth 61→70。

**交付就绪度评估** (8-agent workflow): 距交付**一个收口冲刺**。4 项门 2 绿(数据/三门)2 缺(**Docker完全无 + 真老师试用从未发生**)。最高杠杆=动员1名辽宁老师30分钟试用(Rule10, 也是范围裁决器)。收口路径: 用户拍板形态+范围 → 统一前端入口 → **金矿(词典/word_sense)接前端** → 学情空态引导 → Docker+最小鉴权 → 真老师试用 → 按反馈再建。**别让"还能建更多KG维度"无限延迟真老师校验。**

---

## 最近 session (2026-06-20 续): 全面审计 (13-agent workflow) + 20 真问题整改 19/20 闭环

**全面审计** (架构师/moth/sherpa + 13-agent workflow 7 维度): 验证-验证器, 抓 20 真问题 (三绿门盲区, 坑1/坑21 复发), 6 假警报正确排除。**整改 6 commit 全程三门绿** (932dddc→acc885f):
- **P0 多租户 BLOCK (5项, 用户硬约束)**: inc6 只 scope 1/7 端点, live curl 实证 t-li 可读 t-wang 学生全档案/弱点/列表 = 越权。修: `_tenant.py` 归属判定单一执行点 (owns_student/owns_class 经 classes 链) + 全 7 端点强制 teacher_id + IDOR 防护 (import_csv 拒跨租户接管) + D0 `_check_28` **行为级门** (真调路由跨租户必拒, 非仅结构) + moth 行为断言。教训 L-ZE/坑24 (隔离声明≠全端点隔离)。
- **P1 HIGH (5项)**: ① 答案保真门 (中考MCQ按题型∈{A-D}/{A-E}, 2024 answer-key全非空) ② 高考计数正向锁 466/182 (B1去重后非陈旧472/188) + 改全部陈旧文档 + moth 17→60 ③ deepens 衔接补全 (label精确漏12时态/非谓语/定从 → grammar_stage_aliases.yaml 数据化, 59→71 全初中语法无衔接孤儿) ④ 中考90题空心诚实标记 (zhongkao_questions.content_status 派生列 + 前端banner: 2024全walled/2025答案待补) ⑤ beike命题迁移做差下沉 exam_point_shift service (Rule1)。
- **P2 MEDIUM (7项)**: sherpa fail_regex 假阳性收紧 (坑21坏门) / phrases 双定义删死代码 / class_weakness agg下沉service / stage未分阶1234词披露 (校本超纲1094+课标变形140, 防静默截断) / JSONL↔DB答案对账moth / beike .catch / **ECharts 本地 vendoring** (用户选; 下载 5.5.0 到 frontend/static/vendor/ 去 cdnjs CDN 供应链风险, moth锁无CDN)。
- **20/20 全闭环** (7 commit: 932dddc→2459a0f); moth 17→61。
- 前端全部浏览器实测 (2 诚实banner + 命题迁移 + 本地echarts v5.5.0 + 0 console error + 截图存证); fresh schema in-memory 加载验证 init_db 可复现。

## 最近 session (2026-06-20): K12 入库 inc1-6 全完成 + 前端4页 + 强验证修复

**A. 强验证 (独立重推导)**: 8切片并行从第一手源重推导→比对→对抗确认 (`docs/data_validation_design.md`); 抓6区真错全修 (高考2024辽宁双源去重/2025中考parser/课标三级清洗按官方口径/沪教截断/五选四/grammar label); ocr_image 可复用裁决模块。**关键**: 三门测自洽不测源保真度, 强验证补盲区。

**B. 数据可视化+前端**: understand+design 工作流(3提案收敛=教师驾驶舱) → 4页落地 (app.html SPA 扩展, 全 vanilla JS + ECharts 单算点不重算):
- 🎯 备课驾驶舱: 考点分布(era分层)/命题迁移/趋势(reliable护栏灰显)/词汇热力
- 📖 讲课调取: 概念浮窗4路追溯(复用graph_popup) + 考点关联力导图
- 🔗 K12衔接: stage阶梯 + 10维语法蓝图59对 + 中考题型
- 👥 分析学生: 多租户(teacher_id隔离) + 班级学情热力 + demo banner

**C. K12 入库 inc1-6 全完成** (`docs/junior_db_integration_design.md`, architect 设计+approve): 单库三判别维(node_type/stage/exam_type) + 两大域(共享知识图谱/多租户学情):
- inc1 中考90题入库 (schema模块化7域文件 + exam_questions_all物理表 + **高考视图隔离零回归** + 修cross_verify回归)
- inc2 初中112词+71grammar:jr节点 + stage节点 + at_stage边防孤儿
- inc3 stage回填(3095高中词at_stage) + **10维蓝图59 deepens边**(中考∩高考)
- inc4 K12 API (services/k12.py单算点) / inc5 K12前端页 / inc6 多租户(2老师隔离+析生页)
- 全程三门绿; 每增量独立commit; 9个commit (656c448→9e658d2 已push)

## 最近 session (2026-06-19): 中考 2024+2025 结构化 + N=2 语篇填空"10维语法蓝图"发现

**C 阶段中考真题按高考标准做完** (2024+2025 两年, junior D0 F9 守门, 对抗验证)。
- **结构化双路径** (`scripts/extract_zhongkao.py`, 高考 schema):
  - **2025 题面驱动**: Scribd 页图 OCR×视觉 → 45题 (题干+选项, 22 MCQ options, 10 语篇填空考点)。
  - **2024 答案key驱动**: 中考网官方答案图 11.png(637x673) **paddleocr×视觉裁决**(裁3块放大4x精读, 与 PaddleOCR 1-40 全一致, 初次扫读误差纠正; 19.E 确认 17-20 五选四) → 45题全官方答案 + 10 语篇填空考点。题干各免费源全门控(Scribd学科网水印空白/kaosheng登录/中考网仅答案/教习网滑块/学科网付费), 标 `stem_status=walled` **不伪造**(mio 失败先承认)。
- **D0 门** (坑17/坑21): junior_accuracy_check 加 **F9/F9b 中考校验**(每年45题/id唯一/辽宁§7/题型分段不变量/语篇填空考点全; 2024 全45官方答案+MCQ∈{A-E})。已接 stop_gate 1c, 对抗验证(污染Q19→exit1, 还原→exit0)。全函数 CC≤10。
- **发现 (N=2 实证, `docs/zhongkao_gaokao_alignment.md`)**: 中考语篇填空 = **固定 10 维语法蓝图** — 2024+2025 逐空覆盖**完全相同的 10 个语法维度**(连词/被动/名复/冠词/非谓语/时态/比较级/介词/副词/代词), 仅词例不同(非随机出题); 且这 10 维 = **高考语法填空考点全集**。→ 这 10 点 = 平台最高优先级地基 + 跨阶段 `deepens` 边已验证种子(真卷实证非 LLM 臆测)。诚实边界: N=2 是蓝图快照非趋势(坑12)。

## 最近 session (2026-06-17): 高中地基重审根治 + 初中子系统立项

### A. 高中数据地基重审 — 18 项数据正确性问题全清 (已 push)
前轮 14-问题审计 + 本轮对抗复核新发现 4 项, 全部根治。**三门全程绿** (D0 exit0 / moth PASS46 / stop_gate exit0)。
6 个 commit (e2dfc59→80e930c, 已 push origin/main):
1. **renjiao/waiyan 词表单一区段重写**: 跨单元重复 331+96→0 (字母总表/glossary 砸进尾单元污染); bixiu_2 U1 56→66; cefr 3055→3052(截国家表误纳)。
2. **exam-status 单一计算点** (#12/#13/#14): province-blind(§7违反) + 3处各算 + attrs整段覆盖 → 收口。grammar_4q 孪生同修。
3. **「考过」判定收口到 tests_word 边** (Rule1): core-无边 347→0 (你指出 token-bag vs 边不一致); build_tests_word 改 lemmatize+覆盖 cefr∪教材词。
4. **section 边界+截断** (#7/#9): 过宽 section 8→0(末单元吞 workbook/glossary, waiyan锚点cap + renjiao unit_overrides); section_text 20000截断 28→0。
5. **EOL 真题截断** (#8): raw_question 900硬截 11→0 + 空白13→0; 辽宁阅读 AVG 361→637。
6. **代码债**: data_accuracy_check<400 + _from_outline CC11→10。

教训沉淀: 每条修复都加 D0断言+moth(坑17双门); 门会假绿(坑1)——前轮审计漏 331/96 重复且其提议反是根源, 再审 Workflow 也误火过, **直接查 live DB 才靠谱**。moth coupling 验证: 单一真相拓扑健康(tests_word fan-in26=canonical读, 0孤儿引用)。

### B. 初中 + 中考 子系统 — 立项 + 顶层设计 (Phase 0 进行中)
用户立项: 拉沈阳中考+初中教材/课标, 像高中一样标注, 将来打通成"初中+高中统一平台"。
核心洞察: **stage 标注**(with/the 是小学词非高中词, 标 stage 后处理方便)。
- **顶层设计**: `docs/junior_high_subsystem_design.md` (architect-controller: genesis层 + stage原语 + separate-build-merge-later)。
- **已有资产**: 义务教育课标2022 PDF(三级体系,词汇表p94-152/语法p116,145) + 初中教材人教5册+外研6册 + renjiao_vocab.txt(4578)。
- **缺/待核**: 沈阳中考真题(命题方/卷型/源) + 沈阳初中教材版本(§1.4≥2源)。研究 Workflow wq9lacnsp 核验中。

### C. K12 分阶段 — 主业即时步 S3 落地 + 设计深化 (2026-06-17)
- **S3 stage 标注 (主业)**: 高中 word 节点加 `attrs_json.stage` (cefr_level 派生)。**with/the/and=义务教育**(修用户指出"非高中词处理不便", **tag-not-exclude 不删**)。分布: 义务教育1580/校本超纲1134/高中选修985/高中必修487/课标变形143。D0 加2断言(每分类词带stage + 义务教育==cefr义教1580)。单一writer exam_coverage 写。三门绿(moth PASS46)。
- **设计深化**: junior_high_subsystem_design.md §10 加**双向贯通+跨阶段语义扩展5维**(词义扩展/搭配/语法deepens/语篇/思维品质/主题spiral + 回溯补救+受控渗透+评估轨迹)。删重复 k12_staged_platform_design.md。
- ⚠️ power 案例: 当前 stage=高中必修(仅高中cefr口径); 用户举 power=初中力量 → 待 S1 初中三级加载后 S4 reconcile 重标。

### D. 定位已决「服务沈阳本市」+ 沪教牛津已获取 + Phase1 课标落地 (2026-06-17)
- **定位拍板 = 服务沈阳本市** → 主用版锚定**沪教牛津(广深沈通用,上海教育出版社)**; 中考=沈阳省统一卷(2024起)。
- **沪教牛津6册已下** `data/junior_high/textbooks/hujiao/{7a,7b,8a,8b,9a,9b}.pdf` (gitignore同高中, manifest track): 源 TapXWorld/ChinaTextbook(同高中渠道), §1.4 双源核验(版权页**辽宁批文[2018]3** + Oxford原作者 + 六三制7-9 ≠上海五四制 + 美英桥)。⚠️ 文本层 InDesign 乱码**待 OCR**(同高中坑)。⚠️ 别混同目录沪外教版。
- **Phase1 课标抽取**: 义务课标2022 → curriculum_vocab.jsonl(1647: 小学502+初中1145, 三级1593/1600 CMap漏~7不凑) + grammar(66)。stage切分用集合交(不靠损坏星标)。S4桥接: 义务∩高中义教=1333(84%)。
- **sherpa init**: `.sherpa/takeover.yaml` 定制为本仓3门+真相源(D0/stop/moth/map/junior), `sherpa takeover --repo .` 可用。

### E. Phase 2.5 — OCR 全局持久化 + 沪教词表 + S4 双向 stage reconcile (2026-06-17)
- **OCR 工具链全局持久**: PaddleOCR 官方装 `~/.venvs/ocr` (paddle3.3.1+paddleocr3.7.0), 全局入口 `ocr-python`/`paddleocr` (PATH 已含, **跨项目可用**), 模型缓存 `~/.paddlex`。docs/junior_high_ocr_setup.md。
- **纠正"文本层乱码"**: 沪教文本层**大体可读**(7a 122/138页), agent 的"全乱码"错(它用pymupdf)。**CID 只污染中文释义, 英文 word 可读** → stage 词表文本层全抽, OCR 仅补释义。交叉验证: 可读页文本层抽词 **171/171=100% 被OCR确证**。
- **沪教6册词表 926 distinct** (extract_hujiao_vocab.py): 首现去重 per-grade(七上159...九下127); 9b 29页累积总表回填 CID 卷释义 → **仅26释义待OCR**。∩课标三级=648(70%)。
- **S4 stage reconcile** (junior_stage_reconcile.py): 初中源(课标二级=小学/课标三级∪沪教=初中)细分高中 4329词 → **1763(40%)更精细**(义务教育1580→小学499+初中1264); **298 语义扩展候选**(power✓: 初中力量→高中power plant, design§10 边种子)。emit stage_refined.jsonl。

## 当前真相源 (live, 不引旧数字)
- 高中主门 (exit0/PASS): `data_accuracy_check.py` + `stop_gate.sh` + `moth assert` + `map doctor`
- 初中产物: `data/junior_high/structured/{curriculum_vocab,grammar_items,hujiao_vocab,stage_refined}.jsonl` (**尚无独立 D0 门** — 审计待补)
- 接手对账: `sherpa takeover --repo .`

### F. gaozhong 完全独立 + 主架构 v2 + Phase2.6 初中地基修复 (2026-06-17)
- **gaozhong↔gaokao 完全独立**: 切断 2 处运行时跨项目读(gaokao_bench/truth_baseline → 本地镜像);
  init_db 自包含复现 466/182 (B1双源去重后, 原472/188 含6个2024辽宁重复); moth gaozhong-self-contained 守门。"不ATTACH"=跨项目非初中↔高中。
- **主架构 v2** (`docs/k12_platform_master_design.md`): 第一性原理 + 3视角对抗评审定稿(REVISE);
  sense级stage(power自反驳word单标签) + 单库node_type(弃双库三态) + 补学习者/语篇/思维节点 + tutorial契约。
- **Phase2.6 初中地基修复 — 初中 D0 全绿**: 建 junior_accuracy_check(8不变量, 坑17) + 接 stop_gate
  阻断路径(坑21, 对抗验证污染→exit2)。OCR 交叉验证(master§3)洗净课标: F1垃圾51→0 + goal恢复(glyph误解码)
  + F4沪教cid 176→0 + F6语法66→71 + 契约注册。词典门已证不净, OCR=视觉真值。

## 下一步 (Phase2.6 完成, 地基达标解锁 A/B/C)
- **✅ C. 沈阳中考真题** (2026-06-19 done): 2024+2025 省统一卷结构化(junior D0 F9) + 中考×高考对接发现(题型全对齐 + 语篇填空10维语法蓝图=高考语法填空考点全集)。**余**: 2024 题面 stem 待用户提供 doc 补全(各免费源门控); 第三年真卷可得后验蓝图稳定性。
- **A. Phase3 集成 (单库)**: stage_refined 回填高中 word 节点 stage + word_sense 节点(义项级) + 跨阶段 edges。**中考语篇填空10维 = `deepens` 边已验证种子**(可优先落)。
- **B. 语义扩展边** (依赖 A+C): 298候选→跨stage语料 NLP pipeline → expands_sense/collocates_into。
- 余: F7 二级补转写3词(502→505, 低优先); F3 沪教*超纲词召回(926→~1200, 门现800-1400放行)。

## 真相源/门 (live, 不引文档旧数字)
- D0: `python3 scripts/data_accuracy_check.py` (exit0)
- 门: `bash scripts/stop_gate.sh` (exit0) + `moth assert --repo .` (PASS) + `moth coupling --repo .` (孤儿引用)
- 全库重建: `python3 scripts/init_db.py`; 重建后必重生成 `python3 scripts/build_vocab_classification.py`
- 状态总览: `python3 -m scripts.tools.map doctor`
