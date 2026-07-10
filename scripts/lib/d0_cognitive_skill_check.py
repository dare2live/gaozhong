"""D0 设问类型 cognitive_skill 金矿校验 (KG层 A1; 坑16/坑17/§7, docs/kg_layer_design §5/§6).

跨era(2026-07-03 v4): 两真值源拼出"考查方式演变"——
  - 2015-20 旧课标全国II: exam_questions refine 后 province 门(坑3 provenance-aware 单点真值), reading 子题前导题型 86 边(六年全覆盖, 两格式抽)。
  - 2021+ 新高考全国II: subquestions jsonl + 真值锚交叉门(2021 经 ≥2 源证实=甲卷 Take a view 已剔§7), 现 2023(15) + 2024(14) 共 29 边。
锁: 边数==115(86+29) + 源年 ∈ {2015-20, 2023, 2024}(无甲卷/无未映射年混入) + 命题迁移真值(推断占比 新era>旧era, 坑16) + explicit_label + 血缘。
2022/2025/2026 仍无本地/免费可核验的逐题教研解析(2026-07-03 系统性网络检索 ~15 次尝试确认: zhihu 403 封锁 +
学科网/组卷网付费墙 + 新闻站宏观评析非逐题) — 诚实标未补, 非代码/流程缺陷, 待有偿源或未来免费源出现。

2026-07-06 v5(方法论调研+对抗核查): (a) 发现并清理2024阅读理解15条重复行(GAOKAO-Bench-Updates
原始导入的空analysis旧行, 与07-03已补的带analysis新行是同一批真实子题的重复条目, 删除空的旧行,
数值上不影响本check——旧行analysis为空本就被_skill_of跳过, 纯数据卫生, 非D0数值变更);
(b) 首次填充"理解目的"官方桶(此前0数据覆盖): exam_point_taxonomy.yaml补"写作意图题"(legacy 2017
q27)+"目的意图题"(subq 2024 EN-XGKII-2024-078)→理解目的, 均只1条真实样本(诚实标注小样本, 见
kg_layer_design.md)。legacy 85→86, new 28→29, 总数113→115。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B

_DIM = "json_extract_string(evidence_json,'$.dimension')='cognitive_skill'"
_SRC_YEAR = "json_extract_string(evidence_json,'$.lineage.source_year')"
_VALID_YEARS = {"2015", "2016", "2017", "2018", "2019", "2020", "2023", "2024"}


def check_cognitive_skill(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (30) 设问类型 cognitive_skill 金矿 (跨era: 旧课标II 2015-20 + 新高考II 2023/2024, 真值锚剔2021甲卷, 坑16/§7) ===")
    n_edge = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM}").fetchone()[0]
    check("cognitive_skill 边 == 115 (跨era: 旧课标II 86 + 新高考II 29)", n_edge == B('cognitive_skill'), f"{n_edge}")

    # 此处 2015/2020/2021 是**独立验证断言**(verify-the-verifier, 坑1): 故意 NOT 从 scope.py 取,
    # 否则流水线边界常量漂移时验证器随之移动 → 绿门假绿。验证器须独立钉死预期年段才能抓住漂移。
    n_legacy = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND CAST({_SRC_YEAR} AS INT) BETWEEN 2015 AND 2020").fetchone()[0]
    check("2015-20 旧课标全国II reading子题 == 86 (refine省份门, 坑3)", n_legacy == B('cognitive_skill_legacy'), f"{n_legacy}")
    n_new = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND CAST({_SRC_YEAR} AS INT) >= 2021").fetchone()[0]
    check("2021+ 新高考全国II == 29 (真值锚门, 2023+2024)", n_new == B('cognitive_skill_new'), f"{n_new}")

    # §7: 源年只能 ∈ 真值门通过的集合 (2021甲卷已剔; 2022/25/26 无前导题型未抽 → 不应出现)
    bad_years = con.execute(
        f"SELECT DISTINCT {_SRC_YEAR} FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND {_SRC_YEAR} NOT IN ({','.join('?' * len(_VALID_YEARS))})",
        sorted(_VALID_YEARS)).fetchall()
    check("无源误标年混入 (源年 ⊆ {2015-20,2023,2024}; 甲卷冒辽宁已剔§7)", not bad_years, f"越界年={[r[0] for r in bad_years]}")

    # 命题哲学迁移真值 (坑16: 新高考重推断): 推断占比 新era > 旧era — 显式标签拼出的"考查方式演变"核心信号
    from backend.services.exam_point import cognitive_skill_distribution
    dist = cognitive_skill_distribution(con)

    def _infer_pct(era_key: str) -> float:
        for era, pts in dist["by_era"].items():
            if era.startswith(era_key):
                return next((p["pct"] for p in pts if p["label"] == "推断"), 0.0)
        return -1.0
    old_pct, new_pct = _infer_pct("2015-2020"), _infer_pct("2021")
    check("命题迁移真值: 推断占比 新高考II > 旧课标II (坑16重推断; 新era n=28方向性诚实标)",
          new_pct > old_pct > 0, f"旧{old_pct}% → 新{new_pct}%")

    bad_prov = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        "AND json_extract_string(evidence_json,'$.provenance')<>'explicit_label'").fetchone()[0]
    check("cognitive_skill 全 explicit_label (教研显式标签非inference)", bad_prov == 0, f"{bad_prov}")

    bad_lin = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND ("
        "json_extract_string(evidence_json,'$.lineage.version_ids.exam_paper') IS NULL "
        f"OR {_SRC_YEAR} IS NULL)").fetchone()[0]
    check("cognitive_skill 边全带血缘 (version_ids.exam_paper + source_year)", bad_lin == 0, f"{bad_lin} 缺血缘")

    # G4: _SKILL_MAP 收口 exam_point_taxonomy.yaml 单点 — 锁 yaml 题型→技能映射不漂出官方7。
    # verify-the-verifier: _OFFICIAL_SKILLS 是本 check 独立字面量(非从 yaml 取), 抓"yaml alias 改成非官方 label
    # (重建后技能分布错但边数仍 85)"这类 gate 时即可见的源漂移 (坑16: dual-model 一致≠对, 映射须钉官方真相源)。
    from backend.services.exam_point.cognitive_skill import _load_skill_map
    smap = _load_skill_map()
    bad_tgt = sorted({t for t in smap.values() if t not in _OFFICIAL_SKILLS})
    check("_SKILL_MAP yaml单点 (G4): ≥9条 + target ⊆ 官方7理解性技能 (坑16防非官方漂移)",
          len(smap) >= 9 and not bad_tgt, f"n={len(smap)} 越界={bad_tgt}")


"""坑(2026-07-04 全数据审计): 独立字面量本身抄错了3处(与 exam_point_taxonomy.yaml
question_intent.labels 官方7项字面对比: 理解观点态度→曾抄'理解观点', 理解目的→曾抄'理解意图',
理解文章结构类型→曾抄'理解结构'). 当前 DB 内 cognitive_skill 边实际只用到4个双方拼写一致的
标签(理解具体信息/理解主旨要义/推断/理解词汇)故未曾触发可见故障, 但属于"抄错的独立副本"
真bug非设计问题——verify-the-verifier 精神(不从 yaml 读取, 见上方注释)继续保留, 只订正字面量。"""
_OFFICIAL_SKILLS = {"推断", "理解具体信息", "理解主旨要义", "理解词汇",
                    "理解文章结构类型", "理解观点态度", "理解目的"}


def check_cognitive_cross(con: duckdb.DuckDBPyConnection, check) -> None:
    """设问技能×题材/主题 交叉 view D0 (2015-20截面; 异质provenance分层 + join对齐防回归 + 计数单位)."""
    print("\n=== (31) 设问技能×题材交叉 view (2015-20截面, 技能=真值/题材=模型推断 异质分层) ===")
    from backend.services.exam_point import cognitive_skill_by_content
    g, t = cognitive_skill_by_content(con, "genre"), cognitive_skill_by_content(con, "theme_l2")

    # join 对齐防回归: passage_label 前缀对齐断了 → n_matched 静默掉 0 (违 D0); 锁命中数
    check("技能×题材 join 命中 == 79 ('question:'||passage_label 对齐, 防前缀回归静默漏行)",
          g["n_matched"] == B('cog_cross_genre'), f"{g['n_matched']}")
    check("技能×主题群 join 命中 == 76 (11miss=有theme无genre真缺口)",
          t["n_matched"] == B('cog_cross_theme_l2'), f"{t['n_matched']}")

    # era 锁死 (2021+ 桥缺失, 不可跨era泄漏)
    check("交叉 view era 锁 2015-2020 (2021+桥缺失不出迁移, 坑3)", g["era"] == "2015-2020_旧课标II", g["era"])

    # 异质 provenance 诚实分层: 技能侧真值 / 题材侧模型推断 — 防把模型推断冒充真值交叉 (坑16)
    ok_prov = "explicit_label" in g["skill_provenance"] and "dual_model_agree" in g["content_provenance"]
    check("异质provenance分层标注 (技能=explicit_label真值 / 题材=dual_model_agree模型推断, 非真值交叉)",
          ok_prov, f"skill={g['skill_provenance'][:20]} content={g['content_provenance'][:20]}")

    # 计数单位诚实: 0<n_matched<=n_subq_total (子题数, 无 fan-out 膨胀超总数, 坑12)
    check("计数单位=子题数, 0<命中<=总数(无膨胀, 坑12)", 0 < g["n_matched"] <= g["n_subq_total"],
          f"{g['n_matched']}/{g['n_subq_total']}")

    # 每格内部自洽 + 无臆造技能泄漏 (skill ∈ 官方7理解性技能)
    bad = [(c, s["label"]) for d in (g, t) for c, cell in d["by_content"].items()
           for s in cell["skills"] if s["label"] not in _OFFICIAL_SKILLS]
    check("交叉格技能 ∈ 官方7理解性技能 (无臆造类目泄漏)", not bad, f"越界={bad[:3]}")
    bad_sum = [c for d in (g, t) for c, cell in d["by_content"].items()
               if sum(s["n"] for s in cell["skills"]) != cell["total"]]
    check("每题材格 total == 各技能 n 之和 (内部自洽)", not bad_sum, f"不自洽={bad_sum[:3]}")


def check_joint_attribution(con: duckdb.DuckDBPyConnection, check) -> None:
    """语篇级联合归因 D0 (2026-07-06 方法论落地; backend/services/exam_point/attribution.py).

    颗粒度边界锁: 只做语篇级(passage), 不假装子题级(词汇边挂语篇/设问思维边挂子题, 见模块docstring)。
    语法维度已实测排除(tests_grammar/cognitive_skill question_type不相交), 锁"确实不返回该字段"防回归。
    """
    print("\n=== (32) 语篇级联合归因 (词汇学段×设问思维, 2015-20截面, KG-A1衍生) ===")
    from backend.services.exam_point import joint_attribution_by_passage
    d = joint_attribution_by_passage(con)

    check("联合归因语篇数 == 24 (cognitive_skill覆盖语篇∩tests_word覆盖语篇)",
          d["n_passages"] == B('joint_attribution_passages'), f"{d['n_passages']}")
    check("era 锁 2015-2020 (2021+ passage_label非全局唯一, 无法桥接tests_word, 已实测)",
          d["era"] == "2015-2020_旧课标II", d["era"])
    check("语法维度已诚实排除 (excluded_dimension_note存在, 不返回必空的grammar_cefr_mix字段)",
          "excluded_dimension_note" in d and "grammar_cefr_mix" not in str(d["passages"][:1]),
          f"note={'excluded_dimension_note' in d}")

    # 每篇 word_stage_mix 内部自洽: foundation+senior+unclassified ≈ 100% (四舍五入容差0.2)
    bad_pct = [p["passage_id"] for p in d["passages"] if p["word_stage_mix"] and
               abs(p["word_stage_mix"]["foundation_pct"] + p["word_stage_mix"]["senior_pct"]
                   + p["word_stage_mix"]["unclassified_pct"] - 100.0) > 0.2]
    check("每篇 foundation+senior+unclassified ≈ 100% (内部自洽)", not bad_pct, f"不自洽={bad_pct[:3]}")

    # 无臆造技能泄漏 (skill ∈ 官方7理解性技能, 同 check_cognitive_cross 复用同一独立字面量)
    bad_skill = [(p["passage_id"], s) for p in d["passages"] for s in p["skill_dist"]
                 if s not in _OFFICIAL_SKILLS]
    check("联合归因技能 ∈ 官方7理解性技能 (无臆造类目泄漏)", not bad_skill, f"越界={bad_skill[:3]}")

    # 每篇 skill_dist 之和 == n_subq (计数单位诚实, 坑12)
    bad_n = [p["passage_id"] for p in d["passages"] if sum(p["skill_dist"].values()) != p["n_subq"]]
    check("每篇 n_subq == skill_dist 之和 (计数单位自洽)", not bad_n, f"不自洽={bad_n[:3]}")


def check_cloze_answer_word_stage(con: duckdb.DuckDBPyConnection, check) -> None:
    """完形填空得分点词学段分布 D0 (2026-07-07; backend/services/exam_point/attribution.py)。

    范围锁: 10 篇"选项文本完整内联"完形填空(eol/2021,2022/xgkii 结构性排除, 见模块 docstring),
    分 era 不跨 era 合并(坑12 分层不取平均)。
    """
    print("\n=== (33) 完形填空得分点词学段分布 (对比全篇基线, 2026-07-07) ===")
    from backend.services.exam_point.attribution import cloze_answer_word_stage
    d = cloze_answer_word_stage(con)

    check("得分点分析篇数 == 10 (2015-2020旧课标II 6 + 2023-2026新高考II 4)",
          d["n_passages"] == B('cloze_answer_word_passages'), f"{d['n_passages']}")
    check("排除说明字段存在 (eol/2021,2022诚实排除, 非静默丢弃)",
          "excluded_source_note" in d and "eol" in d["excluded_source_note"], "")
    check("era 集合 ⊆ {2015-2020旧课标II, 2021+新高考II} (无臆造 era 泄漏)",
          set(d["by_era"]) <= {"2015-2020_旧课标II", "2021+_新高考II"}, f"{sorted(d['by_era'])}")

    bad = [era for era, cell in d["by_era"].items()
           if cell["n_blanks_classified"] > cell["n_blanks_total"]]
    check("各 era 已分类空数 ≤ 总空数 (计数自洽)", not bad, f"不自洽={bad}")

    bad_pct = [era for era, cell in d["by_era"].items()
               if cell["answer_word_senior_pct"] is not None and
               abs(cell["answer_word_senior_pct"] + cell["answer_word_foundation_pct"] - 100.0) > 0.2]
    check("各 era senior_pct+foundation_pct ≈ 100% (内部自洽)", not bad_pct, f"不自洽={bad_pct}")
