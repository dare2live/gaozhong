"""D0 设问类型 cognitive_skill 金矿校验 (KG层 A1; 坑16/坑17/§7, docs/kg_layer_design §5/§6).

跨era(2026-06-22 v3): 两真值源拼出"考查方式演变"——
  - 2015-20 旧课标全国II: exam_questions refine 后 province 门(坑3 provenance-aware 单点真值), reading 子题前导题型 67 边。
  - 2021+ 新高考全国II: subquestions jsonl + 真值锚交叉门(2021 经 ≥2 源证实=甲卷 Take a view 已剔§7), 现仅 2023 共 15 边。
锁: 边数==82(67+15) + 源年 ∈ {2015-20, 2023}(无甲卷/无未映射年混入) + 命题迁移真值(推断占比 新era>旧era, 坑16) + explicit_label + 血缘。
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
    check("cognitive_skill 边 == 82 (跨era: 旧课标II 67 + 新高考II 15)", n_edge == B('cognitive_skill'), f"{n_edge}")

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
