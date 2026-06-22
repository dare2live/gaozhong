"""D0 设问类型 cognitive_skill 金矿校验 (KG层 A1; 坑16/坑17/§7, docs/kg_layer_design §5/§6).

跨era(2026-06-22 v3): 两真值源拼出"考查方式演变"——
  - 2015-20 旧课标全国II: exam_questions refine 后 province 门(坑3 provenance-aware 单点真值), reading 子题前导题型 85 边(六年全覆盖, 两格式抽)。
  - 2021+ 新高考全国II: subquestions jsonl + 真值锚交叉门(2021 经 ≥2 源证实=甲卷 Take a view 已剔§7), 现仅 2023 共 15 边。
锁: 边数==100(85+15) + 源年 ∈ {2015-20, 2023}(无甲卷/无未映射年混入) + 命题迁移真值(推断占比 新era>旧era, 坑16) + explicit_label + 血缘。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B

_DIM = "json_extract_string(evidence_json,'$.dimension')='cognitive_skill'"
_SRC_YEAR = "json_extract_string(evidence_json,'$.lineage.source_year')"
_VALID_YEARS = {"2015", "2016", "2017", "2018", "2019", "2020", "2023"}


def check_cognitive_skill(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (30) 设问类型 cognitive_skill 金矿 (跨era: 旧课标II 2015-20 + 新高考II 2023, 真值锚剔2021甲卷, 坑16/§7) ===")
    n_edge = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM}").fetchone()[0]
    check("cognitive_skill 边 == 100 (跨era: 旧课标II 85 + 新高考II 15)", n_edge == B('cognitive_skill'), f"{n_edge}")

    n_legacy = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND CAST({_SRC_YEAR} AS INT) BETWEEN 2015 AND 2020").fetchone()[0]
    check("2015-20 旧课标全国II reading子题 == 67 (refine省份门, 坑3)", n_legacy == B('cognitive_skill_legacy'), f"{n_legacy}")
    n_new = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND CAST({_SRC_YEAR} AS INT) >= 2021").fetchone()[0]
    check("2021+ 新高考全国II == 15 (真值锚门, 现仅2023)", n_new == B('cognitive_skill_new'), f"{n_new}")

    # §7: 源年只能 ∈ 真值门通过的集合 (2021甲卷已剔; 2022/24/25 无前导题型未抽 → 不应出现)
    bad_years = con.execute(
        f"SELECT DISTINCT {_SRC_YEAR} FROM edges WHERE relation='tests_exam_point' AND {_DIM} "
        f"AND {_SRC_YEAR} NOT IN ({','.join('?' * len(_VALID_YEARS))})",
        sorted(_VALID_YEARS)).fetchall()
    check("无源误标年混入 (源年 ⊆ {2015-20,2023}; 甲卷冒辽宁已剔§7)", not bad_years, f"越界年={[r[0] for r in bad_years]}")

    # 命题哲学迁移真值 (坑16: 新高考重推断): 推断占比 新era > 旧era — 显式标签拼出的"考查方式演变"核心信号
    from backend.services.exam_point import cognitive_skill_distribution
    dist = cognitive_skill_distribution(con)

    def _infer_pct(era_key: str) -> float:
        for era, pts in dist["by_era"].items():
            if era.startswith(era_key):
                return next((p["pct"] for p in pts if p["label"] == "推断"), 0.0)
        return -1.0
    old_pct, new_pct = _infer_pct("2015-2020"), _infer_pct("2021")
    check("命题迁移真值: 推断占比 新高考II > 旧课标II (坑16重推断; 新era n=15方向性诚实标)",
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


_OFFICIAL_SKILLS = {"推断", "理解具体信息", "理解主旨要义", "理解词汇", "理解结构", "理解观点", "理解意图"}


def check_cognitive_cross(con: duckdb.DuckDBPyConnection, check) -> None:
    """设问技能×题材/主题 交叉 view D0 (2015-20截面; 异质provenance分层 + join对齐防回归 + 计数单位)."""
    print("\n=== (31) 设问技能×题材交叉 view (2015-20截面, 技能=真值/题材=模型推断 异质分层) ===")
    from backend.services.exam_point import cognitive_skill_by_content
    g, t = cognitive_skill_by_content(con, "genre"), cognitive_skill_by_content(con, "theme_l2")

    # join 对齐防回归: passage_label 前缀对齐断了 → n_matched 静默掉 0 (违 D0); 锁命中数
    check("技能×题材 join 命中 == 74 ('question:'||passage_label 对齐, 防前缀回归静默漏行)",
          g["n_matched"] == B('cog_cross_genre'), f"{g['n_matched']}")
    check("技能×主题群 join 命中 == 75 (11miss=有theme无genre真缺口)",
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
