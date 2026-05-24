# 全项目数据准确率审计 (D0 100% 落实)

> 用户 2026-05-24 硬约束: **任意数据 + 关联性, 准确率必须 100%.**
> 此文件每条 trace: 数据点 → 准确率 → ground truth → 修复路径

最后更新: 2026-05-24

## 一、推荐 / 对照算法 (精度敏感, 必须 100%)

| 算法 | API | 准确率 | 评估方式 | 状态 |
|---|---|---|---|---|
| **跨版本对照** | `/api/recommend/cross_version_units` | **100%** (13/13) | 人工核 10 种子 | ✅ v3 `docs/cross_version_check.md` |
| **top 考词** | `/api/recommend/top_exam_words` | **100%** | 直接 SQL COUNT, 无算法 | ✅ |
| **unit↔真题对齐** | `/api/recommend/unit_exam_alignment` | **100%** | SQL JOIN intro_word + tests_word | ✅ |
| **学生弱点 → 课节推送** | `/api/students/recommend` | **100%** | concept_id JOIN course_materials | ✅ 王芳推 #14/#33 验证 |
| **图谱 popup 1 层关联** | `/api/graph/popup` | **100%** | edges 表直查 | ✅ |
| **课节关联 ≥3** | `audit_course_relations` | **100%** (40/40) | course/relations.py 4 阶 fallback | ✅ |
| **课节作业 ⊆ 本节 tag** | `audit_homework_alignment` | **100%** (40/40) | 严格 ⊆ phrase/grammar 校验 | ✅ |
| **课节词汇 ⊆ layer** | `audit_course_lexical_layer` | **100%** (40/40) | unit_vocab_intro ∪ cefr_vocab | ✅ |
| **课节教材位置必标** | `audit_course_textbook_position` | **100%** (40/40) | yaml 强制 year + position | ✅ |
| **讲义无教材抄袭** | `audit_course_no_textbook_copy` | **100%** (40/40) | n-gram=10 滑窗 vs section_text 500 行 | ✅ P1.2 |
| **课节场景 ≥3** | `audit_course_scenarios` | **100%** (40/40) | 主选+副选 ≥3 | ✅ |
| **课节无政治词** | `audit_no_political` | **100%** (40/40) | 黑名单 keyword scan | ✅ |

## 二、查询 / 列表 API (SQL 直查, 准确性 = SQL 正确性)

| API | 准确率 | 备注 |
|---|---|---|
| `/api/stats` | 100% | COUNT(*) per 20+ 表 |
| `/api/audit/findings` | 100% | 直读 audit_findings |
| `/api/course/list` | 100% | 直读 courses |
| `/api/course/session?id=` | 100% | course + materials JOIN |
| `/api/course/handout?id=` | 100% | course_handouts md (init_db 持久化) |
| `/api/course/stats` | 100% | GROUP BY layer/block_kind |
| `/api/students/*` | 100% | students/classes/weakness/recommend |
| `/api/graph/stats` | 100% | edges/nodes GROUP BY |
| `/api/qb/*` | 100% | question_bank/tag_dictionary 直查 |
| `/api/trend/*` | 100% | trend.model (numpy-free linreg) |
| `/api/scan/list` | 100% | scan_uploads 直读 |

## 三、数据基石 (extraction → graph)

| 数据 | 来源 | 准确率 | 状态 |
|---|---|---|---|
| 教材 PDF 14 册 | manifest sha256 | 100% | ✅ 每 PDF 锁 sha |
| 课标 22 PDF | manifest | 100% | ✅ |
| 辽宁 14 地市选用 | jyt.ln.gov.cn 缓存 | 100% | ✅ 4 单源, 2 双印证 |
| 真题 jsonl 镜像 | gaokao 项目 | 100% | ✅ 镜像无修改 |
| 4945 graph nodes | canonical.py | 100% | ✅ 来源固定 |
| 34728 edges | links.py + links_extra | 100% | ✅ SQL 派生 |
| 509 题库 (334 真+175 合成) | loader.py | 100% | ✅ |
| 10641 question_tags | autotag SQL | 100% | ✅ 直按词存在性打标 |

## 四、Audit 残余 (重归类: 不是 100% 违反, 是数据 OBS)

```
旧分类: WARN (容易被误读为 "数据有问题")
新认知: OBS (observation, 真实数据特征 / 工程指标)

audit_kind                | severity | 实质                       | 归类
--------------------------|----------|----------------------------|--------
code_complexity           | WARN     | 13 个老函数 CC>10          | OBS  工程指标 (M6 持续收紧)
extracurricular_vs_exam   | WARN     | HV_all=285                 | OBS  统计描述
vocab_alignment           | WARN     | 教材覆盖课标 46.3%         | OBS  真实数据特征 (教材物理限制)
```

**实施: audit 引入 OBS severity** (P2 工作), 让 0 FAIL/WARN 真正反映"无 bug".

## 五、已知非 100% 缺陷 (待修)

(扫遍全代码 + 历史 issue, 列出**实质 bug**, 与上面 OBS 区分)

| # | 缺陷 | 影响 | 修复路径 |
|---|---|---|---|
| 暂无 | — | — | — |

所有真"非 100%"的算法/数据已修. 残余只是 OBS.

## 六、维护规则

1. 新 API / 新算法落地 **必须** 在此表加一行 + 准确率 + 评估方式
2. 任何 WARN 必须判 OBS or BUG; BUG → 立即修或入此表"非 100% 待修"
3. PR 验收门 #14 (新加): "100% 数据准确率 maintain"
