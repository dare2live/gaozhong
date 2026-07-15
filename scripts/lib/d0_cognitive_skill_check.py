"""D0 设问类型 cognitive_skill 金矿校验 (KG层 A1; 坑16/坑17/§7, docs/kg_layer_design §5/§6).

跨era:
  - 2015-20: 阅读四选一 86 + 七选五结构 30 = 116
  - 2021+: 阅读四选一 74(剔甲卷) + 七选五结构 30(含2021真xgkii) = 104
  合计 220。
锁: 边数 + 源年 + 推断迁移(仅四选一口径, 不含七选五结构空) + provenance 三档 + 血缘 + 态度5/结构60。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B

_DIM = "json_extract_string(evidence_json,'$.dimension')='cognitive_skill'"
_SRC_YEAR = "json_extract_string(evidence_json,'$.lineage.source_year')"
_GAOKAO = "COALESCE(json_extract_string(evidence_json,'$.exam_stage'),'gaokao')='gaokao'"
# 2021: 阅读四选一 subq 甲卷已剔; 七选五 eol/xgkii 为真新高考II, 允许入源年
_VALID_YEARS = {"2015", "2016", "2017", "2018", "2019", "2020", "2021",
                "2022", "2023", "2024", "2025", "2026"}
_OK_PROV = ("explicit_label", "curriculum_aligned_stem", "curriculum_aligned_task")


def check_cognitive_skill(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (30) 设问类型 cognitive_skill 金矿 (高考四选一+七选五; 中考另计) ===")
    n_edge = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO}"
    ).fetchone()[0]
    check("高考 cognitive_skill 边 == 220 (四选一160 + 七选五60)", n_edge == B('cognitive_skill'), f"{n_edge}")

    n_legacy = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} "
        f"AND CAST({_SRC_YEAR} AS INT) BETWEEN 2015 AND 2020").fetchone()[0]
    check("高考2015-20 == 116 (四选一86 + 七选五30)", n_legacy == B('cognitive_skill_legacy'), f"{n_legacy}")
    n_new = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} "
        f"AND CAST({_SRC_YEAR} AS INT) >= 2021").fetchone()[0]
    check("高考2021+ == 104 (四选一74 + 七选五30)", n_new == B('cognitive_skill_new'), f"{n_new}")

    bad_years = con.execute(
        f"SELECT DISTINCT {_SRC_YEAR} FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} "
        f"AND {_SRC_YEAR} NOT IN ({','.join('?' * len(_VALID_YEARS))})",
        sorted(_VALID_YEARS)).fetchall()
    check("高考无源误标年混入 (源年 ⊆ 2015-2026; 甲卷阅读已剔§7)", not bad_years,
          f"越界年={[r[0] for r in bad_years]}")

    # 命题迁移: 仅四选一口径(排除七选五 task), 避免结构空稀释考查方式信号
    from backend.services.exam_point import cognitive_skill_distribution
    dist = cognitive_skill_distribution(con)

    def _infer_pct_mcq(era_prefix: str) -> float:
        """推断占比 — 分母不含理解文章结构类型(七选五)。"""
        for era, pts in dist["by_era"].items():
            if not era.startswith(era_prefix):
                continue
            mcq = [p for p in pts if p["label"] != "理解文章结构类型"]
            tot = sum(p["n"] for p in mcq)
            if tot <= 0:
                return -1.0
            return next((100 * p["n"] / tot for p in mcq if p["label"] == "推断"), 0.0)
        return -1.0
    old_pct, new_pct = _infer_pct_mcq("2015-2020"), _infer_pct_mcq("2021")
    check("命题迁移真值: 四选一推断占比 新高考II > 旧课标II (不含七选五)",
          new_pct > old_pct > 0, f"旧{old_pct:.1f}% → 新{new_pct:.1f}%")

    bad_prov = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND json_extract_string(evidence_json,'$.provenance') NOT IN ({','.join('?'*len(_OK_PROV))})",
        list(_OK_PROV)).fetchone()[0]
    check("cognitive_skill provenance ∈ {explicit_label, curriculum_aligned_stem, curriculum_aligned_task}",
          bad_prov == 0, f"{bad_prov}")
    n_cur = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} "
        "AND json_extract_string(evidence_json,'$.provenance')='curriculum_aligned_stem'"
    ).fetchone()[0]
    check("高考课标题干纠正边 == 5 (态度桶 curated)", n_cur == 5, f"{n_cur}")
    n_task = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} "
        "AND json_extract_string(evidence_json,'$.provenance')='curriculum_aligned_task'"
    ).fetchone()[0]
    check("高考七选五 task 边 == 60 (结构桶)", n_task == 60, f"{n_task}")
    n_att = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN nodes n ON n.concept_id=e.dst_id "
        f"WHERE e.relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} AND n.label='理解观点态度'"
    ).fetchone()[0]
    check("高考理解观点态度桶 == 5", n_att == 5, f"{n_att}")
    n_struct = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN nodes n ON n.concept_id=e.dst_id "
        f"WHERE e.relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} AND n.label='理解文章结构类型'"
    ).fetchone()[0]
    check("高考理解文章结构类型桶 == 60 (七选五每空1边)", n_struct == 60, f"{n_struct}")
    miss = dist.get("missing_categories") or []
    check("官方7技能 missing_categories 为空", miss == [], f"{miss}")

    # L2 subtype: 全覆盖 (analysis→curated→discourse→fallback句际衔接); unknown 必须为 0
    from backend.services.exam_point.cognitive_seven_choose_five import structure_subtype_distribution
    sub = structure_subtype_distribution(con, "gaokao")
    check("高考结构 L2 边 == 60", sub["n_total"] == 60, f"{sub['n_total']}")
    check("高考结构 L2 unknown == 0 (全覆盖, 不留空)", sub["unknown_n"] == 0,
          f"unknown={sub['unknown_n']} by={sub['by_subtype']}")
    bad_sub = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND {_GAOKAO} "
        "AND json_extract_string(evidence_json,'$.provenance')='curriculum_aligned_task' "
        "AND (json_extract_string(evidence_json,'$.subtype') IS NULL "
        "OR json_extract_string(evidence_json,'$.subtype')='' "
        "OR json_extract_string(evidence_json,'$.subtype')='unknown')"
    ).fetchone()[0]
    check("高考结构边全带非 unknown subtype", bad_sub == 0, f"{bad_sub}")

    sub_zk = structure_subtype_distribution(con, "zhongkao")
    check("中考结构 L2 边 ≥ 8", sub_zk["n_total"] >= 8, f"{sub_zk['n_total']}")
    check("中考结构 L2 unknown == 0", sub_zk["unknown_n"] == 0,
          f"unknown={sub_zk['unknown_n']} by={sub_zk['by_subtype']}")

    n_jr = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        "AND json_extract_string(evidence_json,'$.exam_stage')='zhongkao'"
    ).fetchone()[0]
    check("中考 cognitive_skill 边 ≥ 8 (五选四结构; 另含题干对齐阅读)", n_jr >= 8, f"{n_jr}")

    bad_lin = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} AND ("
        "json_extract_string(evidence_json,'$.lineage.version_ids.exam_paper') IS NULL "
        f"OR {_SRC_YEAR} IS NULL)").fetchone()[0]
    check("cognitive_skill 边全带血缘 (version_ids.exam_paper + source_year)", bad_lin == 0, f"{bad_lin} 缺血缘")

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

    check("技能×题材 join 命中 == 79 ('question:'||passage_label 对齐, 防前缀回归静默漏行)",
          g["n_matched"] == B('cog_cross_genre'), f"{g['n_matched']}")
    check("技能×主题群 join 命中 == 76 (11miss=有theme无genre真缺口)",
          t["n_matched"] == B('cog_cross_theme_l2'), f"{t['n_matched']}")

    check("交叉 view era 锁 2015-2020 (2021+桥缺失不出迁移, 坑3)", g["era"] == "2015-2020_旧课标II", g["era"])

    ok_prov = (("explicit_label" in g["skill_provenance"] or "curriculum_aligned" in g["skill_provenance"])
               and "dual_model_agree" in g["content_provenance"])
    check("异质provenance分层标注 (技能=真值/课标对齐 / 题材=dual_model_agree模型推断)",
          ok_prov, f"skill={g['skill_provenance'][:40]} content={g['content_provenance'][:20]}")

    check("计数单位=子题数, 0<命中<=总数(无膨胀, 坑12)", 0 < g["n_matched"] <= g["n_subq_total"],
          f"{g['n_matched']}/{g['n_subq_total']}")

    bad = [(c, s["label"]) for d in (g, t) for c, cell in d["by_content"].items()
           for s in cell["skills"] if s["label"] not in _OFFICIAL_SKILLS]
    check("交叉格技能 ∈ 官方7理解性技能 (无臆造类目泄漏)", not bad, f"越界={bad[:3]}")
    bad_sum = [c for d in (g, t) for c, cell in d["by_content"].items()
               if sum(s["n"] for s in cell["skills"]) != cell["total"]]
    check("每题材格 total == 各技能 n 之和 (内部自洽)", not bad_sum, f"不自洽={bad_sum[:3]}")


def check_joint_attribution(con: duckdb.DuckDBPyConnection, check) -> None:
    """语篇级联合归因 D0 (2026-07-06 方法论落地; backend/services/exam_point/attribution.py)."""
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

    bad_pct = [p["passage_id"] for p in d["passages"] if p["word_stage_mix"] and
               abs(p["word_stage_mix"]["foundation_pct"] + p["word_stage_mix"]["senior_pct"]
                   + p["word_stage_mix"]["unclassified_pct"] - 100.0) > 0.2]
    check("每篇 foundation+senior+unclassified ≈ 100% (内部自洽)", not bad_pct, f"不自洽={bad_pct[:3]}")

    bad_skill = [(p["passage_id"], s) for p in d["passages"] for s in p["skill_dist"]
                 if s not in _OFFICIAL_SKILLS]
    check("联合归因技能 ∈ 官方7理解性技能 (无臆造类目泄漏)", not bad_skill, f"越界={bad_skill[:3]}")

    bad_n = [p["passage_id"] for p in d["passages"] if sum(p["skill_dist"].values()) != p["n_subq"]]
    check("每篇 n_subq == skill_dist 之和 (计数单位自洽)", not bad_n, f"不自洽={bad_n[:3]}")


def check_cloze_answer_word_stage(con: duckdb.DuckDBPyConnection, check) -> None:
    """完形填空得分点词学段分布 D0 (2026-07-07; backend/services/exam_point/attribution.py)。"""
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
