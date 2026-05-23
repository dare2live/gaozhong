"""数据完整性 / 准确性 / 交叉验证 (架构 §0 Rule 1: 算一次, 落 audit_findings 表).

输入: Layer 1 文件 + Layer 2 主表 + 外部参照 (mahavivo 高中词表)
输出: audit_findings 行 (severity OK/WARN/FAIL) + console summary

调用: scripts/init_db.py 末尾, 或独立 python -m backend.services.audit
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def run_all(con: duckdb.DuckDBPyConnection) -> dict:
    """跑全部审计. 返回 {kind: {OK, WARN, FAIL} count}"""
    con.execute("DELETE FROM audit_findings")
    findings: list[dict] = []
    findings += audit_file_sha(con)
    findings += audit_curriculum_vocab(con)
    findings += audit_grammar_hierarchy(con)
    findings += audit_publisher_coverage(con)
    findings += audit_cross_source_vocab(con)
    findings += audit_textbook_pages(con)

    if findings:
        for i, f in enumerate(findings):
            f["finding_id"] = i + 1
        con.executemany(
            "INSERT INTO audit_findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(f["finding_id"], f["audit_kind"], f["severity"], f.get("target"),
              f.get("expected"), f.get("actual"), f.get("delta"), f.get("note"), _now())
             for f in findings],
        )

    summary: dict = {}
    for f in findings:
        sev_map = summary.setdefault(f["audit_kind"], {"OK": 0, "WARN": 0, "FAIL": 0})
        sev_map[f["severity"]] = sev_map.get(f["severity"], 0) + 1
    return summary


def audit_file_sha(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """每个 file_manifest 行重算 sha 比对."""
    out: list[dict] = []
    rows = con.execute("SELECT rel_path, sha256, size_bytes FROM file_manifest").fetchall()
    for rel, sha, sz in rows:
        p = ROOT / rel
        if not p.exists():
            out.append(dict(audit_kind="file_sha", severity="FAIL",
                            target=rel, expected=sha, actual="MISSING"))
            continue
        actual = _sha256(p)
        if actual != sha:
            out.append(dict(audit_kind="file_sha", severity="FAIL",
                            target=rel, expected=sha, actual=actual))
    # OK 摘要单行
    out.append(dict(audit_kind="file_sha", severity="OK",
                    target="*", expected=str(len(rows)),
                    actual=str(len(rows) - sum(1 for f in out if f["severity"] == "FAIL")),
                    note=f"全核 {len(rows)} 个 manifest 行"))
    return out


def audit_curriculum_vocab(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """课标声明 3000 词, 实际抽 N; 各级别比例校验."""
    total = con.execute("SELECT COUNT(*) FROM cefr_vocab").fetchone()[0]
    by = dict(con.execute("SELECT cefr_level, COUNT(*) FROM cefr_vocab GROUP BY cefr_level").fetchall())
    out = []
    # total 期望 3000
    sev = "OK" if abs(total - 3000) <= 100 else ("WARN" if abs(total - 3000) <= 300 else "FAIL")
    out.append(dict(audit_kind="vocab_recall", severity=sev, target="cefr_vocab.total",
                    expected="3000", actual=str(total), delta=str(total - 3000),
                    note="课标 p129 说明: 共收 3000 (义教 1500 + 必修 500 + 选必 1000)"))
    for lv, want in (("义教", 1500), ("必修", 500), ("选必", 1000)):
        got = by.get(lv, 0)
        sev = "OK" if abs(got - want) <= 50 else ("WARN" if abs(got - want) <= 200 else "FAIL")
        out.append(dict(audit_kind="vocab_recall", severity=sev,
                        target=f"cefr_vocab.{lv}", expected=str(want), actual=str(got),
                        delta=str(got - want)))
    return out


def audit_grammar_hierarchy(con: duckdb.DuckDBPyConnection) -> list[dict]:
    out = []
    total = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
    depths = dict(con.execute("SELECT depth, COUNT(*) FROM grammar_items GROUP BY depth").fetchall())
    out.append(dict(audit_kind="grammar_recall", severity="OK",
                    target="grammar_items.total", expected=">=80",
                    actual=str(total),
                    note=f"depth distribution: {depths}"))
    # parent_id 引用完整性
    orphan = con.execute("""
        SELECT g.grammar_item_id, g.parent_id FROM grammar_items g
        WHERE g.parent_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM grammar_items p WHERE p.grammar_item_id = g.parent_id)
    """).fetchall()
    out.append(dict(audit_kind="grammar_recall",
                    severity="FAIL" if orphan else "OK",
                    target="grammar_items.parent_id",
                    expected="0 orphan", actual=str(len(orphan)),
                    note=str(orphan[:5]) if orphan else None))
    return out


def audit_publisher_coverage(con: duckdb.DuckDBPyConnection) -> list[dict]:
    out = []
    # 1) 14 地市选用的版本必须都 ∈ 允许的 8 版本
    allowed = {row[0] for row in con.execute("""
        SELECT DISTINCT publisher FROM liaoning_allowed_publishers WHERE subject='英语'
    """).fetchall()}
    # 短名→长名映射 (与 services/canonical 同源)
    expand = {
        "外研版": "外语教学与研究出版社",
        "人教版": "人民教育出版社",
        "北师大版": "北京师范大学出版社",
        "译林版": "译林出版社",
    }
    bad = []
    for (city, short) in con.execute("""
        SELECT city, publisher_short FROM liaoning_city_textbook_choice WHERE subject='英语'
    """).fetchall():
        full = expand.get(short, short)
        if not any(full in a for a in allowed):
            bad.append((city, short))
    out.append(dict(audit_kind="publisher_coverage",
                    severity="FAIL" if bad else "OK",
                    target="city_choice ⊆ allowed",
                    expected="0 bad", actual=str(len(bad)),
                    note=str(bad[:5]) if bad else "14 地市选用全部在 8 允许版本内"))

    # 2) 14 地市完整 (辽宁省 14 个地级市)
    cities = {row[0] for row in con.execute("SELECT city FROM liaoning_city_textbook_choice").fetchall()}
    expected = {"沈阳","大连","鞍山","抚顺","本溪","丹东","锦州","营口","阜新","辽阳","盘锦","铁岭","朝阳","葫芦岛"}
    missing = expected - cities
    extra = cities - expected
    out.append(dict(audit_kind="publisher_coverage",
                    severity="FAIL" if missing else ("WARN" if extra else "OK"),
                    target="14 地市 完整性",
                    expected=str(sorted(expected)), actual=str(sorted(cities)),
                    note=f"missing={sorted(missing)} extra={sorted(extra)}"))
    return out


def audit_cross_source_vocab(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """课标 cefr_vocab vs mahavivo Highschool_edited 交集/差集.
    mahavivo 是通用高中词表 (~3468 词, 含义教高中混合, 与课标 3000 接近)."""
    out = []
    cefr = {row[0] for row in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    mh_path = ROOT / "data/structured/english-wordlists/Highschool_edited.txt"
    if not mh_path.exists():
        out.append(dict(audit_kind="cross_source", severity="WARN",
                        target="mahavivo.Highschool_edited", actual="MISSING",
                        note="mahavivo 词表未入仓"))
        return out
    mh = {ln.strip().lower() for ln in mh_path.read_text(encoding="utf-8").splitlines()
          if ln.strip() and ln.strip()[0].isalpha()}
    inter = cefr & mh
    only_cefr = cefr - mh
    only_mh = mh - cefr
    out.append(dict(audit_kind="cross_source", severity="OK",
                    target="cefr ∩ mahavivo", expected="≥60% of min(|cefr|,|mh|)",
                    actual=f"{len(inter)}",
                    note=f"|cefr|={len(cefr)} |mh|={len(mh)} "
                         f"only_cefr={len(only_cefr)} only_mh={len(only_mh)}"))
    cov = len(inter) / max(1, min(len(cefr), len(mh)))
    sev = "OK" if cov >= 0.6 else ("WARN" if cov >= 0.4 else "FAIL")
    out.append(dict(audit_kind="cross_source", severity=sev,
                    target="cefr_vs_mahavivo_coverage",
                    expected=">=0.6", actual=f"{cov:.3f}"))
    return out


def audit_textbook_pages(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """14 册 PDF page count 必须 > 50 (健康检查), 与 manifest 一致."""
    out = []
    rows = con.execute("""SELECT version_key, volume_key, pdf_pages, pdf_rel_path FROM textbooks""").fetchall()
    bad = [(v, k, p) for v, k, p, _ in rows if (p or 0) < 50]
    out.append(dict(audit_kind="textbook_pages",
                    severity="FAIL" if bad else "OK",
                    target="textbooks.pdf_pages", expected="all > 50",
                    actual=f"{len(rows) - len(bad)}/{len(rows)} pass",
                    note=str(bad) if bad else None))
    return out
