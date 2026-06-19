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
EXAMS = ROOT / "data" / "junior_high" / "exams"
FAIL = []


def _qtype_expect(n: int) -> str:
    """中考题型分段不变量 (与 extract_zhongkao._qtype 同口径; D0 单一真相)."""
    if 1 <= n <= 16:
        return "阅读理解(四选一)"
    if 17 <= n <= 20:
        return "阅读理解(五选四/选句填空)"
    if 21 <= n <= 30:
        return "完形填空"
    if 31 <= n <= 40:
        return "语篇填空(语法填空)"
    if 41 <= n <= 44:
        return "阅读与表达(开放问答)"
    return "书面表达(应用文)"


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
    ocr = S / "_ocr_curriculum_words.txt"   # OCR 视觉确认 = 真词 (app/organise 等)
    if ocr.exists():
        wl |= {l.strip().lower() for l in ocr.read_text(encoding="utf-8").splitlines() if l.strip()}
    return wl


def _check_curriculum(cur) -> None:
    l3 = [r for r in cur if r.get("level") == "三级"]
    xiao = [r for r in cur if r.get("stage") == "小学"]
    words = {r["word"] for r in cur}
    garbage = sorted(r["word"] for r in cur if re.fullmatch(r"[a-z]+", r["word"]) and r["word"] not in _whitelist())
    check("F1 无垃圾词头 (curriculum_vocab 词∈白名单)", not garbage, f"{len(garbage)} 疑垃圾: {garbage[:8]}")
    # F2: 总数≈官方三级1600 (含505小学带星; 初中level=三级 only=1187 非全集); 各地可增100-300 → [1500,1850]。
    check("F2 词汇总数 ≈ 官方三级1600 (含小学, OCR交叉验证不凑)", 1500 <= len(cur) <= 1850,
          f"total={len(cur)} (小学{len(xiao)}+初中{len(l3)}; 官方≈1600+可增)")
    check("F2b OCR 恢复丢词 (goal 等 glyph 误解码)", "goal" in words, f"goal 在={'goal' in words}")
    # F7: 官方二级505; 人工 vision 转写502 (缺3, §1.3 诚实标缺口不凑); 待补转写。
    check("F7 二级(小学) ≥500 (官方505, 转写诚实)", len(xiao) >= 500, f"{len(xiao)} (官方505, 缺{505 - len(xiao)}待补转写)")


def _check_hujiao(hj) -> None:
    cid = [r for r in hj if "(cid:" in r.get("zh_def", "")]
    check("F4 沪教无未标 cid 乱码释义", not cid, f"{len(cid)} 条含(cid:未标待OCR")
    n_hj = len({r["word"] for r in hj})
    check("F5 沪教词量护栏 (800-1400)", 800 <= n_hj <= 1400, f"{n_hj}")


def _zk_load(y: str) -> list | None:
    f = EXAMS / f"{y}_liaoning" / "exam_questions.jsonl"
    return [json.loads(l) for l in f.open(encoding="utf-8")] if f.exists() else None


def _zk_struct_ok(r: list) -> bool:
    """45题 + id唯一 + 题号1-45连续."""
    nums = sorted(x["question_number"] for x in r)
    return len(r) == 45 and len({x["question_id"] for x in r}) == 45 and nums == list(range(1, 46))


def _zk_meta_ok(r: list) -> bool:
    """每题 province=辽宁(§7) + 中考 + 题型分段口径一致."""
    return all(x["province"] == "辽宁" and x["exam_type"] == "中考"
               and x["question_type"] == _qtype_expect(x["question_number"]) for x in r)


def _zk_kaodian_ok(r: list) -> bool:
    """语篇填空(31-40)逐空带语法考点 (高考语法填空对齐核心数据)."""
    return all(x.get("kaodian") for x in r if 31 <= x["question_number"] <= 40)


def _check_zhongkao() -> None:
    """F9 中考真题结构化 D0 (坑17 新数据入门). 2024答案key驱动→全45官方答案; 2025题面驱动→语篇填空考点."""
    for y in ("2024", "2025"):
        r = _zk_load(y)
        if r is None:
            check(f"F9 中考{y} exam_questions 存在", False, "缺文件")
            continue
        ok = _zk_struct_ok(r) and _zk_meta_ok(r) and _zk_kaodian_ok(r)
        check(f"F9 中考{y}: 45题/id唯一/辽宁/题型分段/语篇填空考点全", ok, f"n={len(r)}")
    r = _zk_load("2024")
    if r:
        mcq_ok = all(x["answer"] in ("A", "B", "C", "D", "E") for x in r if 1 <= x["question_number"] <= 30)
        check("F9b 中考2024 官方答案全45 + MCQ(1-30)∈{A-E}", all(x.get("answer") for x in r) and mcq_ok,
              "官方key驱动")


def main() -> int:
    print("=== 初中子系统 D0 校验 (坑17 补门, 审计 F1-F8) ===")
    cur, hj = _words("curriculum_vocab.jsonl"), _words("hujiao_vocab.jsonl")
    _check_curriculum(cur)
    _check_hujiao(hj)
    _check_zhongkao()
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
