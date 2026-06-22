"""D0 趋势/考点分布/关联性 数值正确性校验 (件3 — 对 service 输出断言, 不落表).

把 D0 100% 从"边存在性"扩到"派生数值正确性": 分布占比/计数/era分类/样本诚实/共现守门。
对 service 输出 (exam_point_distribution / exam_point_cooccurrence / scope.diagnose) 断言不变量,
**不重算** (单一计算点: service 是唯一计算点, D0 只验它的输出)。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import duckdb

from backend.services.exam_point import exam_point_cooccurrence, exam_point_distribution
from backend.services.exam_point.cooccur import _axis
from backend.services.trend import scope
from backend.services.trend.raw import question_type_era_presence

# v2 题型 presence 掩码期望 (卷面结构真相源 exam_structure_eras.yaml 驱动; 防 config 漂移误标):
# (signal, extraction_gap) — 听力≠登场(skeleton+缺源); 短改=真退场; 续写/应用文=真登场(但登场年缺源)。
_QT_EXPECT = {
    "短文改错": ("retired", False), "听力": ("skeleton", True),
    "续写": ("introduced", True), "应用文写作": ("introduced", True),
    "阅读理解": ("skeleton", False), "语法填空": ("skeleton", False),
}


def _check_pct_sums(dist: dict, check) -> None:
    bad = []
    for era, dims in dist.items():
        for dim, rows in dims.items():
            s = sum(r["pct"] for r in rows)
            if not (99.0 <= s <= 101.0):
                bad.append(f"{era}/{dim}={s}")
    check("分布占比每(era,dim)和≈100", not bad, f"{bad}")


def _check_count_total(con, dist: dict, check) -> None:
    dist_n = sum(r["n"] for dims in dist.values() for rows in dims.values() for r in rows)
    edge_n = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN exam_questions q "
        "ON ('question:'||q.question_id)=e.src_id AND q.province LIKE '辽宁%' "
        "WHERE e.relation='tests_exam_point'").fetchone()[0]
    check("分布计数总和=辽宁考点边数", dist_n == edge_n, f"dist={dist_n} edge={edge_n}")


def _check_era_labels(dist: dict, check) -> None:
    bad = [e for e in dist if e not in (scope.ERA_NEW, scope.ERA_OLD)]
    check("era 分类=scope单点两卷制(无杂era)", not bad, f"{bad}")


def _check_sample_honesty(diag: dict, check) -> None:
    # 分布够格(核心竞争力可报) + 无伪造 trend_eligible (谄媚死防线)
    fake = [seg for seg, d in diag["by_segment"].items()
            if d["trend_eligible"] and len(d["adequate_years"]) < scope.MIN_TREND_YEARS]
    check("辽宁分布样本够格(可报占比)", diag["distribution_reliable"],
          f"distribution_reliable={diag['distribution_reliable']}")  # 动态反映真值, 不写死 False (防绿门自欺)
    check("无伪造逐年趋势可信度(谄媚死防线)", not fake, f"{fake}")


def _check_cooccur_guard(co: dict, check) -> None:
    bad = []
    for era, slot in co["by_era"].items():
        for p in slot["pairs"]:
            if p["co_n"] < co["min_co"] or _axis(p["a_dim"]) == _axis(p["b_dim"]):
                bad.append(f"{era}:{p['a_label']}⨯{p['b_label']}")
    check("共现对守门(co_n≥阈+跨轴)", not bad, f"{bad[:5]}")


def _check_qtype_structure(con, check) -> None:
    """v2 题型 presence 掩码: signal 由卷面结构config定(非数据presence) + extraction_gap 诚实标 (坑12)."""
    by_qt = {x["question_type"]: x for x in question_type_era_presence(con)["by_question_type"]}
    bad = []
    for qt, (sig, gap) in _QT_EXPECT.items():
        x = by_qt.get(qt)
        if not x or x["signal"] != sig or x["extraction_gap"] != gap:
            got = f"{x['signal']}/gap={x['extraction_gap']}" if x else "缺"
            bad.append(f"{qt}:期望{sig}/gap={gap}得{got}")
    check("题型presence signal=卷面结构真值(听力≠登场=skeleton缺源/短改真退场/续写应用文真登场缺源)", not bad, f"{bad}")
    # 无 unregistered (数据每题型都在 config 卷面结构登记; 漏登记=诚实暴露但也表 config 不全)
    unreg = [x["question_type"] for x in question_type_era_presence(con)["by_question_type"]
             if x["signal"] == "unregistered"]
    check("无未登记题型(数据题型全在卷面结构config; 防漏登记卷改)", not unreg, f"未登记={unreg}")


def check_trend_distribution(con: duckdb.DuckDBPyConnection, check) -> None:
    """分布 pct/计数 + era 分类 + 样本诚实 + 共现守门 + 题型结构掩码 6 项 D0 数值校验 (件3 + v2)."""
    print("\n=== (23) 趋势/考点分布/关联性 数值正确性 (件3, 对 service 输出断言) ===")
    dist = exam_point_distribution(con)
    _check_pct_sums(dist, check)
    _check_count_total(con, dist, check)
    _check_era_labels(dist, check)
    _check_sample_honesty(scope.diagnose(con), check)
    _check_cooccur_guard(exam_point_cooccurrence(con), check)
    _check_qtype_structure(con, check)
