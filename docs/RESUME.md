# 断点续传 — 新 session 第一份读物

> 新 session 一打开: **先 invoke `gaozhong-ops` skill**(坑库+发现方法+修复模式)→ 读本文件 → `docs/README.md`(权威索引)→ `agent.md`(现行规则)→ `docs/architecture.md`(八铁律)。

最后停止时间: **2026-06-15**
最后 commit: **`ea8fd98`** refactor: 拆分 4 个 god-module + run_all 可复现绿
状态: **数据层已清洗, 三门全绿, moth 守漂移**。无"待修的严重数据问题"——2026-05 那批污染已全部闭环(见下)。

---

## 1. 当前状态 — 数据诚实性已闭环, 三门全绿

验证命令(接手先跑这三道, 全绿=健康):
```bash
cd /Users/dp/Documents/M/gaozhong
python3 scripts/data_accuracy_check.py     # D0 全数据校验, exit 0
moth assert --repo .                        # claims-vs-reality 12 条, verdict=PASS
bash scripts/stop_gate.sh; echo "exit=$?"   # stop gate, exit 0
```
定位/影响面用 `codegraph query <symbol>` / `codegraph context <task>`, **不人肉 grep**(见 skill)。

---

## 2. 2026-06-15 本轮成果 (6 commits, 真题基座 + 工程纪律双翻新)

| commit | 成果 |
|---|---|
| `18c01f6` | 真题 province/paper_type provenance-aware(假"辽宁新课标II"诚实降级)+ 学情弱点从写死改答题派生 + check_21 防回归 |
| `4f32fad` | 回滚 Phase 7 生成层(删 enriched 讲义/合成题/生成练习/65 week 演练 — 教材基石不完整不该有上层生成内容) |
| `fafd3d7` | **EOL 真题入库**: 2021/2022 辽宁新高考全国II卷走 review gate 入 exam_questions(替换 GAOKAO 混合卷占位) |
| `4bd83d8` | autotag/tests_word 去停用词污染(config/stopwords.yaml) |
| `d250543` | 注册 moth claims-vs-reality 弹仓(守成果不回退) |
| `ea8fd98` | 拆 4 个 god-module 到 <400 行 + codequality 基线对齐 → run_all 可复现 44 OK |

详见 `docs/lessons_learned.md` L-2026-06-15-R..V + `docs/data_accuracy_audit.md`。

---

## 3. 当前真题数据全景 (清洗后)

| 年份 | 来源 | provenance | 卷型标注 |
|---|---|---|---|
| 2010-2014 | GAOKAO-Bench | 辽宁当年自主命题, 数据为他省 | **全国卷(非辽宁)** 诚实降级 |
| 2015-2020 | GAOKAO-Bench | 国家卷期辽宁=全国新课标II | 辽宁(史实推断未逐题核验) |
| **2021/2022** | **EOL 中国教育在线** | **官方真题 + M0 review 核验** | **辽宁新课标II卷(110 题入库)** ✅ |
| 2023 | GAOKAO-Bench-Updates | repo 标卷型 | 辽宁新课标II卷 |
| 2024/2025 | local PDF | 全文核验 | 辽宁新课标II卷 |

- `exam_questions` = 454 行(真辽宁卷 152: 2021-2025)。GAOKAO 全国甲卷"Landscape Photographer"污染已删。
- `question_bank` = **仅真题**(178 + EOL, 无合成题/生成练习 — Phase 7 回滚)。
- `course_handouts` = 0(讲义生成层回滚); courses 40 + course_materials 结构骨架保留。
- 学情 student_weakness 100% 从 student_answers 派生(无写死假推); 知识图谱去停用词(tests_word 28430→16540)。

---

## 4. 下一步 / 已知留白

> 2026-06-15 实测纠正: "外研选必4 零单元 / 教材基石不完整" 是 lessons L (旧状态) 的**陈旧引用** — 实测教材基石**已抽全**: 77 单元(含 waiyan/xuanze_4 的 6 单元)、150 sections 全有 raw_text 正文、unit_vocab_intro 4056 词 100% 课标对齐、cefr_vocab 2986 分级。**教材覆盖课标 ~46%** 是数据特征(教材显式引入约 46% 课标 3500 词, 非提取缺口)。

1. ✅ **趋势/考点模型已重建(核心竞争力, commit 后)**: 真题清洗后 trend_analysis(288 题)/exam_patterns 在干净数据重建; 信号合理(应用文/续写↑)。
2. **官方源印证(真正未关项)**: 课标 3500 词官方词汇表 OCR 提取(data_gaps G2)· 沈阳"外研版"官方印证(现仅民间两源)· jyt.ln.gov.cn 教学用书目录缓存。这些是反爬/官方源问题, 非代码能解。
3. **M0 收口剩余**: 2021 听力答案源是 Sohu 候选(非官方 EOL 答案表), analysis 已留 lineage; 写作 rescope 未入(需 writing schema)。
4. **教学内容**: Phase 7 生成范文已回滚(用户决策: 不信任 LLM 生成内容)。若重建, 应基于已抽全的教材 + 干净真题, 且每条可反证(不偏离学校 §1.2)。
5. **CC 减债**: 仍 37 个 CC>10 函数(基线对齐现状), 可继续降。

---

## 5. 接手必读 + 工具

- **skill**: `gaozhong-ops`(`~/.claude/skills/`, 坑库8条+发现方法+修复模式)— 做实质工作前 invoke。
- **真相守护**: `.moth/assertions/claims.yaml`(12 条断言)— 改数据/真题/题库前后 `moth assert`。
- **文档**: `docs/README.md`(权威索引)· `goal.md`(控制板, 注意有历史漂移)· `agent.md`(现行规则, 非 CLAUDE.md)· `docs/architecture.md`(八铁律)· `docs/lessons_learned.md`(L-A..L-V)。
- **真题源**: `data/external/exam_sources/eol/`(EOL 2021/2022 + review_decisions)· `local_pdfs`(2024/2025)。
- **入库**: `backend/services/imports/eol_import.py`(EOL 真题)· `scripts/init_db.py`(全库重建)。
