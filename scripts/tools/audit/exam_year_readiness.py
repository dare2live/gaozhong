#!/usr/bin/env python3
"""真题年入库预检 — 加一份卷前列缺口 (Occam: 不重构 init_db, 先让摩擦可见).

用法:
  python3 scripts/tools/audit/exam_year_readiness.py --year 2027
  python3 scripts/tools/audit/exam_year_readiness.py --year 2026 --exam-type zhongkao
  python3 scripts/tools/audit/exam_year_readiness.py --year 2026 --json

exit 0 = 无 BLOCK 缺口 (WARN 可有); exit 1 = 有 BLOCK (--strict 时 WARN 也退 1).
对照 docs/toplevel_architecture_design.md §2 #1 (目标 ≤2 处; 现状 ~8-9 处).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / "backend" / "config" / "sources.yaml"
CONTRACTS = ROOT / "backend" / "config" / "exam_paper_contracts.yaml"
ANCHORS = ROOT / "backend" / "config" / "truth_anchors.yaml"
YEAR_WEIGHTS = ROOT / "backend" / "config" / "year_weights.yaml"
INIT_DB = ROOT / "scripts" / "init_db.py"
EXAM_PY = ROOT / "backend" / "services" / "extraction" / "exam.py"
JUNIOR_EXAM = ROOT / "backend" / "services" / "data_sources" / "extract" / "junior" / "exam.py"
K12_PY = ROOT / "backend" / "services" / "k12.py"
SUBQ_DIR = ROOT / "data" / "structured" / "exam_subquestions"
GENRE_LABELS = ROOT / "data" / "structured" / "exam_point" / "genre_theme_labels.jsonl"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _check(items: list, name: str, ok: bool, detail: str, *, level: str = "block") -> None:
    items.append({"name": name, "ok": ok, "level": level if not ok else "ok", "detail": detail})


def audit_gaokao(year: int) -> list[dict]:
    items: list[dict] = []
    sources = _load_yaml(SOURCES).get("exam_sources") or {}
    src_hit = [k for k, v in sources.items() if isinstance(v, dict) and v.get("year") == year]
    _check(items, "sources.yaml 有 year 条目", bool(src_hit),
           f"keys={src_hit}" if src_hit else "缺 exam_sources year 登记")

    raw_c = _load_yaml(CONTRACTS)
    contracts = {}
    for v in (raw_c.get("contracts") or raw_c).values():
        if isinstance(v, dict) and isinstance(v.get("years"), dict):
            contracts.update(v["years"])
    has_c = str(year) in {str(k) for k in contracts} or year in contracts
    _check(items, "exam_paper_contracts.yaml 有 years.Y", has_c,
           "已登记" if has_c else "缺卷面契约 years 块", level="warn")

    raw_a = _load_yaml(ANCHORS)
    exam_block = (raw_a.get("exam") or {}).get("anchors") or {}
    key = f"{year}:辽宁:gaokao"
    has_a = key in exam_block
    life = (exam_block.get(key) or {}).get("lifecycle", "") if has_a else ""
    _check(items, f"truth_anchors 有 {key}", has_a,
           f"lifecycle={life}" if has_a else "缺真值锚(active 或 no_anchor)")

    weights = _load_yaml(YEAR_WEIGHTS).get("weights") or {}
    has_w = year in weights or str(year) in weights
    _check(items, "year_weights.yaml 含该年", has_w,
           f"w={weights.get(year) or weights.get(str(year))}" if has_w else "缺年份权重(滚动加最高权)",
           level="warn")

    init_txt = INIT_DB.read_text(encoding="utf-8") if INIT_DB.exists() else ""
    wired = str(year) in init_txt or f"xgkii{year}" in init_txt.lower()
    # 2024/2025 via import_pdfs registry — count as wired if sources hit + import_pdfs present
    if year in (2024, 2025) and "import_pdfs" in init_txt and src_hit:
        wired = True
    _check(items, "init_db.py 导入路径已接线", wired,
           "已接线" if wired else "需加 Layer 2a* importer 或扩 registry 遍历")

    exam_txt = EXAM_PY.read_text(encoding="utf-8") if EXAM_PY.exists() else ""
    m = re.search(r"LOCAL_PDF_LIAONING_YEARS\s*=\s*\(([^)]*)\)", exam_txt)
    local_years = []
    if m:
        local_years = [int(x) for x in re.findall(r"\d{4}", m.group(1))]
    needs_local = bool(src_hit) and any(
        (sources.get(k) or {}).get("family") == "exam_truth_source_local_pdf" for k in src_hit
    )
    if needs_local:
        _check(items, "LOCAL_PDF_LIAONING_YEARS 含该年", year in local_years,
               f"当前={local_years}", level="warn")

    subq_hits = list(SUBQ_DIR.glob(f"*_{year}_*.jsonl")) + list(SUBQ_DIR.glob(f"*{year}*.jsonl"))
    # also combined files may contain year
    combined = SUBQ_DIR / "xgkii_2021_2025_subquestions.jsonl"
    in_combined = False
    if combined.exists() and 2021 <= year <= 2025:
        in_combined = True
    _check(items, "exam_subquestions 产物存在", bool(subq_hits) or in_combined,
           f"files={[p.name for p in subq_hits]}" if subq_hits or in_combined else "缺 subquestions jsonl",
           level="warn")

    n_genre = 0
    if GENRE_LABELS.exists():
        for line in GENRE_LABELS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            if f"/{year}/" in line or f"_{year}_" in line or f"\"year\": {year}" in line or f"{year}/xgkii" in line:
                n_genre += 1
    _check(items, "genre_theme_labels 覆盖该年", n_genre > 0,
           f"匹配行≈{n_genre}" if n_genre else "链外标注未覆盖 — 分布会缺年", level="warn")

    return items


def audit_zhongkao(year: int) -> list[dict]:
    items: list[dict] = []
    qpath = ROOT / "data" / "junior_high" / "exams" / f"{year}_liaoning" / "exam_questions.jsonl"
    _check(items, "中考 structured jsonl 存在", qpath.exists(),
           str(qpath.relative_to(ROOT)) if qpath.exists() else f"缺 {qpath.relative_to(ROOT)}")

    jr = JUNIOR_EXAM.read_text(encoding="utf-8") if JUNIOR_EXAM.exists() else ""
    m = re.search(r'YEARS\s*=\s*\(([^)]*)\)', jr) or re.search(r'YEARS\s*=\s*\(([^)]*)\)', jr)
    years = re.findall(r'20\d{2}', jr)
    # parse YEARS = ("2024", "2025")
    m2 = re.search(r"YEARS\s*=\s*\(([^)]+)\)", jr)
    listed = re.findall(r"20\d{2}", m2.group(1)) if m2 else []
    _check(items, "junior/exam.py YEARS 含该年", str(year) in listed,
           f"当前={listed}")

    k12 = K12_PY.read_text(encoding="utf-8") if K12_PY.exists() else ""
    # look for years lists near zhongkao
    has_k12 = str(year) in k12
    _check(items, "k12.py 年份列表含该年", has_k12,
           "已出现" if has_k12 else "distribution API 可能漏年", level="warn")

    labels = ROOT / "data" / "junior_high" / "structured" / "genre_theme_labels.jsonl"
    n = 0
    if labels.exists():
        for line in labels.read_text(encoding="utf-8").splitlines():
            if str(year) in line:
                n += 1
    _check(items, "初中 genre_theme_labels 覆盖", n > 0,
           f"匹配行≈{n}" if n else "缺中考题材标注", level="warn")
    return items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--exam-type", choices=("gaokao", "zhongkao"), default="gaokao")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN 也退非零")
    args = ap.parse_args(argv)

    items = audit_gaokao(args.year) if args.exam_type == "gaokao" else audit_zhongkao(args.year)
    blocks = [i for i in items if not i["ok"] and i["level"] == "block"]
    warns = [i for i in items if not i["ok"] and i["level"] == "warn"]
    report = {
        "year": args.year,
        "exam_type": args.exam_type,
        "ready": not blocks,
        "n_block": len(blocks),
        "n_warn": len(warns),
        "items": items,
        "note": "预检只列缺口, 不执行入库; 目标摩擦≤2处见 toplevel_architecture_design §2",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== 真题年入库预检 {args.exam_type} {args.year} ===")
        for i in items:
            sym = "✅" if i["ok"] else ("⚠️" if i["level"] == "warn" else "❌")
            print(f"  {sym} {i['name']}  ({i['detail']})")
        print()
        if report["ready"]:
            print(f"✅ 无 BLOCK ({len(warns)} WARN) — 可继续入库/接线")
        else:
            print(f"❌ {len(blocks)} BLOCK / {len(warns)} WARN — 先补缺口再 init_db")
    if blocks:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
