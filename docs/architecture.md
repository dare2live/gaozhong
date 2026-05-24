# gaozhong 顶层架构 (v2 — 知识图谱 + 单一计算点)

> 用户 2026-05-23 明确: **"从顶层设计的角度来总体设计架构, 模块化 可扩展 可复用, 而不是到处计算各自展示"**.
> 本文是后续所有代码的强约束, 反此设计的 PR 直接拒.

---

## 0. 八条铁律 (系统级强制, hook 配套)

> 1-3 为原版铁律 (单一计算点 / Canonical First / Edges 一等公民).
> 4-8 为 2026-05-24 用户反馈新加 (模块化 / 可复用 / 可扩展 / 不牵一发动全身 / 反模式禁令).
> 每条违例必须 hook 自动检测, 否则会被遗忘.

## 0.

### Rule 1 — 单一计算点 (Single Computation Point)
任何派生事实 (vocab CEFR level / unit 主题 / 短语越纲与否 / 题目难度 / 知识点关联强度) 只在 **services/** 层算**一次**, 入 DB 表或视图. **API / 前端 / 脚本 不准重复 JOIN/SUM/计算同一事实**.

错例 ❌:
```python
# bad: api/main.py 里 ad-hoc JOIN, 前端拼字段
SELECT v.word, t.unit_number FROM unit_vocab_intro v JOIN units t ...
```
正例 ✅:
```python
# good: services/links.py 算好, 灌进 view vocab_with_unit
SELECT * FROM vocab_with_unit WHERE word = ?
```

### Rule 2 — Canonical Model First
任何对象 (词 / 语法点 / 主题 / 单元 / 课文 / 短语 / 题目 / 知识点) 必须先有 canonical 表示 (PK + 不可变属性), 再谈关联. 不允许"一次性脚本里 zip 出来的字典" 当事实源.

### Rule 3 — Graph Edges 是一等公民
不允许在 schema 里塞 "related_unit_ids JSON 数组" 这种 inline 关系. 任何 N:M 关联走 **`edges` 表** (src_node_id, dst_node_id, relation, weight, evidence). 这样:
- 关联可被独立扩展 (新增 relation 不改主表)
- 推理 / 查询走统一图遍历 (graph service), 不到处写 SQL
- 出题 / 推荐 / 教学路径 = 图查询

### Rule 4 — 模块化 (新功能先扩, 不新建)
加新功能前必须先查 codegraph: 已有 service / route / extractor 能否复用? 不能再建.
- **检查方法**: `codegraph query <symbol_name>` 看是否已有同名/近似 fn
- **违例**: 我加 `teacher.html` 没复用 `index.html` 的 `app.js` → L-G
- **hook 自动**: PreToolUse 新建 html/py 时, 先扫"同目录是否已有相似命名/职责文件"

### Rule 5 — 可复用 (helper 抽 common)
任何在 ≥ 2 处出现的逻辑必须抽到 shared:
- 前端: `frontend/static/common.js` (fetchJSON / tagChip / renderTable / parseForm)
- 后端: `backend/api/db.py` (db_ro / rows_to_dicts), `backend/services/<area>/common.py`
- 模板: `frontend/_layout.html` (header/nav/footer)
- **违例**: index/teacher/student 三页各自重写 fetch+render → L-G
- **hook 自动**: 改 frontend/*.html 时检测 inline `fetch(` / `<script>` 块大小 > 50L → 警告抽出去

### Rule 6 — 可扩展 (向后兼容加列加表加 relation)
- schema: 加列 + DEFAULT, 不改字段语义; 加新表, 不破坏现有表 PK
- relation: 加 `ALLOWED_RELATIONS` 字典, audit 自动校验
- API: 加 `/api/foo/v2`, 不破 v1; query param 添加要 backward-compatible
- **违例处理**: 改 schema/api 必须能跑 `python3 scripts/init_db.py` + 现有 endpoint 仍 200

### Rule 7 — 不牵一发动全身 (fan-in 警戒)
改 fan-in > 3 文件前必须:
1. `codegraph query <symbol>` 看下游
2. 改 service 函数签名 → 同时改所有 caller (一次性, 不留半成品)
- **违例 hook**: `scripts/precode_review_hook.sh` 已含 fan-in 检测, 但只 WARN; **升级到 fan-in > 5 BLOCK** (exit 2)

### Rule 8 — 反模式禁令 (一票否决)
| 反模式 | 违例 | 自动检测 |
|---|---|---|
| god-module > 400 L | 拒收 | `audit/codequality.audit_code_size` FAIL |
| CC > 15 | 必须拆 | `audit/codequality.audit_code_complexity` FAIL |
| 前端 inline `<style>` 块 > 30 L | 必须抽 css | `audit/frontend_dupe` (待加) |
| 前端 inline `<script>` 块 > 80 L | 必须抽 js | 同上 |
| API endpoint 写 SQL JOIN | Rule 1 反例 | code review 拦 |
| `try: ... except: pass` 静默吃错 | 见 CLAUDE.md §1.5 | grep CI |
| "形式 OK, 实质未验" (eg 跑通但没真用数据查) | L-J | Stop hook 跑 init_db 真审计 |
| 用户问后才发现的盲区 | M-5/M-6 元教训 | 见下条 |

---

## 元约束: hook 系统化, 不靠口头

| 时机 | hook | 做什么 |
|---|---|---|
| 改代码前 | PreToolUse (`Edit\|Write\|MultiEdit`) | size / CC / fan-in / 前端重复 → WARN 或 BLOCK (exit 2) |
| 新消息进来 | UserPromptSubmit | 检查 git uncommitted + .claude/in_progress.md → 提醒 "先完成手头" |
| Session 启动 | SessionStart | 注入 lessons 前 5 条 + 架构铁律 |
| Session 结束 | Stop | 跑 `init_db` 全审计 + complexity 扫 → 任何 FAIL 阻断 stop |

**永不接受**: "下次我注意" 类承诺. 任何重复 ≥ 2 次的失误必须落 hook.

---

## 1. 分层 (Layered Architecture)

```
┌─────────────────────────────────────────────────────┐
│  Layer 5: View (前端 HTML/JS)                        │
│    只调 API, 不做计算. 不解析 raw, 不再 JOIN.        │
├─────────────────────────────────────────────────────┤
│  Layer 4: API (backend/api/, stdlib http.server)    │
│    薄壳, 每个 endpoint ≤ 30 行, 调 service 即返回.  │
├─────────────────────────────────────────────────────┤
│  Layer 3: Services (backend/services/)              │
│    canonical / links / graph / extraction /          │
│    audit / exercise.   ⬅ 唯一允许计算的地方.        │
├─────────────────────────────────────────────────────┤
│  Layer 2: Store (DuckDB, gaozhong.duckdb)           │
│    canonical 表 + edges 表 + 物化视图.               │
├─────────────────────────────────────────────────────┤
│  Layer 1: Raw / External                            │
│    data/{textbooks,curriculum,external,structured}  │
│    PDF / XLSX / DOCX / JSONL / JSON / HTML 原始档.   │
└─────────────────────────────────────────────────────┘
```

跨层调用 = 反模式. 例: API 直接读 PDF 是错的, 必须先 Layer 3 抽出 → Layer 2 落表 → Layer 4 查表.

---

## 2. 模块 (backend/services/, 复用单位)

| 模块 | 职责 | 唯一输入 | 唯一输出 |
|---|---|---|---|
| `extraction/curriculum.py` | 课标 PDF → cefr_vocab / grammar_items / theme_contexts | Layer 1 PDF | Layer 2 三张课标主表 |
| `extraction/textbook.py` | 教材 PDF → units / sections / phrases / vocab_intro | Layer 1 PDF | Layer 2 教材层表 |
| `extraction/exam.py` | 高考题 JSON → exam_questions / question_options | Layer 1 GAOKAO-Bench jsonl | Layer 2 exam 表 |
| `canonical/concept.py` | 把跨表实体统一为 concept_node (word/grammar/theme/phrase/unit/question 等) | Layer 2 主表 | `nodes` 表 |
| `links/build.py` | 计算/插入 N:M 关系 (词→单元, 短语→主题, 题目→知识点) | `nodes` + 主表 | `edges` 表 |
| `graph/query.py` | 单一图查询入口: 邻居/最短路/子图/中心度 | `nodes` + `edges` | dict / list |
| `audit/cross_check.py` | 完整性 + 准确性核查 (课标 vs mahavivo, 教材 vs 课标, PDF sha 等) | Layer 1 + Layer 2 | `data/audit/<date>.jsonl` + DB `audit_findings` 表 |
| `exercise/generate.py` | 给定约束 → 出题候选 | `graph/query` + 题型模板 | 题目对象 |

**绝对禁止** 在 `api/` 内写 SQL JOIN 或自定义聚合 — 一旦发现, 必须下沉到 `services/`.

---

## 3. 数据流 (从 PDF 到出题, 端到端)

```
raw PDF/JSON                services 层                       DB                        API/view
─────────────              ────────────                     ──────                    ────────
课标 4.英语.pdf  ──→ extraction/curriculum.py ──→ cefr_vocab / grammar_items / theme_contexts
教材 14 册 PDF   ──→ extraction/textbook.py   ──→ units / sections / vocab_intro / phrases
GAOKAO-Bench    ──→ extraction/exam.py        ──→ exam_questions / question_options
辽宁附件1.xlsx   ──→ extraction/directory.py   ──→ allowed_publishers / city_choice

                  └─→ canonical/concept.py    ──→ nodes (统一 PK: concept_id)

                  └─→ links/build.py:
                        word -[in_unit]→     unit         (教材引入)
                        word -[cefr_level]→ level         (课标分级)
                        grammar -[in_unit]→ unit          (教材出现)
                        theme   -[of_unit]→ unit          (单元主题)
                        phrase  -[evidence]→ section      (出处)
                        question -[tests]→ word/grammar  (考点)
                        question -[year]→  exam_year      (年份)
                        unit    -[in_volume]→ volume      (册)
                                     ↓
                                edges 表

                  └─→ audit/cross_check.py    ──→ audit_findings (cross check)
                                     ↓
                              所有上层只查 nodes/edges/views, 不直读主表 raw

api/main.py                    GET /api/graph/neighbors?node=word:apple   →  graph/query.py
                              GET /api/exercise/generate?unit=B1_U1      →  exercise/generate.py
                              GET /api/audit/findings?date=2026-05-23    →  审计快照表

frontend/index.html            只 fetch + render, 永不做派生计算
```

---

## 4. 不该长在一起的东西 (反内聚)

- ❌ 不要在 `extraction/textbook.py` 里查 `cefr_vocab` 做越纲判 — 那是 `links/` 的事 (extraction 只产出 raw)
- ❌ 不要在 `exercise/generate.py` 里 JOIN units 表 — 走 graph query
- ❌ 不要在 `api/main.py` 里把字典 mutate 后再返回 — service 应返回 final dict
- ❌ 不要在 `scripts/init_db.py` 里写业务计算 — 它只负责装载已经计算好的 jsonl

---

## 5. 可扩展性 (新增功能时改哪里)

| 新需求 | 改的文件 | 不改的文件 |
|---|---|---|
| 新增一个出版社 (上海版进辽宁) | 1 行 jsonl + 重跑 links/build | API/前端/schema 全不动 |
| 新增一种关系 (eg word→synonym→word) | links/build.py 加一个 builder; edges 表自然容纳 | schema/api 不动 |
| 新增一种题型 (听力) | exercise/generate.py 加 template, exam.py 抽器 | graph/links 不动 |
| 新增一个学科 (语文) | 整个 backend 复用, 仅 raw 路径换 + extraction 实现换 | api/前端代码不动 |
| 切换 DuckDB 到 Postgres | 改 1 处连接, schema.sql 几乎原样 | 业务/api 不动 |

---

## 6. 与姊妹项目 gaokao 的关系 (再次强调)

- **DuckDB 独立**, 不 ATTACH 不混用 (用户硬性约束).
- 真题数据**单向** 从 gaokao 项目镜像到 `data/external/gaokao_bench/` (jsonl 复制), 不读 gaokao 的 DuckDB.
- 两边交点: 只是知识图谱里 `question` node 引用同一 GAOKAO-Bench `index`, 各自项目自治.

---

## 7. STEP 路线 (本架构下的实施)

| STEP | 输出 | 关键 service | 验收门 |
|---|---|---|---|
| 1 (✅) | 资料基石 + MVP 骨架 | extraction/curriculum (P0) | DB 7 张表, API 8 endpoint, 前端 7 区块 |
| 2 | 教材结构化 + 知识图谱 v1 | extraction/textbook + canonical + links | 14 册 100% 切 Unit, edges ≥ 5k 条 |
| 3 | 真题对齐 + 考点映射 | extraction/exam + links (question→word/grammar) | 辽宁卷 5 年题全入图, 每题 ≥ 3 个 edges |
| 4 | 趣味化内容生成 (LLM, 课标硬约束) | exercise/generate + LLM service | 每单元 ≥ 3 类内容, 越纲率 < 5% |
| 5 | 作业生成体系 (4 级) | exercise/generate (高级) | 课时/单元/阶段/总体 4 套, 难度可控 |
| 6 | 评估闭环 | telemetry service | 学生答题日志 → 弱点 → 推送 |

每 STEP 完成时, schema 不破坏性扩 (加列/加表), 不允许"改字段语义" 类破坏性变更.

---

## 8. 顶层模块图 (ASCII)

```
                       ┌──────────────────────┐
                       │  Layer 1: Raw Files  │
                       │  PDF · XLSX · JSON   │
                       └──────────┬───────────┘
                                  │
        ┌─────────────────────────┼────────────────────────┐
        ▼                         ▼                        ▼
┌──────────────┐         ┌───────────────┐         ┌──────────────┐
│ extraction/  │         │ extraction/   │         │ extraction/  │
│ curriculum   │         │ textbook      │         │ exam         │
└──────┬───────┘         └───────┬───────┘         └──────┬───────┘
       │                         │                        │
       ▼                         ▼                        ▼
┌────────────────────────────────────────────────────────────────┐
│  Layer 2: DuckDB canonical tables                             │
│  cefr_vocab | grammar_items | theme_contexts | units |        │
│  sections | vocab_intro | phrases | exam_questions | ...      │
└──────────────────────────┬─────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌──────────┐
        │canonical│  │  links  │  │  audit   │
        │/concept │  │ /build  │  │/cross_ck │
        └────┬────┘  └────┬────┘  └────┬─────┘
             ▼            ▼            ▼
        ┌────────────────────┐  ┌──────────────┐
        │ nodes + edges 表   │  │audit_findings│
        └─────────┬──────────┘  └──────┬───────┘
                  │                    │
        ┌─────────▼─────────┐          │
        │  graph/query      │          │
        └─────────┬─────────┘          │
                  ▼                    ▼
        ┌────────────────────────────────────┐
        │   Layer 3.5: exercise/generate     │
        └──────────────────┬─────────────────┘
                           ▼
                 ┌─────────────────┐
                 │  Layer 4: api/  │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ Layer 5: HTML   │
                 └─────────────────┘
```
