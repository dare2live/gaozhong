"""D0 跨年级分阶 correctness (B轨; 坑1 未断言维度永远绿 / 坑2 防 loader 回退).

verify-the-verifier 结论 (2026-06-20): at_stage **边**早已是细分阶(stage_backfill 读 refined_stage),
node attrs.stage 仍粗是 word 多义项跨阶段(master A1 word_sense, 大改延后), 几乎无消费方。
红队"DB粗分阶红线"是误读 — 真跨年级消费(k12.stage_distribution)只读 at_stage 边, 已细已对。
本门锁: 每个 refined 真阶段词的 at_stage 边精确指向 stage:{refined_stage} (0 错指/0 缺边),
防 stage_backfill 回退或 stage_refined.jsonl 漂移而门不知 (此前仅有 at_stage≥2000 计数门, 坑1 不测 correctness)。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

_ROOT = Path(__file__).resolve().parents[2]
_REFINED = _ROOT / "data" / "junior_high" / "structured" / "stage_refined.jsonl"
_REAL_STAGES = {"小学", "初中", "义务教育", "高中必修", "高中选修"}


def check_stage(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (31) 跨年级分阶 correctness (at_stage 边 == refined_stage, B轨) ===")
    if not _REFINED.exists():
        check("stage_refined.jsonl 存在", False, "缺失")
        return
    rs = {json.loads(l)["word"]: json.loads(l)["refined_stage"]
          for l in _REFINED.read_text(encoding="utf-8").splitlines() if l.strip()}
    real = {w: st for w, st in rs.items() if st in _REAL_STAGES}
    mismatch = missing = 0
    for w, st in real.items():
        dsts = {r[0] for r in con.execute(
            "SELECT dst_id FROM edges WHERE relation='at_stage' AND src_id=?", [f"word:{w}"]).fetchall()}
        if not dsts:
            missing += 1
        elif f"stage:{st}" not in dsts:
            mismatch += 1
    check("refined 真阶段词全有 at_stage 边 (无缺边)", missing == 0, f"{missing} 缺边")
    check("at_stage 边精确指向 refined_stage (无错指; 细分阶 correctness 非仅计数, 坑1)",
          mismatch == 0, f"{mismatch} 错指")
    check("覆盖 ≥3000 refined 真阶段词 (小学/初中细分非粗义务教育)", len(real) >= 3000, f"{len(real)}")


def check_tested_word_stage(con: duckdb.DuckDBPyConnection, check) -> None:
    """考查词学段分布 (k12.tested_word_stage_distribution) — "最少覆盖最大" 实证的 D0 锁.

    跨源核验 (非同源重言, 根因D): service 输出 vs 独立 SQL 直接从边重算; 防口径漂移
    (如丢 province 过滤 / at_stage join 断→全未分类 / 学段标签污染) 而门不知。
    """
    print("\n=== (32) 辽宁高考考查词 学段分布 correctness (k12.tested_word_stage_distribution) ===")
    from backend.services.exam_vocab import TESTED_QTYPES
    from backend.services import k12
    d = k12.tested_word_stage_distribution(con)
    # 独立重算 distinct 辽宁离散考查词 (不经 service, 跨源)
    qmarks = ",".join("?" * len(TESTED_QTYPES))
    indep = con.execute(
        "SELECT COUNT(DISTINCT SUBSTR(e.dst_id,6)) FROM edges e "
        "JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        f"WHERE e.relation='tests_word' AND q.province LIKE '辽宁%' AND q.question_type IN ({qmarks})",
        list(TESTED_QTYPES)).fetchone()[0]
    check("total == 独立SQL重算的辽宁离散考查词数 (as-served==源, 非同源重言)", d["total"] == indep, f"service={d['total']} sql={indep}")
    check("各学段 n 求和 == total (无词被丢)", sum(s["n"] for s in d["stages"]) == d["total"], "sum≠total")
    pct_sum = round(d["foundation_pct"] + d["senior_pct"] + d["unclassified_pct"], 0)
    check("foundation+senior+未分类 pct ≈ 100 (口径完整)", abs(pct_sum - 100) <= 1, f"{pct_sum}%")
    valid = {"小学", "初中", "义务教育", "高中必修", "高中选修", "未分类"}
    check("学段标签全合法 (无污染; 按 raw_stage 原始档)", all(s.get("raw_stage", s["stage"]) in valid for s in d["stages"]), "有非法标签")
    check("未分类率 <30% (at_stage join 未断; 断则全未分类→catch)", d["unclassified_pct"] < 30, f"{d['unclassified_pct']}%")
