---
name: gaozhong-ops
description: >-
  gaozhong (沈阳/辽宁高中英语教学系统, DuckDB 单库) 项目操作手册 — 接手或做实质工作(改数据/真题/审计/服务/前端/重构)前 invoke。
  固化项目专属: D0 100% 红线 · 八条铁律 · 坑库(数据诚实性反例 + 发现方法 + 修复模式) · 工具调度(data_accuracy_check/stop_gate/run_all/init_db/codegraph) · 真相源文档地图。
  专治"绿门假绿/陈旧快照/省份卷型污染/学情假推/停用词噪声/不完整地基上的生成内容"。架构细节看 docs/architecture.md, 本 skill 给操作+踩坑知识。
---

# gaozhong 操作手册

> 何时用: 在 `~/Documents/M/gaozhong/` 做实质工作(改 exam_questions/真题/学情/审计/服务/前端/重构)前 invoke。
> 真相源不在本 skill — 在项目 doc + DuckDB; 本 skill 是"怎么干 + 别踩什么坑 + 怎么发现坑 + 用什么工具"的操作层。
> DuckDB 完全独立, 禁 ATTACH gaokao DB。

## 0. 接手前 First Actions
1. 读 `docs/README.md`(权威索引: current law / verdict / spec / legacy)→ `agent.md`(现行规则, 非 CLAUDE.md)→ `goal.md`(控制板, 但有漂移, 以最新 ledger 为准)→ `docs/architecture.md`(八铁律)。
2. `git status --short`; 不擅自 revert 上一 session 改动。
3. **live 门禁以脚本为准, 不引文档旧数字**: `python3 scripts/data_accuracy_check.py`(D0, exit 0)+ `bash scripts/stop_gate.sh`(exit 0)。
4. 改数据前 `cp data/db/gaozhong.duckdb /tmp/gz.bak`(DB 是 gitignored, 代码才是真相, 但备份防误删)。
5. **定位/blast-radius 先用工具不人肉 grep**: `codegraph query <symbol>` + `codegraph explore <task>` 查 fan-in/调用面(本项目装了 `/opt/homebrew/bin/codegraph` + `.codegraph/`); 单符号深挖用 `codegraph node <name>`; 改完 `codegraph sync .`。跨文件 audit/research → spawn subagent, 主对话只带结论。

> ⚠️ 反面教训(2026-06-15): 删生成内容时我**人肉 grep 盘 blast-radius** 而非 `codegraph query <loader>`——既慢又易漏。codegraph 装着却没用 = 工具使用失误。**任何"删/重构某模块影响谁"先 codegraph, grep 是兜底。**

## 1. 红线 / 死亡条款 (不可违)
- **D0 = 任意数据+任意关联性 100% 准**。算不出标 `unknown`/`未知`, 不假填(宁缺毋滥, 返空>假推)。
- **八铁律**(docs/architecture.md §0): 单一计算点 / Canonical First / Edges 一等公民 / 模块化 / 可复用 / 可扩展 / fan-in>5 BLOCK / 反模式禁令(god-module>400L · CC>15 · try:pass)。
- **数据基石优先(§1.1)**: 教材完整提取(STEP1)前, 任何生成内容(讲义范文/合成题/趣味化)都是降级话题, 不该建在不完整地基上。
- **不偏离学校(§1.2)**: 趣味化内容必须能反证"词量≤已学单元+课标3500" + "语法≤已学单元"。
- **判断规则数据化(§3.5)**: 停用词/卷型/阈值/source 状态写 `backend/config/*.yaml`, 不在 route/service hardcode。
- **真相源 = 教材+课标+真题 PDF(类比量化的 K 线), 不是中间派生表**。
- destructive(批量删/重构整层)先确认; commit 只在用户要求时, 默认分支先问/先 review。

## 2. 坑库 (本项目踩过的数据诚实性反例 → 发现方法 → 修复模式)

### 坑1: 绿门假绿 / 自欺 (L-R)
- **反例**: `data_accuracy_check.py` exit 0 报"D0 100%", 但它**零覆盖** exam_questions.province/paper_type 正确性 → 2021/2022 假标"辽宁新课标II卷"(含全国甲卷)长期静默通过。
- **发现**: grep 绿门脚本看它**到底断言了什么维度**; 没断言的维度永远绿。独立审计(exam_paper_contract_audit)与绿门**对账**。
- **修复**: 绿门**加断言锁死该维度**(check_21: 无未核验源冒充新课标II / smoking gun 行已降级)。对抗验证: 故意污染 1 行→必须 FAIL, 自愈→OK。**每条数据教训三件套: 改单一计算点 + 改已落库数据 + 加 gate 断言防回归**。

### 坑2: 陈旧 audit 快照掩盖工程债 (L-S)
- **反例**: committed audit_findings "44 全 OK" 是陈旧快照; fresh `run_all` 揭露 code_complexity 42 CC>10 + code_size 4 god-module(治理代码自身违反 Rule 8)。
- **发现**: **跑 `run_all` 刷新, 别信 committed 快照**。`cp DB /tmp/bak` → run_all → 对比 → `ATTACH bak; DELETE; INSERT SELECT` 还原。
- **修复**: 工程债(CC/size)非数据准确性, OBS 重归类 + 甩独立减债任务; 数据审计必须 fresh。

### 坑3: 省份/卷型 provenance 污染 (L-N/L-P)
- **反例**: GAOKAO-Bench **不标省**, 旧逻辑对 2021+ 默认推断辽宁 → 混合卷(含甲卷)假标辽宁。2010-2014 辽宁自主命题期数据实为他省。
- **发现**: **provenance 溯源**(source_repo 区分可信度) + **smoking gun 抽查**(2021 'Landscape Photographer' = 全国甲卷, grep raw_question 验)。
- **修复**: 单一计算点 `exam_province.refine_province` 改 provenance-aware(local_pdf/Updates/eol_xgkii 可信→辽宁; GAOKAO-base 自主命题期/混合期→诚实降级)。**辽宁卷史: 2009-14 自主命题 / 2015-20 新课标全国II / 2021+ 新高考全国II**。

### 坑4: 学情假推 (无答题的伪造置信度)
- **反例**: student_weakness 写死 score=0.85/n=12, 但 student_answers 空 → 热力图在零作答上渲染伪造置信度。
- **发现**: 查派生表是否有**真实上游支撑**(weakness 行能否在 student_answers 找到 join)。
- **修复**: 删写死, seed demo student_answers → `weakness.recompute_all` **派生**(单一计算点)。零 orphan 断言: 每 weakness 行必有答题支撑。

### 坑5: token∩词表=考点 的停用词污染 (L-U)
- **反例**: `_autotag`/`build_tests_word` 把 the/it/to/they 也建 word tag/边(41% 噪声)→ 弱点"弱在 they", tests_word 边稀释考点。
- **发现**: top word tag 按频排序看是否是功能词; cefr_vocab 不区分功能/实词。
- **修复**: 停用词表 `config/stopwords.yaml`(数据化) + 共享 `services/stopwords.py` content_tokens(token∩cefr−停用词)。

### 坑6: 不完整地基上的生成内容 (L-T)
- **反例**: Phase 7 在教材 46% 覆盖时就生成 40 讲义范文 + 合成题; 绿门还把"讲义==40"当 D0 项校验。
- **发现**: 问"这内容的地基(教材)完整吗?" 生成内容 vs 真值, 哪个是真相源。
- **修复**: 协同回滚生成层(删源文件 + 剥 pipeline loader + 改门禁对真题诚实 + 前端下线), 保留真题/canonical/结构骨架。**真值走 review gate 入库**(EOL: structured_draft + review_decisions import_ready → exam_questions)。

### 坑7: 标签否定词 + 子串匹配 bug
- **反例**: 给 2010-2014 标"非辽宁", 下游 `province LIKE '%辽宁%'` 子串把"非辽宁"也命中 → qb 误收外省题。
- **发现**: 改标签后查所有 `LIKE '%X%'` 消费者; 标签含否定词("非X")时子串会反向命中。
- **修复**: 精确前缀 `LIKE '辽宁%'`(以辽宁开头)。

### 坑8: 生成内容非模块化 → blast-radius 靠人肉盘点 (元教训)
- **反例**: Phase 7 生成内容散在 `config/enriched_content/*.yaml`(40)+ `config/*_exercises.yaml`(3)+ `services/course/{handout,reading,writing,listening}.py` loader + `loader.load_synthesized_samples` + `init_db` Layer 4c/4d/4f + question_bank.origin 多值, **没有单一边界/统一标记**。删它时 blast-radius 只能人肉 grep+盘点。
- **发现 (smell)**: **当"删/改某类东西影响谁"需要人肉盘点而非 `codegraph query` 一把定位, 这本身就是"非模块化"的 smell**。模块化的东西 codegraph 一查 fan-in 即出全量调用面。
- **修复/原则**: 生成内容(或任何一类可整体增删的东西)应**模块化管理**: 单一目录 + 统一 `origin`/`generation_meta` 标记 + 单一 loader 入口 + 配置集中。这样增删 = 改一个模块, codegraph 秒定位影响面, 不留散落残留。**判断标准: 能不能一句 `codegraph explore "删除生成内容"` 拿到完整 blast-radius; 不能就是没模块化。**

### 坑9: crawl4ai 浏览器 channel 参数名 (M6, 2026-06-15)
- **反例**: 用 `channel="chrome"` 传 crawl4ai 启动配置, 0.8.x **只读 `chrome_channel`**, 静默忽略 `channel` → 不走本机 Chrome。
- **发现**: 在线页(JS 渲染)抓取走 `acquire/web.py` 时启动行为不对; 查 crawl4ai 0.8.x 源码确认参数名是 `chrome_channel`。
- **修复**: 必须 `chrome_channel="chrome"`(本机 Chrome 149 已装)。**不要下 chromium**(已删 531M, 浪费磁盘)。**强反爬官方站**(jyt.ln.gov.cn 等)crawl4ai 也过不去 → 升级走 Chrome MCP(`mcp__Claude_in_Chrome__*`, jyt.ln.gov.cn 实证可达)。

### 坑10: git ls-files 中文文件名八进制引号 (M6, 2026-06-15)
- **反例**: 解析 `git ls-files` 默认输出, git 对含中文的文件名会**八进制转义并加引号**(如 `"\346\225\231\346\235\220.pdf"`)→ 伪路径 → `init_db` file_manifest 阶段 `FileNotFoundError` 崩。
- **发现**: file_manifest 对某些已 track 的中文名 PDF 报文件不存在, 但 `ls` 明明在。
- **修复**: 解析 `git ls-files` 必须用 `-z`(NUL 分隔, 不转义不加引号)。`backend/services/data_sources/.../load.py:_tracked_files_under` 已修。**凡 shell 出来要当真实路径用的, 都用 `-z`/`-0` NUL 分隔。**

### 坑11: DuckDB 单写者 — 入库逻辑别自开第二写连接 (M6, 2026-06-15)
- **反例**: `init_db` 用 `subprocess` 调一个独立写库脚本做 PDF 导入, 子进程**自开第二写连接** → 与父进程写连接锁冲突(DuckDB single-writer)。
- **发现**: 重建在 Layer 4g PDF 导入阶段卡 / 报 lock; 凡"入库逻辑被起成子进程/另开连接"都是嫌疑。
- **修复**: 入库逻辑**复用调用方已持有的写连接**, 不自开第二写连接。Layer 4g 已改为 in-process `import_pdfs(con)`(传入父连接), 不再 subprocess。**模式: 写库函数签名收 `con`, 调用方传, 全程一个写连接。**

### 坑12: "数据诚实" ≠ "分析有效性" (最重要 — 核心方法论, 从流程杜绝) (2026-06-15)
- **反例/盲点**: 本项目全套工程纪律(D0 / 八铁律 / moth / 三绿门)守的是 **"不造假数据"**, 但**不**保证 **"趋势/考点/关联分析是对的、有人用的"** —— 两者被悄悄等同, 是核心方法论盲区。证据: ① 趋势在 **3 处各自算**(违反 Rule1 单一计算点); ② "考点热力" 其实是**词频**(`question_tags` 85% 是 word token, 不是考点); ③ 趋势把 **472 题(含 284 非辽宁)混做回归**、**2023 仅 6 题也画 slope**。数据每条都"真", 但分析整体无效。
- **从流程杜绝(写成规则 — 分析诚实门)**: 任何 **"趋势/考点/分布/关联"** 产物上线前必过此门:
  1. **province-scoped**: 只对辽宁卷(§7), 不混外省。
  2. **卷制分段**: 2015-2020(新课标全国II) / 2021+(新高考全国II)分开, PIT(§3.1), 不跨卷制回归。
  3. **样本量护栏 — 但区分"分布"vs"趋势"两种门槛(2026-06-15 用户纠偏, 别过度保守)**:
     - **考点分布(占比/snapshot)**: 同卷制 era 总题数 ≥ ~30 即可报。辽宁新高考II 140题/5套卷 → **充足**(项目主用途, 别误标"样本不足"!)。
     - **逐年趋势(slope over years)**: 需达标年 ≥5 且每年 ≥10。辽宁仅5年/2023=6题 → **不足**, 标"趋势样本不足(分布可用)"不画斜率线。
     - 反例: 把"辽宁考点分布"误标"样本不足"=把 distribution 当 trend, 用户会反问"研究辽宁怎么会样本不足"。scope.py 已分 `distribution_reliable`/`trend_reliable`。
  4. **分层不取平均(2026-06-15 用户二次纠偏, 主动做别等催)**: 即便是"分布", 也**必按卷制 era 分段看**,
     **绝不混 2015-2025 全历史平均**——平均会抹掉时间轴上的命题迁移。反例: 考点分布若取全历史均值,
     会把"记叙文↔说明文首位翻转""人与自然占比翻倍(8.5→19.5%)"这些**真迁移完全稀释掉**。
     `exam_point_distribution` 已默认 `{era: {dim: [{label,n,pct}]}}` 分层返回。**任何分布/对比默认分层, 不默认平均。**
  5. **考点标注带 provenance**: human / dual_model / llm; C 级 LLM 拆的**必双校验**, 词频不许冒充"考点"。
  6. **能答"谁消费、消费什么形态"**: 答不出 = 为分析而分析, 感知即死。
- **D0 升级**: 从 **"数据诚实"** 扩展到 **"分析诚实"**。载体定义见 `docs/tutorial_consumer_spec.md`(面向教师, 学生档案/错题库为脊柱)。
- **发现**: 任何"X% 上升/某考点热"先问真相源(是 province-scoped 的辽宁卷? 跨卷制了吗? n 够吗? token 还是考点? 谁用?); 样本量透明可跑 `python3 -m scripts.tools.map doctor`(年度 n<10 自动标"样本不足")。

### 坑13: m0_gate_plan.load_gates() order off-by-one (2026-06-15)
- **反例**: `m0_gates.yaml` 的 order **0-indexed**(order 0 = 控制面门), 但 `validate_gates` 硬要 **1-indexed** → `load_gates()` 直接抛错。死代码(无调用方, 故无 live 影响), 但**跑 planner CLI 会崩**。
- **发现**: 单跑 m0_gate_plan CLI 时 `load_gates()` 在序号校验处抛错; gate yaml 从 0 起而校验从 1 起。
- **修复**: `validate_gates` 改为**接受从 0 或 1 起的连续序列**(容忍两种起点)。

### 坑14: "预测试卷/押中高考" 营销话术 — 分析诚实要延伸到造题/组卷 (2026-06-15)
- **反例**: `backend/services/exercise/predicted.py` 名 "趋势驱动预测试卷"(`predicted_trend_driven`), 按件1 已判**不可信的 slope**(辽宁逐年趋势样本不足) 加权选题。"AI 押中高考/精准预测考点" = **营销话术**, 违反 D0 不臆测 + §3.2 Banned 押题 + gaokao 宪法 banned 押题。
- **发现**: 题面其实**来自 question_bank 真题(非合成押题)**, papers 表 0 行未持久化, 前端不调, 仅 API 端点。问题在**框架(命名"预测") + 用不可信 slope 加权**, 不在内容造假。
- **修复(从流程杜绝)**: (1) **reliability 门控**: 趋势可信才轻微 slope 加权; 不可信(辽宁样本不足)→**退回考纲蓝图固定占比**, 不按噪声 slope 加权, 不注入"上升词预测"。(2) **去营销话术**: 改名 `generate_blueprint_practice_paper` / `/api/exercise/blueprint_practice` / `paper_type=blueprint_structured_practice`。(3) moth 断言 `practice-not-prediction` 锁住。
- **规则**: 任何"生成/造题/组卷/预测"产物必须 — (a) 题面来自真题不合成押题; (b) 用趋势时**读 reliable**, 不可信时退回蓝图固定结构; (c) 命名禁"预测/押中"营销话术, 诚实定位="**结构对齐 + 课标合规造题**"(见 docs/exam_scenario_patterns §8: 结构可借鉴 / 具体内容不可预测)。
- **⚠ 红线边界修订 (2026-06-16 用户立法, 防过度外延)**: 本坑的红线是 **"押具体题目/篇章/答案内容 + 用不可信 slope + 营销话术命名"**, **不是** "禁止命题趋势分析/方向性指引"。**数据驱动的命题趋势分析 + 方向性重点指引(哪些考点/题型/题材/命题方式升温→教学优先级)是项目核心竞争力(好老师本就画重点, 大数据做得更准), 鼓励做。** 红线内核=4 护栏(样本量诚实/provenance/结构≠内容/ML数据足才上), 全保留; 删的是"把趋势分析本身当押题"的过度解读。详 goal.md 同日"红线修订"段。

### 坑15: stop_gate 把 DB 锁冲突误判成 D0 违反 (假阳性, 已流程级根治, 2026-06-15)
- **反例**: 后台 `init_db.py` 重建持 DuckDB 写锁时, stop hook 的 `data_accuracy_check.py` 裸 `duckdb.connect` 撞锁抛 IOException → stop_gate 误报 "❌ D0 违反" 阻断。频繁假阳性, 用户: "频繁出现的问题应从流程上解决"。
- **第一性原理**: 锁冲突 = "DB 正被重建"(瞬时运行态), **不是"数据错了"**。门的职责是抓错数据, 不是读不到时谎报。
- **修复(从流程杜绝, 非每次绕过)**: `data_accuracy_check.py` 锁冲突时**重试**(瞬时锁自愈 4×2s); 仍锁返回 **exit 3**(延后)并打"非数据错误"; `stop_gate.sh` 把 exit 3 视为**非阻断**(仅 exit≠0且≠3 才 BLOCK)。check 1(audit_findings) 早有 `except` 容错。
- **通用规则**: 任何"读 DB 判绿"的 gate/脚本, 必须把**锁冲突与数据错误分开** — 锁=延后(重试/非阻断), 不冒充失败。后台 init_db + 前台 stop 是常态, 别让它互相误伤。

### 坑16: dual-model 0分歧 ≠ 正确; 分类/标注必须对显式真相源交叉验证 (2026-06-16)
- **反例**: 设问类型分布用双模型从**设问句 inference**(无答案/解析), 两模型 **0 分歧**, 误以为高置信。但与 **gaokao `english_xgkii_2021_2025.jsonl` 显式教研解析**(解析开头直接标"推理判断题/细节理解题")交叉验证, **系统性低估"推断"**: 我估推断15%, 真相源显示**约50%**。
- **根因**: 只看设问句猜会把"推断题"误判成"细节题"(设问表面像细节实则考推断); **两个模型一致地犯同一系统性偏差** → 0分歧是"一起错"不是"对"。
- **通用规则**: (1) 分类/考点/题型标注**优先用显式真相源**(官方答案/教研解析里直接写的题型标签), 不以表面文本 inference; (2) **dual-model 一致只防随机噪声, 不防系统性偏差** — 必须再对真相源(显式标签/官方解析)交叉验证才算可信; (3) 真相源常在本地: **gaokao 兄弟项目 `data/structured/english_xgkii_2021_2025.jsonl` 有 2021-2025 辽宁卷 sub-question(设问句+答案+36行真解析)**, 别去联网臆测。已收口到 `data/structured/exam_subquestions/`。

### 坑17: 新数据落地必入 D0 强校验, 不只 moth (2026-06-16, 流程纪律)
- **反例**: 连续多 tick 建考点数据(exam_point边/theme_aligns/weakness考点化), 每次只加 **moth 断言**, **忘了 `data_accuracy_check.py` 的 D0 校验项**——直到主动 `grep exam_point scripts/data_accuracy_check.py` 查 D0 覆盖(0 命中)才发现。违反 CLAUDE.md D0 流程("新数据落地必加 data_accuracy_check 校验项")。
- **根因**: moth 和 D0 是**两道独立门**(moth=弹仓漂移检测; D0=100%准强校验/stop_gate阻断), 加了 moth 容易误以为"覆盖了"。
- **通用规则**: 任何新数据/新关系/新派生落地, **moth 断言 AND data_accuracy_check 校验项 都要加**(D0 是用户#1硬约束)。check 函数把 data_accuracy_check 推过 400 行就抽到 `scripts/lib/d0_*.py`(避 god-module Rule 8, check 由调用方传入)。改完 `grep <新数据关键词> scripts/data_accuracy_check.py` 自查覆盖。

### 坑18: 放宽截断上限会暴露下游 bleed; PDF 题型分段边界要双向收口 (2026-06-16)
- **反例**: 修"2025 阅读 raw_question 硬截 2000 丢小题"时把 `_make_section` 上限 2000→8000, 结果**末段「续写」(第二节→文末, 无下边界)立刻吃进卷尾附录**(锦宏/学科网 mock-PDF 把听力重印/答题卡注意事项/参考答案排在卷尾)——放宽上限 = 把原本被截掉的污染暴露出来。同时阅读 D 篇(无下一篇)`+3000` 硬截也会 bleed 进七选五。
- **发现**: 修完**逐行复核每个 section 的 raw_question 头尾 + grep 附录词**(英语听力/参考答案/绝密★启用前/准考证); `LENGTH=上限值` 的行=撞上限嫌疑(可能还在吃后文)。
- **修复/原则**: **任何"段"都要双向收口**——下边界优先取下一结构标记(下一篇/「第二节」/卷尾附录标记 `_strip_post_exam_tail`), 找不到才到段末; 上限(8000)是兜底不是边界。**改一个截断阈值, 必须重审所有共享该阈值的消费者**(本例阅读和续写共用 `_make_section`), 别只验报障的那一个。每条加 D0 断言锁(无硬截断 len=阈值 / 无附录污染)。

### 坑19: 跨年/跨源真值数据异构, 聚合要兼容多形态 (2026-06-16)
- **反例**: 用 gaokao `xgkii_*_subquestions.jsonl` 填 PDF 答案时, **2025 逐题存**(question_number + 标量 answer), **2024 整段存单行**(question_number=None + answer 为 **list**)——同一聚合逻辑对 2024 产出垃圾串 `0.['D','B',...]`(list repr 进了答案字段), 违反 D0。
- **发现**: 聚合后**逐 key 打印答案串肉眼扫**, 发现非预期格式(list repr / 题号=0)。不同年份/源的"同一字段"schema 可能不同。
- **修复**: 聚合前先**探测形态**(`isinstance(ans, list)`), 两形态统一到干净输出(逐题→`1.C 2.B`; 整段 list→保序拼 `D B A`, 不臆造起始题号)。**真值源诚实**: 源怎么存就怎么兼容, 不强行套一个 schema。

### 坑20: 计数型门漏掉单函数严重度尖刺 (CC>15 滑过 CC>10 总数门, 2026-06-16, 流程级)
- **反例**: commit a9e671a 引入 `_jsonl_answer_map` **CC=18**(超 Rule8 硬阈15), 但 `stop_gate` 复杂度门只判 **CC>10 函数总数 ≤ baseline 37**——当时总数 36→37 刚好≤37 滑过, **提交前我跑了 stop_gate 还绿**。下一 tick `complexity_check` 单文件审计才抓到。
- **根因**: 计数型 baseline 门(总数≤N)对"单函数跨硬阈"不敏感——只要别的地方没新增 CC>10, 一个 CC=30 的怪物也能进。Rule8 的 **CC>15 硬阈一直没有 per-severity 门**。
- **修复(从流程杜绝)**: `stop_gate` 加 **2b. CC>15 单函数计数子门**(复用同一次扫描的输出 awk 出 CC>15 数, baseline=现存12, 跨硬阈新增即阻断)。对抗验证: 临时造 CC=18 探针→必阻断(13>12), 删除→回绿。
- **通用规则**: **门要按"会回归的最细粒度"判, 不止聚合计数**。总数门管整体趋势(减债), 但每条硬阈(CC>15/god-module>400/fan-in>5)要有自己的 per-unit 门; 提交前除 stop_gate 还要对**改动的具体函数**单独跑 `complexity_check.py <file>` 看 per-function CC(总数门不替代单点检查)。

### 坑21: 声明为 BLOCK 的 gate_contract 没接进执行点 = 空门; 触发器要覆盖会致漂移的文件类型 (2026-06-16, 流程级)
- **反例**: `project_architecture.yaml` 的 `gate_contracts.project_architecture_audit` 声明 `severity: BLOCK`(查硬编码PDF路径/悬挂doc引用/缺失模块路径), 但 **stop_gate 从未调它** → 3 个架构违规(import_recent_exams 未数据化 + M0_CLOSURE 悬挂引用×2)长期静默躺着, 本 session 靠手动 `map doctor` 才发现。**且** stop_gate 变更过滤器只认 `.py/.sql/.html/.js/.css`, 改 `.yaml`(配置型架构漂移)根本不触发任何门。
- **发现**: `grep -n "<gate脚本名>\|architecture" scripts/stop_gate.sh` 查声明的 gate 有没有真接线; 对抗注入要**用会真正触发门的文件类型**(我第一次注入 .yaml 但过滤器不认 .yaml → stop_gate 直接 exit0 跳过, 假阴性, 差点误判门没用)。
- **修复(从流程杜绝)**: ① 把 gate_contract 声明的 BLOCK 审计真接进 stop_gate(gate 4 跑 `project_architecture_audit.py --strict`, 非0则阻断); ② 触发器加 `yaml/yml`(配置/数据契约漂移也触发)。对抗: 注入悬挂引用→exit2 阻断, 还原→exit0。
- **通用规则**: **gate_contract/契约声明 ≠ 强制执行**。任何"声明为 BLOCK"的审计, 必须 grep 确认它真在 stop_gate/CI 被调用且非0阻断; 否则是装饰性契约。**且 gate 的触发条件(change-detection 过滤器)必须覆盖所有能引发该 gate 所守漂移的文件类型**——守 config 契约的门, 过滤器就得认 config 文件。对抗验证门时, 注入的改动本身要能触发门(否则假阴性)。

### 坑23: 教师子系统"看似可删"实则被多处钉住 — 删前必工具审影响面, 对抗验证揪隐藏依赖 (2026-07-02)
- **反例**: 用户拍板"教师工具中与教学无关的删除", 初判 workbench/qbank/data/students/scan/lesson/k12 都可整删。**对抗验证一轮就推翻大半**: qbank 前端块被 moth `compose-in-spa`/`blueprint-practice-wired` 断言直接 grep 钉住; k12.js 被 `k12-blueprint-senior-rendered` 断言钉住 + service 函数被北极星 Phase E(初中板块)引用; lesson 路由文件本身**就是**北极星"教师工具下线但后端保留"决策的断言对象(`test -f backend/api/routes/lesson_plan.py`); students 表/seed 被 D0 检查16/17/18 + 4 条 multitenant moth 断言 + `api_payload_check.py` 周检脚本共同钉住。真正可删的只有 workbench(零断言引用) + scan(3处门禁引用需先斩) + 2 张 0 行死表。
- **发现**: **改前必 `moth coupling --repo . --impact <名>` + `grep <模块名> .moth/assertions/claims.yaml` + codegraph fan-in** 三件套查真实影响面, 不能只看"前端 nav 里删了 tab"就当作模块死了 —— 断言/D0/门禁脚本对模块的引用不会因为 UI 隐藏而消失。
- **修复/原则**: 删除范围以**对抗验证结论**为准, 不以"用户原话字面覆盖的清单"为准(mio #8 对抗需求本身); 影响面盘点跑一次 25-agent 并行侦察比人肉一个个查快且不漏。删除后同步改被钉住的断言(如 `exam-point-popup-entry-wired` grep 已删文件的分支要撤)、`frontend_rc1_check.py` 的 LIVE_JS 列表、`docs/data_accuracy_audit.md` 对应行 —— 这些"消费残留物"跟代码本体一样需要清, 否则断言假绿或误报陈旧契约。

### 坑24: 端点 HTTP 契约缺失 = 74% 盲区 — 契约数据化 + 双向覆盖率自检 (2026-07-02)
- **反例**: 全面审计发现 75 个 GET 端点里只有约 1/4 有 moth 断言覆盖(且多数是"grep 前端调用字符串"级别的接线验证, 非响应 schema 契约), 其余端点响应结构漂移(拼写改字段名/类型改 list→dict)不会被任何门抓到。
- **修复(数据化, 不写 75 条散断言)**: `backend/config/endpoint_contracts.yaml` 逐端点声明最小合法 `params` + `type`(dict/list) + `required_keys`(2-4个语义关键键) + `allow_error`(已知会诚实报错的端点, 如数据未就绪); `scripts/lib/endpoint_contract_check.py` in-process 直调 `ALL_ROUTES[path](params)`(不用起 http server, 全量 75 端点 <2s), 断言不抛异常/类型对/键全在/无 error 键; **双向覆盖率自检**: `set(ALL_ROUTES) - set(contracts) == 空`(新端点漏契约→红) **且** `set(contracts) - set(ALL_ROUTES) == 空`(端点删了契约没删→陈旧契约红)。挂 D0 + moth 双门(坑17 纪律)。
- **发现方法**: 任何"XX% 端点/维度无断言覆盖"的审计结论, 优先想"能否数据化成一个 yaml + 一个 checker", 而不是让 agent 写 N 条散 shell 断言(N 条断言 = N 处将来要各自维护的重复逻辑, 违奥卡姆)。

### 坑25 = 坑1 的系统性推广: 单条真值锚够, "锚的覆盖率"本身也要一道门 (2026-07-02)
- **反例**: 审计发现 2026 年份导入了真题但 `truth_anchors.yaml` 没给它建锚条目 —— `ExamTruthChecker.check` **只遍历已定义的锚**, 新年份导入了但锚表没同步更新 = 静默不核验(坑1 的翻版: 断言存在不等于断言覆盖新增数据)。系统性门修完后进一步揭露 **2015-2020 五个年份也一样没锚**(同一根因, 藏得更深)。
- **修复**: 加一条 moth 断言直接断言"覆盖率"而非"单个真值": `{DB 里出现的辽宁年份} ⊆ {truth_anchors.yaml 里有锚条目的年份}`, 缺锚年份即使暂时没法验证内容也要显式建 `lifecycle: no_anchor` 条目(UNKNOWN 不冒充已验证, 好过静默不查)。
- **通用规则**: 任何"每个 X 都要有 Y"型的断言(每年份要有锚/每端点要有契约/每模块要有 owner), **除了对已知 X 逐条断言, 还要加一条"X 全集 ⊆ 已断言的 X 全集"的覆盖率元断言**, 否则新增的 X 会静默漏审(坑1/坑17 本质都是这个模式的实例)。

### 坑26: 花大力气网络检索前, 先系统扫描本地仓库是否已有未接入的数据 (2026-07-03, 本 session 最贵教训)
- **反例**: 用户问"设问思维 cognitive_skill 新高考II era 为何仅 2023 单年 n=15", 我立刻假设"这是外部数据缺口"直奔网络检索(WebSearch/WebFetch), 系统性尝试 ~15 次(专有名词精确查/site过滤/知乎/新闻站/学科网), 命中的全是付费墙/403封锁/宏观点评非逐题——**耗费大量轮次后才想起该先查本地**。一查发现 `data/external/gaokao_bench_2024/2024_English_Reading_Comp.json` 里**本来就有** 4 篇阅读理解 15 道题的完整解析(含显式题型标签), 只是现有 pipeline 只抽了同一文件里的完形填空/七选五, 从未抽取过阅读理解部分——数据一直"躺在仓库里没人用"。
- **发现方法(以后必须的顺序)**: 遇到"某年份/某维度数据不全"先问三件事, **顺序不能反**: ① `find data/external data/structured -iname '*<关键年份/关键词>*'` 扫描本地**所有**候选文件(含兄弟命名规律的目录, 如本例 `gaokao_bench_2023/` 存在就该联想 `gaokao_bench_2024/` `gaokao_bench_2025/` 是否也有); ② 对本地候选文件核对**真值锚 marker 是否命中**(防止误用了"名字像但内容是别的卷"的文件, 如本例 2010-2022 老版 mirror 文件的 2021/2022 条目 marker 全不命中, 证实那批不是辽宁卷该弃); ③ **只有本地确认真找不到, 才去网络检索**, 且检索优先用真值锚里已登记的独有专名(人名/机构名如 "Textalyzer"/"Harrogate")做精确查询, 泛化查询("2022年高考英语阅读理解解析")几乎必然只捞到付费资源站。
- **本地检索盘点技巧**: 本项目历史上有多批次镜像/下载(`gaokao_bench/` 老版全集 · `gaokao_bench_2023/`/`gaokao_bench_2024/` per-year GAOKAO-Bench-Updates · `exam_sources/eol/` · `exam_sources/local_pdfs/` · `gaokao_xgkii_2021_2025_mirror.jsonl`), 同一年份的数据可能分散在 3-4 个文件里且**质量不一**(有的只有答案字母, 有的有完整解析), 一次性写小脚本扫描 `json.load` 后 `set((ex.get('year'), ex.get('category')) for ex in ...)` 摸清全貌, 比一个个 cat 文件快得多。
- **网络检索现实(2026-07 实测, 省后人重复劲)**: 知乎(zhuanlan.zhihu.com) WebFetch **系统性 403**(不分内容, 环境级封锁, 别再试); 学科网/组卷网类"教研解析"资源站的详细内容(逐题+题型标签)**commercial-gated**(封面图/下载链接不渲染实际解析, 或需登录/购买), 免费公开网络基本拿不到这类内容; 新闻/门户站的"试题评析"是宏观点评不含逐题标签。**这三条結论已足够稳定, 未来 session 遇到同类"补某年设问/题型解析"任务应直接跳过网络检索环节, 先做坑26①②两步, 大概率就是本地已有未接入。**

### 坑27: 前端整体设计推进方法论 — judge panel 对抗 + 单渲染点根治多处漂移 + 认识论编码 (2026-07-02)
- **背景**: 用户要求"整体设计前端页面/数据可视化, 巧妙简洁美观", 未给具体方向。
- **方法**: 4 个独立视角提案(学习者旅程/数据叙事/极简整合/可视化工艺) 并行对抗 → 3 个评审(taste纪律/学习者可用性/落地成本) 交叉裁决 → 总设计师综合, 出方案书 + P0/P1/P2 分批 backlog。比"直接开始改 CSS"更能一次性抓住系统性问题(如本例"蓝 hero 三连"根因是 `style.css` 一条遗留的裸 `header` 选择器泄漏命中新页头, 而非每页各自的设计缺陷——若不做系统性方案审计, 容易在每页各修一次表面症状)。
- **落地纪律**: ① **单渲染点根治漂移**: 页头(`GZ.pageHead`)/微缩图表(`GZ.stageMiniBand`) 抽共享函数, 一改全站受益, 防"每页各自实现一份、下次改漏一页"; ② **数据可视化色彩纪律数据化**: 蓝阶 = 数据编码(`--down/-2/-3/-4`, 图表代码禁 ad-hoc hex, 违者拒收), 红族 = UI accent 且在数据图里只能有一种语义(不可多个红色系列混淆), 灰+斜纹 = 未分类/不估算; ③ **认识论编码**: 实心=真值(explicit_label/结构真值), 空心/虚线/降饱和=方向性(n<30 或双模型推断) —— 可信度**画进图形本身**, 不能只在脚注写一行字, 否则"先误导视觉再文字更正"违反诚实原则; ④ **工程噪声与学习者语言分离**: API 路径/审计状态字样/内部里程碑词(Phase D)默认不进面向消费者的 UI, 用 `?debug=1` 开发者态显示, 但**诚实标注的语义和数字一个不能删**(只翻译措辞, 不删信息)。

### 坑28 (坑16 具体实例强化): 模糊题型变体宁可诚实 skip, 不自行扩展别名表 (2026-07-03)
- **反例场景**: 新补的教研解析里出现 "词义指代题"(词义+指代二合一表述), 现有 `exam_point_taxonomy.yaml` 的 `analysis_label_aliases` 只收录了明确同义词(词义猜测题/词句猜测题/词义推测题→理解词汇), 没有这一变体。当时的选择是: 自己判断"这题本质是猜词义, 应该算同义" 并直接往 yaml 加一条别名, 还是保持现状让它被 `_skill_of` 正确 skip?
- **决定 + 理由**: **不加**。yaml 头注释已明确"仅明确同义入yaml; 模糊题型不列 → skip 防臆造"——这是项目既有的、经坑16 教训后校准过的保守阈值, 我基于单个样例做的语义判断和当年被坑16 打脸的"双模型 inference"本质是同一类风险(我自己就是那个可能系统性判断错的模型)。**结果**: 14/15 题正确分类, 1 题诚实留空, 好过 15/15 但混入 1 个可能错的语义判断。
- **通用规则**: 遇到"这个新变体是不是该归入已有类目"的边界判断, 默认**不**扩展判断规则表(除非能找到 ≥2 个独立源明确定义这是同义), 让流水线诚实 skip; 在报告里写清楚"为什么没扩展 + 影响多小(1/15)", 把决定权交还用户, 不要因为想"凑整数/更完整"就放宽本已校准好的诚实阈值。

### 坑29: "整单元零命中才兜底"式条件把兜底路径锁死 — 一个误命中就让整个 pass-2 失效 (2026-07-04)
- **反例**: 用户反馈教材单元页"只看得到单词, 看不到短语/句型/表达方式/语法"。追下去发现 `section.py`
  的 pass-2(整页扫多词锚点, 坑22 修 10 waiyan 单元页首是练习正文) 被 `if distinctive_re and not out`
  锁住(仅当 pass-1 整单元**零命中**才兜底)。但绝大多数单元 pass-1 会先误命中 1 个**单词**锚点(如页首
  练习指令行"Writing a story..."匹配到单字"Writing"), 这个"非零命中"就让"零命中"条件为假, **整个
  pass-2 全单元跳过** — 真正的多词 section 标题(Understanding ideas/Using language 等)永不被扫到。
  78 单元 dry-run 实测: 只有 25/78 单元真正跑了完整 6 段结构, 大部分单元实际只捕获 1-2 段。
- **发现方法**: 用户说"看不到 X"时, 先假设"数据地基缺" 是错的默认——**先直接读原始 PDF 的对应
  页范围原文**(`PdfReader.pages[i].extract_text()` 全文, 不是只看 extracted 结果), 确认锚点文本
  到底存在不存在。本例锚点**全部存在**且顺序完整, 证明是提取代码的匹配条件 bug, 不是数据真缺。
  **"某类知识点覆盖率异常低"时, 先按 `(version_key,volume_key)` 分组看覆盖率分布**——如果同一版本
  不同册的覆盖率差异巨大(如 renjiao bixiu_1=6/6 但 xuanze_1-4=0/5), 大概率是代码路径 bug 而非
  教材内容本身参差不齐(教材内容分布通常不会这么整齐地按册断崖式清零)。
- **修复**: 把"仅当零命中才兜底"改成"兜底总是跑, 用 `seen` 去重只补漏"——**已命中的锚点是不可变
  查找表, 兜底扫描对它们是纯加法不会覆写**, 所以对已经工作正常的单元(pass-1 全对)零影响, 对残缺
  单元只会变多不会变少。dry-run 验证: 提取一个 `scan_unit_OLD`/`scan_unit_NEW` 双版本函数跑全量
  78 单元对比, 断言"新版本每单元 anchor 集合 ⊇ 旧版本 anchor 集合"(而不仅仅是数量不减, 集合包含
  关系更严格), 0 回归才落库(坑22 既有纪律的强化: 不只对比数量还要对比具体内容)。
- **连带效应(骨牌覆盖率)**: 这类"某张核心中间表覆盖率低"的 bug 常有连带面——本例 `sections` 表
  完整后, 依赖它的 `grammar_occurrences`(15→51 单元)之外, `section_text` 更完整也让下游**不依赖
  sections.kind 只依赖 section_text 文本量**的 `phrases.py`(短语/句型/表达提取, 靠预定义模式扫
  文本)间接受益(sentence_pattern 46→63, function_expression 57→70)——**改一个"底层结构完整性"
  的 bug, 要检查所有下游消费表的覆盖率一起复核, 不能只看直接报告问题的那一张表**。
- **规则数据化扩容的顺序**: 语法映射表(`grammar_topic_map.yaml`)只有 12 条規則, sections 修复后
  暴露"58 个 Grammar 段只匹配 31 个"的二级缺口——**先扩大匹配窗口(160→300字, 纯机械, 零风险)**,
  再看仍未匹配的文本找**教材原文明确写出的标准术语**(如 "Present perfect passive"/"Ellipsis"/
  "tag question") 加规则, **具体规则必须排在对应 umbrella 规则之前**(有序匹配, 坑16 一致的"仅明确
  同义"纪律——"predicatives"不写"predicative clause"就不加, 通信意图短语"Talk about your future
  plans"不臆测成某语法点, 诚实 skip)。

### 坑30: "考察重点"可视化只能挂已有真实边, 不能为了"更完整"而新造一个口径
- **背景**: 上述坑29 修复覆盖率后, 用户还要求"这些也都该在指出考察重点后可视化的列出"。三类知识点
  三种诚实处理, 不能一刀切:
  - **单词**: 已有 `exam_vocabulary.gaokao_hit_ln`(真题命中次数, 真值) → 直接 LEFT JOIN 挂徽章。
  - **语法**: 已有 `exam_grammar_stats.grammar_exam_stats()` 算出的课标第二级子类辽宁考查占比
    (真值, tests_grammar 边) → 新增 `grammar_category_pct()` **复用**该函数输出(不重跑聚合 SQL,
    Rule1), 把每条 occurrence 的 grammar_item_id 向上查父类目, 查表拿占比, 查不到诚实标"暂无
    考查数据"(不是 0%——0% 意味着"考了但占比0", "暂无数据"意味着"这个类目辽宁卷没有考查边样本",
    两者语义不同, 混淆就是坑12 式的"分析无效")。
  - **短语/句型/表达方式**: 没有短语级考查边(教材出现库, 非考查库)——**不给它们编一个"考察重点"
    数字**, 保留既有的诚实 caveat("出现非考查"), 只是把这句文案抽成共享常量(`PHRASE_LIB_NOTE`)
    跟真题特点页统计口一致(Rule5 可复用, 别写两句意思一样但措辞不同的话)。
- **规则**: "指出考察重点"类需求来了, 先按每个子类目分别问"这类东西有没有第一手考查边/统计?"——
  有则挂真数据, 没有则保留"无"的诚实态, **不能因为用户要求可视化就倒逼出一个新口径去凑"每类都有
  重点标注"的表面一致性**(那是自我-defeatist 的反面: 为了"看起来完整"而牺牲诚实)。

### 坑31: 泛化关键词子串匹配层级化 taxonomy 会跨枝/跨层误配, 精确匹配才安全 (2026-07-07)
- **反例**: `grammar_4q.py::_collect_core_ids` 用 `kw in label` 全局子串反查 `grammar_items`(带
  `depth`/`parent_id` 的树状课标语法点表)——泛化关键词"名词"会误配到*完全不同分支*的"名词短语"
  (parent="短语"类目, 跟"名词"类目无关), "被动语态"/"现在完成"会误配到*同分支更具体的子节点*
  (7个具体时态×语态复合节点、"现在完成进行"), 真实考试证据(如"were used"仅是简单过去时被动)
  被泛化牵连出一堆没被证实的复合形态"必教"标签。独立 workflow 复算实测 core 计数从 43(带 bug)
  精确修复后降到 25(17 个确认误配全排除)。同坑7"子串过度归因"的**层级树变体**(坑7 是扁平标签
  误配, 这次是带 parent_id 的树状结构, 误配模式多一种"跨枝"维度)。
- **修复(不是简单禁用子串, 按语义类型分层)**: 默认精确相等(`label == kw`); 仅"文体变体非独立
  维度"的家族(如从句类: 限制性/非限制性定语从句是同一从句机制的两种表述)允许精确命中后含
  `parent_id` 子孙; 需要缩写映射的术语(如"不定式"→"动词不定式")用**枚举前缀例外**(非泛化前缀
  规则); 课标未单列独立节点的复合概念(如"比较级"/"最高级"合并进"形容词的比较级和最高级")用
  **枚举具体目标例外**(非泛化子串规则)。三类例外都是显式白名单, 不是放宽通用规则。
- **通用规则**: 反查树状/层级化 taxonomy(带 parent/child 关系) 时, 关键词子串匹配的风险比反查
  扁平标签表更高——子串会同时命中"完全不相关的另一分支"(跨枝)和"同分支但引入额外维度的更具体
  子节点"(跨层/组合爆炸)。默认精确匹配, 泛化例外必须逐条验证"这个上位词命中所有下位词在语义上
  是否站得住"(问自己: 泛化提及上位概念, 能不能证明每个具体下位形态都被专门考过?), 通不过就归入
  显式枚举例外表, 不留通用的"kw in label"式子串规则。

## 3. 发现方法 (通用技巧)
- **工具优先, grep 兜底** (跨项目纪律见全局 [[mythos]] + [[codegraph-architecture-audit]]): 找"影响面/漂移/陈旧"先用工具:
  - `codegraph query <symbol>` / `codegraph explore <task>` / `codegraph node <name>` → 定位符号 + fan-in + blast-radius (本项目已装)。
  - `moth assert --repo .` → claims-vs-reality 漂移检测 (2026-06-15 已注册 **20 条**断言守数据+分析诚实性: 真题 provenance/EOL入库/学情派生/Phase7回滚/停用词/D0门/趋势province锚定/练习非押题; 见 `.moth/assertions/claims.yaml`)。**改数据/真题/题库前后跑一次, 红=回退。**
  - 人肉 grep 是这些工具的兜底, 不是首选。我 2026-06-15 没用 codegraph/moth 直接 grep = 反面教材。
- **绿门审计**: 任何"X 通过/100%"先 grep 它的断言, 列出**它测了哪些维度**; 未断言维度=盲区。
- **fresh vs 快照**: audit_findings/report 类是产物, 跑 run_all/重算刷新, 别信 committed 数字。改 DB 类审计前备份(ATTACH 自己的 bak 还原)。
- **provenance 溯源**: 派生事实先问 source_repo/lineage 可信度; 不同源不同可信度, 别混同。
- **smoking gun 抽查**: 怀疑某类数据错, 找一条已知正确答案的标志性行(如某篇 = 某卷)grep 验。
- **派生完整性**: 派生表(weakness/qb/edges)每行能否 join 回上游真实数据; 0 orphan 断言。
- **对抗验证**: 修完故意再制造该问题, 确认 gate 抓到; 修复自愈确认回绿。大改 commit 前 spawn subagent 对抗审查(Rule 10, codex 不可用用 general-purpose)。

## 4. 修复模式 (通用)
- **单一计算点修复 > 打补丁数据**: 改 services/ 计算逻辑(idempotent), 重跑落库, 重建可复现; 别只 UPDATE 数据(下次重建退化)。
- **gate 断言防回归**: 每条数据修复加一条 data_accuracy_check 断言锁死维度。
- **诚实降级**: 不能证明的标 `未知/待核验`, 保留 lineage(analysis 字段记来源/可信度), 不伪造。
- **YAML 数据化判断**: 停用词/卷型契约/阈值/source 状态进 config/*.yaml。
- **门禁对真实诚实**: 数据状态变了(仅真题/池缩小), 门禁断言改成反映真实(动态/降级), 不为过门保留旧假设。

## 5. 工具调度
| 场景 | 命令 |
|---|---|
| **新 session 看 live 状态(单一入口)** | `python3 -m scripts.tools.map doctor`(默认 = 替代分别跑 4 个工具; `--strict` 红退非零供 CI/stop_gate) |
| D0 全校验 | `python3 scripts/data_accuracy_check.py`(exit 0) |
| Stop 门禁 | `bash scripts/stop_gate.sh`(audit FAIL/WARN + D0 + CC baseline + 前端 inline) |
| 刷新审计 | `python3 -c "import duckdb; from backend.services.audit import run_all; run_all(duckdb.connect('data/db/gaozhong.duckdb'))"`(会改 audit_findings, 用 bak 还原) |
| 全库重建 | `python3 scripts/init_db.py`(schema→mirror→EOL→refine→canonical→links→qb→courses→students→audit) |
| 复杂度 | `python3 scripts/lib/complexity_check.py <file>`(CC>10 报 WARN) |
| 定位符号/影响面 | `codegraph query <symbol>` · `codegraph explore <task>` · `codegraph node <name>` · 改完 `codegraph sync .` |
| 架构/大改前 | `/codegraph-architecture-audit`(fan-in>3 / god-module 改前, 全局 skill) |
| 漂移检测 | `moth assert --repo .`(11 条数据诚实性断言, verdict=PASS 才健康); `moth doctor` 取结构快照 |
| 改 services/db/api 前 | PreToolUse hook 自动提示复杂度; 提示跑 codegraph 就先跑 |
| **端点契约全量检查**(坑24) | `python3 scripts/lib/endpoint_contract_check.py --quiet`(75端点 in-process 直调, 双向覆盖率自检, <2s); 新端点必须先在 `backend/config/endpoint_contracts.yaml` 补契约再合并 |
| **改前影响面盘点**(坑23) | `moth coupling --repo . --impact <模块名>` + `grep <模块名> .moth/assertions/claims.yaml` + `codegraph query <symbol>` 三件套, 不能只看前端 nav 隐藏就当模块死了 |
| **补数据前先查本地**(坑26) | `find data/external data/structured -iname '*<年份/关键词>*'` 扫描候选文件 + marker 核对, 确认本地真没有才上网; 网络检索优先用真值锚独有专名精确查询, zhihu 403 别试 |

> ✅ **moth 已就位** (2026-06-15): `.moth/profile.yaml` 注册了 `.moth/assertions/claims.yaml`(11 条断言: no-gaokao-fake-liaoning / eol-truth-imported / weakness-derived-no-orphan / qbank-real-only / no-stopword-tags / d0-accuracy-green 等)。**真相变化时同 commit 改断言**(声称-实况对账, 弹仓红=回退/腐烂)。新增带数字的关键真相就挂一条断言。

> ✅ **项目地图 CLI 已就位** (2026-06-15, 架构师顶层设计): `python3 -m scripts.tools.map [doctor|modules|gates|drift|stats] [--json] [--strict]` — **只读聚合 4 套真相源**(`project_architecture.yaml` 模块/配置/数据契约 + `m0_gate_plan` 17 门 + `moth assert` 弹仓 + `project_architecture_audit` 状态 + read-only DB 计数), 不另起炉灶、纯复用现有真相源、CC<10。实现在 `scripts/tools/map/{__main__,collect}.py`。
> - `doctor`(默认)= **新 session 接手看 live 状态的单一入口**, 替代分别跑那 4 个工具; `--strict` 有红退非零, 供 CI/`stop_gate` 接。
> - `doctor` 还对辽宁真题**年度样本量 < 10 的年份标"样本不足不可下趋势结论"**(D0 样本量透明, 见坑12 分析诚实门)。

## 5.5 数据源模块地图 (data_sources/, M6 2026-06-15 系统化)
`backend/services/data_sources/` 是数据获取/提取的**单一计算点层**。改 extract/clean 逻辑改这些模块, 不改入口。

| 模块 | 职责 |
|---|---|
| `registry.py` | 源目录(读 `sources.yaml`), 源元数据/可信度入口 |
| `fetcher.py` | HTTP 下载 + sha256 + manifest(**直连源**, 非 JS 页) |
| `acquire/web.py` | crawl4ai 本机 Chrome(JS / 在线页; **`chrome_channel="chrome"`**, 见坑9) |
| `extract/gaokao_bench.py` | GAOKAO-Bench JSON → record |
| `extract/pdf.py` | PDF → 文本(校验 `%PDF` 头)+ 题型分段 |
| `extract/curriculum_vocab.py` | 课标 PDF → 词表 |
| `clean/exam_paper.py` | category-aware 卷型分类 |

> **薄壳化原则**: 三个原始入口都已委托上面这些模块, 改 extract 逻辑**改模块不改入口**:
> - `backend/services/extraction/exam.py`
> - `scripts/import_recent_exams.py`
> - `scripts/tools/audit/cross_verify_pdf.py`

## 6. 真相源文档地图
- **现行法律**: agent.md(现行规则) · goal.md(控制板, 有漂移) · docs/architecture.md(八铁律) · backend/config/project_architecture.yaml(机器契约)。
- **判定/证据**: docs/data_accuracy_audit.md(D0 总表) · docs/lessons_learned.md(L-A..L-U 教训) · analysis/project_state_ledger.md · backend/config/m0_gates.yaml(M0 gate)。
- **真题真值**: data/external/exam_sources/eol/(EOL 2021/2022 真题源 + review_decisions) · local_pdfs(2024/2025) · gaokao_bench(2010-2023)。
- **配置即判断(20+ YAML)**: sources / exam_paper_contracts / import_policies / source_states / eol_review_* / stopwords / thresholds / political_blacklist。
- **legacy(不作当前规则)**: CLAUDE.md(冲突以 README 索引/goal.md 为准)。阶段性快照文档(RESUME/round/closure)已删 — live 状态用 `moth assert` + DB 实测, 不靠快照。
- **数据现状(2026-06-16 复核, 件3完成)**: clean `init_db` 可复现基线 = exam_questions **472** / 辽宁 **188** / eol **110** / local_pdf **18**; question_bank 仅真题(无合成); 生成层已回滚。**三门全绿**: `data_accuracy_check` exit0 + `moth assert` PASS(28/0) + `stop_gate` exit0(含 CC>15门+架构契约门)。件1/2/3(趋势分层/考点canonical/关联性第三条腿) 已落地+D0维度21-23锁。
- **⚠ 陈旧说法纠偏(2026-06-16 实证, 防误导)**: 旧"待办: 教材完整提取(外研选必4 零单元/覆盖46%)" **是混淆+defeatist 工件, 已证伪**:
  - 教材**提取**实际相当完整: units **77/77 全册**(renjiao 7册 + waiyan 7册; **waiyan/xuanze_4 = 6 units 非"零"**); 词表 14册全有(unit_vocab_intro 198-377/册); section 课文 **67/77 单元有(87%)**。
  - ~~真缺口 = 10 个 waiyan 单元缺 section 课文~~ **已补 (2026-06-16, commit 2ad0899)**: `section.py _scan_unit` 加 pass-2 (零命中兜底, 整页扫多词锚点 Starting out/Understanding ideas... 不误命中正文); sections **150→216**, 单元覆盖 **67→77/77 (100%)**, 全有正文。最小回归 (67 工作单元字节不变, dry 对比回归=0)。
  - "46%" 实为**另一指标**: 教材词表覆盖课标3500词的 46.3%(goal.md §越纲率), 是**真实数据特征**(教材本就不覆盖全部课标词), **非提取缺口**, 别再当"地基不完整"卡 §1.1 gate。
  - 待办(精确): ① ~~补 10 waiyan 单元 section~~ ✅ done ② 4 god-module 拆分(task_90d55f25)。
  - **section 提取教训 (坑22)**: PDF section 锚点不一定在页首 (外研版练习页页首是题干, section 标题在页中)。锚点扫描"只看前 N 行"对这类 layout 漏 → 辨识度高的**多词锚点**可整页扫 (不误命中正文), 单词锚点限页首。改提取逻辑必 **dry 对比逐单元新旧 section 数** (回归=0 + 只填空不动 working 单元) 才落库。
