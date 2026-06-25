# 教研室内用功能完成度 — 法律 + Punch-list + Loop 协议

> 用户 2026-06-23: 搁置真老师 pilot/多校验证(②③轨), **聚焦把"教研室内用"功能做好做完善**。请 AI 设 /goal + /loop 自驱。
> 立法 = architect-controller; scoping = 7区审计 Workflow + 总指挥综合(去镀金) + controller verify-the-verifier(#1/#2 已第一手核实为真)。
> **本文件 = /goal 与 /loop 的单一真相源。** 进度更新在 §进度 + docs/RESUME.md。

---

## 创世层 (immutable, stranger-testable)

**为何存在**: 平台真值底座(真题466/词典4186/趋势驾驶舱/教材77单元/题库164/KG 5948节)已建且三门绿, 但很多功能"数据算好+API live 却前端断链/无矿口/无导出/困在 legacy 与 /teacher" —— 本引擎把它们从"工程自证就绪"打磨成"**教研员在主入口 app.html 一处可达、可看懂、可导出带走**"的完整内用工具。

**死亡红线 (≤3, 越则跑偏)**:
1. **碰②③轨** = 死: 不动 student_answers/students 假学情当真值、不为合成 demo 补 OCR 批改、不建鉴权/Docker/多租户。学情必空态+demo banner。
2. **建新 KG 维度/算法** = 死: 不新增节点/关系类型/分析维度/命题轴/图算法。真相源(genre/theme dual_model)未经真老师校验, 加=违反分层非平均+反奥卡姆。**只接通"有数据点不到"的现有矿口**。
3. **破诚实分层 / 三门红** = 死: LLM方向性参考(genre/theme零核验、cognitive_skill 新era n=15全2023单年)不得渲成与真值同等的实色/精确斜率/强调色; demo/walled/answer_pending 不当完整内容展示; 任一改动后 D0/moth/stop_gate 任一红不许 --no-verify 跳过。

## 判断法典 (evolving, 人话 + 机器话)

| # | 人话 | 机器话 (可执行) |
|---|---|---|
| J1 | 做完善=完成现有, 非发明新的 | punch-list 每项 scope=in-scope(completion/polish/接矿口/导出现有); 任何 out-gold-plating/out-deferred 项 loop 拒做 |
| J2 | 接矿口走单一计算点, 前端纯渲染 | 新端点必是 backend/services/ 单算点薄壳; 不在 API/前端/脚本重写 JOIN/agg (铁律1) |
| J3 | 重构/收口项行为等价 | byte-identical / 派生量现算 验证; 改判定逻辑 dry-compare 前后 |
| J4 | 诚实分层标注不得移除或弱化 | 前端产物的 真值/LLM方向性/demo 标注保留; 不可信(reliability=false)必降级灰+虚线+banner; moth 锁 |
| J5 | 每项三门绿 + 行为核验才算 done | D0 exit0 + moth PASS + stop_gate exit0; 新API curl :8765 实测真数据; 前端项 preview/核验渲染对得上 DB 真值 |

## 死亡条款 (system-level falsification)

- **感知死**: loop 不跑三门/不核实 live 就 commit; 或 commit 信息声称完成但未 curl/preview 验证。→ 每轮强制 §loop 步骤4-5。
- **判断死**: punch-list 清空后不停、开始发明新 KG 维度/新分析当"活"。→ 清单空 = stop, 不自造活(违 J1+死线2)。
- **谄媚死**: 把"代码更干净/功能更多/导出更全"narrate 成"更接近交付"; 或弱化诚实 caveat 讨好"看起来完整"。→ 沿用上轮交付复评 critic 教训; 阶段回报必区分"功能完成度↑"与"交付门未动"。

---

## Punch-list (去镀金 in-scope, 按 rank; #1/#2 已 controller 核实为真 bug)

> 状态: ☐ 待做 / ◐ 进行 / ☑ done(commit)。每项 done 须满足 done_when + 三门绿。

### High-value 优先 (rank 1-5, 12)
- ☐ **#1 [S] 词典释义溯源徽章修正(85%裸代码 bug, 已核实)** — dict.js SRC 表 key={textbook/unit_vocab/zhongkao...} 与实际 gloss_source(renjiao36%/waiyan26%/中考词汇表23%)失配 → 85% 行徽章渲裸代码。**done**: srcBadge 接 category-config.js canonical 单点(renjiao/waiyan→教材绿, 中考词汇表→中考蓝, variant→变体继承), 前端实测三主力源行显示正确中文徽章; 三门绿。
- ☐ **#2 [S] exam_point 浮窗真题断链修复(581边查不到, 已核实)** — graph_popup.py:100 `relation IN ('tests_word','tests_grammar')` 排除 tests_exam_point; 推断/记叙文/人与社会(31/78/102题)恒返 questions:[]。**done**: _fetch_questions 增 node_type='exam_point' 反查支(dst_id=cid AND relation='tests_exam_point' JOIN question_bank UNION); curl popup?id=exam_point:cognitive_skill:推断 返回真题非空=DB真值(31); word浮窗回归不变; 三门绿。
- ☐ **#3 [S] exam_point 概念加 popup 入口(配#2)** — 考点分布/cooccur/驾驶舱考点标签用 GZ.conceptLink 替死文本。**done**: 考点标签可点弹浮窗显示#2修好的真题; 三门绿。
- ☐ **#4 [S] 浮窗显示 attrs_json 教学元数据(已fetch未渲染)** — graph_popup.js renderHTML 顶部 JSON.parse(center.attrs_json) 渲 meta chips(exam_status/gaokao_hit_count_ln/cefr/teaching_hint)。**done**: word浮窗顶显真值chips=DB; attrs缺失不报错; 三门绿。
- ☐ **#5 [M] shared 导出/打印能力(跨7区最高频缺口, 一次建解全部)** — 通用helper: ECharts chart.getDataURL()→PNG + 表格rows→client Blob CSV + @media print(.bk-grid/.bk-card/dict表/k12卡 break-inside:avoid+隐侧栏); 核心分析tab加导出/打印按钮。**done**: 驾驶舱图导PNG + 词典筛选导CSV + Cmd+P 驾驶舱/词典/K12 出干净A4; 三门绿。
- ☐ **#12 [S] blueprint_practice 接前端矿口(诚实组卷引擎空转)** — 组卷视图加'蓝图练习卷(真题/非押题)'按钮调 /api/exercise/blueprint_practice, 渲 paper+composition_basis(诚实标'结构对齐非预测')。**done**: 按钮调通渲蓝图卷标 basis=blueprint_fixed; 三门绿。

### 收敛/接矿口 (rank 6-10)
- ☐ **#6 [M] compose 组卷接进主SPA** — teacher.js compose 表单移植进 app_router qbank tab 内联面板, 复用 /api/paper/compose; type_mix 改库内真实题型(从/api/qb/stats by_type动态); 阅读题 stem 放宽~3000不截。**done**: 主SPA可组完整卷, 默认0 shortfall, 阅读含全小题; 三门绿。
- ☐ **#7 [M] 按unit备课接进主SPA** — teacher.js renderLesson(unit下拉+/api/lesson_plan 词/语法/越纲/真题溯源)移植成主SPA'单元备课'tab, 后端零改; 加打印。**done**: 主SPA备课tab选unit渲染=/api/lesson_plan真值可打印; 三门绿。
- ☐ **#8 [M] course session materials 接矿口(40节课空壳)** — _openHandout 调 /api/course/session?id, materials按kind(word/grammar/exam_question)分组渲染(带textbook_position/reason/year_level), 测验保留。**done**: 点课卡显示materials分组=DB真值; 三门绿。
- ☐ **#9 [M] K12 10维语法蓝图结构化(核心卖点埋markdown)** — /api/zhongkao/distribution 已返回但drop的语篇填空考点20行 pivot成10维×2024/2025表(末列✅高考语法填空考点); B卡71对降级标注'71≠10'; service补按维度聚合字段(单算点)。**done**: k12渲10维pivot表=alignment.md§发现2; service聚合是单算点; 三门绿。
- ☐ **#10 [M] word_sense 跨阶段多义接全链路(DB有/API无/前端无)** — 新/api/word_detail?word=X JOIN nodes(word_sense)+edges(has_sense/expands_sense) services单算点; dict词行可展开显逐阶段义项, provenance=dual_model **必标'方向性参考'非真值**(守J4)。**done**: /api/word_detail?word=power 返初高义项=DB; dict词行展开显示且LLM源标方向性; 三门绿。

### 诚实可视化 + 减债 (rank 11, 14, 16, 17)
- ☐ **#11 [S] D区设问技能不可信新era视觉降级(critic flag, 守J4)** — renderCognitiveSkill 读 reliability[ERA_NEW].distribution_reliable, false时新era series opacity:0.45+dashed(复用C区), label后缀?, bk-cog顶加显著banner'新高考n=15仅方向性非精确', 推断红不可信降灰。**done**: 新era不可信时灰+虚线+banner, 推断红降级, C/D诚实态一致; 三门绿。
- ☐ **#14 [S] F题材x思维 era锁徽章 + K12中考卡年份诚实** — beike F卡右上加灰底era锁徽章'仅旧课标II截面'; k12.js删冗余complete项; C卡中考题型按年(2024/2025)拆并列条守'N=2非趋势'。**done**: F卡era徽章显著; k12 banner无冗余; C卡分年并列+N=2标注; 三门绿。
- ☐ **#16 [S] 题库详情 alert→内联modal + 热力导词表** — teacher.js loadDetail alert()换内联modal(可滚动复制 stem+answer+analysis+tags); E区热力点格并行给导词表CSV; 删前端死options_json分支。**done**: 详情modal可滚动复制; 热力格导CSV; options死分支删; 三门绿。
- ☐ **#17 [S] 侧栏静态'0 FAIL'改live + graph tab过时注释收口** — app.html:20 硬编码'0 FAIL'改 fetch /api/audit/findings 算(复用populateNavCounts) 或去静态数字; graph tab更正'iframe嵌'过时注释。**done**: 侧栏FAIL随真实audit变(可注入FAIL验); graph tab注释准确; 三门绿。

### 大件 (rank 13, 须确认讲义定位前可做教材浏览部分)
- ☐ **#13 [L] 教材77单元浏览tab接进主SPA(STEP1地基不可见)** — 新'教材'tab: 列14册77单元(/api/units页范围)+点单元展lesson_plan+cross_version外研↔人教对照+/api/textbooks PDF内嵌; city_curriculum顶选地市。**done**: 教材tab列77单元=/api/units, 单元详情含cross_version, PDF预览可开; 三门绿。

---

## 拒做 (out-gold-plating / out-deferred, 防 loop 跑偏)
新KG维度/关系/节点类型 · 新图算法(社区发现/中心度/PageRank) · 新命题方式轴/趋势模型 · COCA义项裁剪(涉真值裁剪) · options_json结构化拆/EOL重做提取层 · course_sessions排课实例(②③轨) · scan答题卡OCR→批改链路(deferred) · curriculum_level全称美化 · 7缩写词补释义(0.17%) · course quiz LIMIT参数化(动反增险)。

## 需用户拍板 (needs_user_decision, loop 跳过并回报, 不擅自定)
1. **UI收敛终态**: /teacher /legacy = 302重定向 / '旧版已迁移'横幅 / 共存? (loop 先接矿口消依赖, 下线方式待拍板)
2. **讲义生成层定位**: 永久下线(清#15死代码壳)vs 未来重建(保壳)? (#15 死代码清理绑此决策, loop 不擅删可能复活的壳)
3. **考点关联 cooccur IA**: 嵌进研判驾驶舱补G区 vs 保持'研判看趋势/讲课调关联'分离?
4. **blueprint 写作类题型**: 库里0道写作题, 蓝图过滤 vs 输出'需主观命题'占位?
5. **工作台'今日态'**: 改最近活动流(localStorage) vs 诚实改名'平台概览'?
6. **词典检索增强**: 中文释义反查 + -able中段子串? (可用但偏窄, 看教研员习惯)

---

## Loop 协议 (每轮)
1. 取 punch-list 下一未完成项(按 rank, 跳过 needs_user_decision 未拍板项 + #15)。
2. 改 backend/services|db|api 或 init_db|extract_* 前看 precode hook 复杂度提示; 触发阈值先跑 codegraph 审计。
3. 实施: 接矿口=services 单算点薄壳 + 前端纯渲染(J2), 不重写计算点。
4. 行为等价/真值核验: 新端点 curl :8765 实测 200+真数据=DB真值; 前端改动 preview_eval/preview_screenshot 或核验渲染对得上 DB(消费者锚定: 走一遍"教研员这步")。
5. 三门: data_accuracy_check(exit0) + moth assert(PASS) + stop_gate(exit0); 新API/数据落地必同步加 docs/data_accuracy_audit.md + data_accuracy_check.py 校验项; 任一红查根因不跳过。
6. git commit(新commit不amend, Co-Authored-By)。
7. 更新本文件 §进度勾选 + docs/RESUME.md(live真相源不引旧数字)。
**停止条件**: punch-list 清空 / 撞 needs_user_decision / 三门连续红查不出根因 / 行为核验失败无法修复 → 回报用户。每清一个 rank 段(如 high 全清)回报一次阶段进度。

## 进度
- 立法 + scoping(7区审计Workflow) + #1/#2 controller 核实 = done (2026-06-23)。
- **High-value 批 (loop 执行中)**:
  - ☑ #1 词典徽章 85%裸代码 → GZ_CAT.glossSource 单点 (022c204; preview 301行徽章正确, 裸码泄漏=0)。
  - ☑ #2 exam_point浮窗真题断链 → _fetch_questions 加 tests_exam_point + 子题分支 (d19408a; 记叙文8真题/推断8子题诚实/word回归; moth锁)。
  - ☑ #3 考点图可点弹浮窗 → GZ.openPopup导出 + beike/cooccur图click (afee1d3; 端到端"真题命中8"; #2+#3=考点关联矿口打通)。
  - ☑ #4 浮窗显教学元数据 → renderHTML渲attrs chips (preview: 核心/辽宁命中53/义教/teaching_hint; 不再丢弃)。
  - ☐ #5 shared导出/打印 (M, 下一项)。 ☐ #12 blueprint接矿口。
- 累计 4/17 done, 三门全程绿 + sherpa GO。Loop 续 #5。
