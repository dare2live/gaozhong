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
