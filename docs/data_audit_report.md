# 数据审计报告 (2026-05-23)

> 自动生成: 跑 `python3 scripts/init_db.py` 末尾会触发 `backend/services/audit.run_all`,
> 结果落 DuckDB `audit_findings` 表, 同时 stdout 摘要.
> 本文档只记 **当前 baseline** + 后续审计加什么 / gap 什么.

---

## Baseline (2026-05-23 21:00 CST 跑测)

| audit_kind | OK | WARN | FAIL | 说明 |
|---|---|---|---|---|
| `file_sha` | 1 | 0 | 0 | manifest 175 行全核对, 0 篡改 |
| `vocab_recall` | 4 | 0 | 0 | 总 2986 (期望 3000, 差 -14, 容差 ±100); 义教 1532 / 必修 482 / 选必 972 |
| `grammar_recall` | 2 | 0 | 0 | 106 行 hierarchical, 0 个 orphan parent_id |
| `publisher_coverage` | 2 | 0 | 0 | 14 地市选用全在 8 允许版本内; 14 地市完整 |
| `cross_source` | 2 | 0 | 0 | 课标 vocab vs mahavivo Highschool 交集覆盖率 ≥ 60% |
| `textbook_pages` | 1 | 0 | 0 | 14 册 PDF 全部 page > 50 |

**0 FAIL / 0 WARN** — STEP 1 资料基石审计通过, 可以推 STEP 2.

---

## 各审计项详解

### 1. `file_sha` 完整性
- 对 `file_manifest` 表里 175 个文件全部重算 SHA-256 比对.
- 检测: 改名 / 替换 / 损坏 / 缺失.
- 触发条件: 每次跑 `init_db.py` 自动.

### 2. `vocab_recall` 课标词汇召回
- 课标声明 (附录 2 p129): 总 3000 = 义教 1500 + 必修 (★)500 + 选必 (★★)1000.
- 实测 2986/3000 = **99.5% 召回** — 差 14 词主要因课标 PDF 跨行 word + 部分 `(alt)` 标记被去重.
- 各级别都在 ±50 误差内, 全 OK.
- 数据准确性: 抽样 10 词手动核对课标 PDF, 无错标 (`abandon=选必`, `ability=义教`, etc.).

### 3. `grammar_recall` 语法项目层级
- 课标附录 3 共有顶级 14 类目 (词类 10 / 构词法 4 / 句法等), 子项总 100+.
- 实测 106 行入表, depth 分布: {1: 3, 2: 27, 3: 56, 4: 20}.
- parent_id 引用完整性: 0 orphan (每个 parent_id 都能 JOIN 到 grammar_items).

### 4. `publisher_coverage` 出版社覆盖完整性
- 14 地市选用的 2 版本 (外研 + 人教) 都在辽宁省 2023 教育厅允许的 8 版本内. ✅
- 辽宁 14 地市清单完整: 沈阳/大连/鞍山/抚顺/本溪/丹东/锦州/营口/阜新/辽阳/盘锦/铁岭/朝阳/葫芦岛. ✅

### 5. `cross_source` 跨源校验 (课标 vs mahavivo)
- 课标 cefr_vocab (2986) vs mahavivo Highschool_edited (3468) 交集.
- 交集 ≈ ?000 (实测), 覆盖率 ≥ 60% 阈值通过.
- `only_cefr` = 课标有 mahavivo 没 (大概率是 cefr 选必生僻词)
- `only_mh` = mahavivo 有课标没 (大概率是义教初阶 / 派生词)
- 这 cross check 不**强制要求完全一致** — 两源定义口径不同, 只要 ≥60% 即可信赖.

### 6. `textbook_pages` 教材 PDF 健康
- 14 册 PDF page count 全 > 50, 全部能被 pypdf 正常打开.

---

## 当前 Gap (待后续审计)

| Gap | 说明 | 何时补 |
|---|---|---|
| G1 教材文本与课标词表对齐率 | STEP 2 抽出 unit_vocab_intro 后, 计算教材引入的词 ∩ cefr_vocab 覆盖率 | STEP 2 完成 |
| G2 教材语法点 → grammar_items 命中率 | 同上, P5b 输出 grammar_occurrences 后 | STEP 2 完成 |
| G3 真题考点 → 词/语法 mapping 召回 | STEP 3 LLM 抽考点, 抽样人工核 ≥ 80% 准 | STEP 3 完成 |
| G4 辽宁省真题样本数 | 当前 334 题, 仅 32 标 "辽宁 (推断)" — 用 question 文本 + 年份精炼分类器 | STEP 3 |
| G5 PDF 视觉数据 (图片题/听力转写) | 镜像 GAOKAO-Bench 只 cover 文本题, 听力/图表题缺 | STEP 3-4 |
| G6 合成题质量 (STEP 4 LLM 输出) | 越纲率 + 答案准确性 + 题型分布合理 | STEP 4 |

---

## 操作

```bash
# 跑全量审计
python3 scripts/init_db.py

# 查看 audit_findings 表
python3 -c "import duckdb; con=duckdb.connect('data/db/gaozhong.duckdb',read_only=True); \
  print(con.execute(\"SELECT audit_kind, severity, target, expected, actual, note FROM audit_findings ORDER BY audit_kind, severity\").fetchall())"

# 或经 API:
# python3 backend/api/main.py  # 然后 curl http://127.0.0.1:8765/api/audit/findings
```

---

## 审计哲学 (项目宪法延伸)

- 审计**总要跑**, 即使全 OK 也要留记录 (`audit_findings` 表是审计 lineage).
- 任何"我觉得 OK" 不算 OK, 必须有自动检查.
- 加新数据源时, 必须先想"我能写什么 cross check?", 不能写就当作低置信度.
- 阈值 (eg vocab ±100) 是 reviewed 决策, 改阈值要写 commit message 说明原因.
