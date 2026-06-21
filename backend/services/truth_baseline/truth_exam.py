"""真题真值校验器 — 库内真题内容 ∩ 第一手真值锚 markers (红线①省份污染根治).

验"2021辽宁库内容是否含真值卷篇章标志(Take a view/rhino)", 不是"2021辽宁计数==182"。
eol 误标的 Zafirakou/Harrogate 不含真值 markers → content_mismatch BLOCK (旧门验计数永远绿)。
"""
from __future__ import annotations

from .base import Deviation, TruthChecker, load_anchors


def _db_text(con, year: int, province: str) -> str:
    r = con.execute(
        "SELECT string_agg(raw_question, ' ') FROM exam_questions_all "
        "WHERE year = ? AND province LIKE ?", [year, province + "%"]).fetchone()
    return (r[0] or "").lower() if r else ""


def _check_anchor(con, key: str, a: dict) -> Deviation | None:
    """单锚: active→内容比对; no_anchor→UNKNOWN(不冒充已验证)."""
    if a.get("lifecycle") != "active":
        return Deviation("exam", key, "no_anchor", "UNKNOWN",
                         f"{a['year']}{a['province']}卷无第一手真值锚(provenance={a.get('provenance')}); "
                         "不冒充已验证, 待补锚")
    txt = _db_text(con, a["year"], a["province"])
    missing = [m for m in a["markers"] if m.lower() not in txt]
    if missing:
        return Deviation("exam", key, "content_mismatch", "BLOCK",
                         f"{a['year']}{a['province']}卷入库内容≠真值锚(provenance={a['provenance']}): "
                         f"缺标志篇章 {missing} of {a['markers']}; 疑省份/卷型污染(§7红线)")
    return None


class ExamTruthChecker(TruthChecker):
    domain = "exam"

    def check(self, con) -> list[Deviation]:
        anchors = load_anchors().get("exam", {}).get("anchors", {})
        out = []
        for key, a in anchors.items():
            dev = _check_anchor(con, key, a)
            if dev:
                out.append(dev)
        return out

    def self_test(self) -> bool:
        """注入: 2021辽宁缺markers→必抓content_mismatch; 含markers→不误报."""
        import duckdb
        c = duckdb.connect(":memory:")
        c.execute("CREATE TABLE exam_questions_all(year INTEGER, province VARCHAR, raw_question VARCHAR)")
        c.execute("INSERT INTO exam_questions_all VALUES (2021,'辽宁','Zafirakou Harrogate tiger cub no anchors here')")
        polluted = [d for d in self.check(c) if d.anchor_key.startswith("2021") and d.kind == "content_mismatch"]
        c.execute("DELETE FROM exam_questions_all")
        c.execute("INSERT INTO exam_questions_all VALUES (2021,'辽宁','... Take a view ... rhino ... City Wall ...')")
        clean = [d for d in self.check(c) if d.anchor_key.startswith("2021") and d.kind == "content_mismatch"]
        c.close()
        return bool(polluted) and not clean
