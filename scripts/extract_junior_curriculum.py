"""义务教育课标 2022 → 初中子系统 stage 真相源 (Phase 1).

emit:
  data/junior_high/structured/curriculum_vocab.jsonl   词 + level(二级/三级) + stage(小学/初中)
  data/junior_high/structured/grammar_items.jsonl      语法项目 (idx144-148)
reconcile (S4 桥接, 设计§1 承重决策): 初中三级 ↔ 高中义教 对账 → stdout 报告。

stage 切分铁律 (robust, 不靠 CMap-损坏的 * 星标):
  小学 = 三级 ∩ 二级(人工转写 _vision_l2.txt 权威 505)
  初中 = 三级 − 二级
源诚实(§1.3): 三级抽 1589/官方1600(CMap损坏漏~11), emit 标 extracted_n, 不凑 1600。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.lib import junior_high_curriculum as jh

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "junior_high" / "structured"
L2_VISION = OUT / "_vision_l2.txt"
DB = ROOT / "data" / "db" / "gaozhong.duckdb"


def _load_l2_vision() -> set[str]:
    """二级(小学)权威词集 — 人工 vision-OCR 转写, 剥括号变体取主词."""
    words: set[str] = set()
    for raw in L2_VISION.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        main = re.sub(r"\([^)]*\)", "", line).strip()
        m = re.match(r"^([A-Za-z][A-Za-z\-'/]*)", main)
        if m:
            words.add(m.group(1).lower().strip("/-'."))
    return words


def _split_slash(words: set[str]) -> set[str]:
    """拆 slash 变体: a/an→{a,an}, actor/actress→{actor,actress} (课标 '/'='或').
    强验证 G1/L2a: 保留内部 -/' (o'clock/ping-pong) — 原 isalpha() 误踢含连字/撇号的二级词。"""
    out: set[str] = set()
    for w in words:
        for part in w.split("/"):
            p = part.strip("-'. ")
            if p and re.fullmatch(r"[A-Za-z][A-Za-z\-']*", p):
                out.add(p)
    return out


def _load_ocr_words() -> set[str]:
    """OCR 课标词表页缓存 (PaddleOCR 视觉真值, 绕文本层 glyph 误解码; 持久于 structured/)."""
    p = OUT / "_ocr_curriculum_words.txt"
    return {l.strip().lower() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()} if p.exists() else set()


def _dictionary() -> set[str]:
    """英文真词词典 (严格: COCA∪cefr∪沪教, **不含 systemdict** — 它收 obscure 词放 glyph 垃圾 ai/gif)."""
    import os
    import duckdb
    wl: set[str] = set()
    p = "data/structured/english-wordlists/COCA_20000.txt"
    if os.path.exists(p):
        wl |= {l.split(",")[0].split("\t")[0].strip().lower()
               for l in open(p, encoding="utf-8", errors="ignore") if l.strip()}
    c = duckdb.connect(str(DB), read_only=True)
    wl |= {r[0] for r in c.execute("SELECT word FROM cefr_vocab").fetchall()}
    c.close()
    hj = OUT / "hujiao_vocab.jsonl"
    if hj.exists():
        wl |= {json.loads(l)["word"] for l in hj.open(encoding="utf-8")}
    return wl


def _sysdict_long() -> set[str]:
    """systemdict 长词(len≥4): 收真词(antelope)不收短 glyph 垃圾(ai/gif/fu)."""
    import os
    p = "/usr/share/dict/words"
    if not os.path.exists(p):
        return set()
    return {l.strip().lower() for l in open(p, encoding="utf-8", errors="ignore") if len(l.strip()) >= 4}


# 文本层错切残片/编辑标记 (官方口径非词条, 强验证 L3a): ame/bre=AmE/BrE 标记, fu=full 截断残片.
_GARBAGE = {"ame", "bre", "fu"}


def _cross_validate(l3_text: set, l2: set, ocr: set, paren: set) -> set:
    """OCR 交叉验证 (审计 F1/F2/F2b, master §3): glyph 误解码垃圾(fuit/ai)在文本层, OCR 读正确印刷词。
    干净 = (文本∩真词)[clean] ∪ (文本∩OCR)[互证如app] ∪ (OCR∩真词−括号词)[恢复 fruit/goal]; 滤 misspelling。
    官方口径 (强验证 L3b/c): 括号内 gloss/变体(application/color/theater) 只经 OCR 混入,
    从恢复项减掉(词头在 l3_text 不动, 如 education); −_GARBAGE 去文本层错切残片(ame/fu)。"""
    if not ocr:
        return l3_text - _GARBAGE
    real = _dictionary() | l2
    keep = real | _sysdict_long()
    return ((l3_text & keep) | (l3_text & ocr) | ((ocr & real) - paren)) - _GARBAGE


def _vocab_rows(l3_words: set, l2: set, ocr: bool) -> list[dict]:
    """stage/level 切分: 小学/二级=∩二级, 初中/三级=其余 (集合交, 不靠损坏星标)."""
    src = "义务教育英语课程标准2022 附录3" + (" (OCR交叉验证)" if ocr else "")
    rows = []
    for w in sorted(l3_words | l2):
        in_l2 = w in l2
        rows.append({"word": w, "level": "二级" if in_l2 else "三级",
                     "stage": "小学" if in_l2 else "初中", "source": src})
    return rows


def _emit(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def build() -> dict:
    l2 = _split_slash(_load_l2_vision())
    l3_text = _split_slash({r["word"] for r in jh.extract_vocab("三级", "初中", jh.L3_AZ_PAGES, "yiwu_2022_L3")})
    ocr = _load_ocr_words()
    paren = _split_slash(jh.extract_paren_words())   # 括号内 gloss/变体 (官方口径非独立词条)
    l3_words = _cross_validate(l3_text, l2, ocr, paren)
    vocab = _vocab_rows(l3_words, l2, bool(ocr))
    grammar = jh.extract_grammar()
    _emit("curriculum_vocab.jsonl", vocab)
    _emit("grammar_items.jsonl", grammar)
    n_xiao = sum(1 for r in vocab if r["stage"] == "小学")
    return {"vocab_total": len(vocab), "小学": n_xiao, "初中": len(vocab) - n_xiao,
            "l3_extracted": len(l3_words), "l2_vision": len(l2), "grammar": len(grammar)}


def reconcile() -> None:
    """S4 桥接对账: 初中(三级) ↔ 高中义教 — 验证两课标接缝 (设计§1 承重)."""
    import duckdb
    vocab = [json.loads(l) for l in (OUT / "curriculum_vocab.jsonl").open(encoding="utf-8")]
    yiwu = {r["word"] for r in vocab}                      # 义务教育全(小学+初中)
    c = duckdb.connect(str(DB), read_only=True)
    hs_yj = {r[0] for r in c.execute("SELECT word FROM cefr_vocab WHERE cefr_level='义教'").fetchall()}
    c.close()
    overlap = yiwu & hs_yj
    print("\n=== S4 stage 桥接对账 (义务课标三级 ↔ 高中课标义教级) ===")
    print(f"义务教育(小学+初中) 词集: {len(yiwu)}")
    print(f"高中课标'义教'级 词集: {len(hs_yj)}")
    print(f"重叠(两课标都认=义务教育阶段确证): {len(overlap)} ({len(overlap)/max(1,len(hs_yj)):.0%} of 高中义教)")
    print(f"高中标义教但义务课标无: {len(hs_yj - yiwu)} 例 {sorted(hs_yj-yiwu)[:12]}")
    print(f"义务课标有但高中义教无(高中可能标必修/选必或未收): {len(yiwu - hs_yj)}")


if __name__ == "__main__":
    summary = build()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    reconcile()
