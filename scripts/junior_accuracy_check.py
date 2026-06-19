"""初中子系统 D0 强校验门 (坑17: 新数据必入 D0; 审计 F5 补门).

独立于高中 data_accuracy_check (初中产物在 data/junior_high/structured/*.jsonl, 未入主 DB)。
8 不变量 (审计 F1-F8); 0 错 exit 0。当前多项 RED = Phase2.6 待修真实状态 (TDD 红→逐项绿)。

未接 stop_gate 阻断路径 (达标全绿后才接), 现作独立 TDD harness。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "data" / "junior_high" / "structured"
FAIL = []


def check(name, ok, detail=""):
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}  ({detail})")
    if not ok:
        FAIL.append(name)


def _words(f):
    return [json.loads(l) for l in (S / f).open(encoding="utf-8")] if (S / f).exists() else []


def _whitelist() -> set:
    wl = set()
    for p in ["data/structured/english-wordlists/COCA_20000.txt", "/usr/share/dict/words"]:
        if os.path.exists(p):
            wl |= {l.split(",")[0].split("\t")[0].strip().lower()
                   for l in open(p, encoding="utf-8", errors="ignore") if l.strip()}
    import duckdb
    c = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    wl |= {r[0] for r in c.execute("SELECT word FROM cefr_vocab").fetchall()}
    c.close()
    wl |= {r["word"] for r in _words("hujiao_vocab.jsonl")}
    return wl


def _check_curriculum(cur) -> None:
    l3 = [r for r in cur if r.get("level") == "三级"]
    xiao = [r for r in cur if r.get("stage") == "小学"]
    words = {r["word"] for r in cur}
    garbage = sorted(r["word"] for r in cur if re.fullmatch(r"[a-z]+", r["word"]) and r["word"] not in _whitelist())
    check("F1 无垃圾词头 (curriculum_vocab 词∈白名单)", not garbage, f"{len(garbage)} 疑垃圾: {garbage[:8]}")
    check("F2 三级抽取数透明 (extracted, 不凑1600)", len(l3) >= 1500, f"三级={len(l3)} (官方≈1600)")
    check("F2b 已知丢词缺口记录 (goal 等)", "goal" in words, f"goal 在={'goal' in words} (False=待OCR恢复)")
    check("F7 二级(小学)=505", len(xiao) == 505, f"{len(xiao)} (差 {505 - len(xiao)})")


def _check_hujiao(hj) -> None:
    cid = [r for r in hj if "(cid:" in r.get("zh_def", "")]
    check("F4 沪教无未标 cid 乱码释义", not cid, f"{len(cid)} 条含(cid:未标待OCR")
    n_hj = len({r["word"] for r in hj})
    check("F5 沪教词量护栏 (800-1400)", 800 <= n_hj <= 1400, f"{n_hj}")


def main() -> int:
    print("=== 初中子系统 D0 校验 (坑17 补门, 审计 F1-F8) ===")
    cur, hj = _words("curriculum_vocab.jsonl"), _words("hujiao_vocab.jsonl")
    _check_curriculum(cur)
    _check_hujiao(hj)
    check("F6 语法项目=71 (含5理解项)", len(_words("grammar_items.jsonl")) == 71,
          f"{len(_words('grammar_items.jsonl'))}")
    cur_words = {r["word"] for r in cur} | {r["word"] for r in hj}
    orphan = [r for r in _words("stage_refined.jsonl")
              if r.get("refined_stage") in ("小学", "初中") and r["word"] not in cur_words]
    check("F8 stage_refined 无 orphan (初中依据存在)", not orphan, f"{len(orphan)} orphan")
    pa = (ROOT / "backend/config/project_architecture.yaml").read_text(encoding="utf-8")
    check("契约 junior 子系统已注册 project_architecture.yaml", "junior_high" in pa,
          "registered" if "junior_high" in pa else "未注册")
    print(f"\n{'✅ 初中 D0 全绿' if not FAIL else f'❌ {len(FAIL)} RED (Phase2.6 待修): ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
