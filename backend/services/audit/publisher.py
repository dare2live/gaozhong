"""辽宁 14 地市 ⊆ 8 允许版本 + 14 地市完整性."""
from __future__ import annotations

import duckdb

from ._common import finding

# 短名 → 出版社全名 substring (与 services/canonical.PUB_SHORT_MAP 同源)
SHORT_TO_FULL = {
    "外研版": "外语教学与研究出版社",
    "人教版": "人民教育出版社",
    "北师大版": "北京师范大学出版社",
    "译林版": "译林出版社",
}

EXPECTED_LIAONING_CITIES = {
    "沈阳", "大连", "鞍山", "抚顺", "本溪", "丹东", "锦州",
    "营口", "阜新", "辽阳", "盘锦", "铁岭", "朝阳", "葫芦岛",
}


def audit_publisher_coverage(con: duckdb.DuckDBPyConnection) -> list[dict]:
    allowed = {row[0] for row in con.execute(
        "SELECT DISTINCT publisher FROM liaoning_allowed_publishers WHERE subject='英语'"
    ).fetchall()}
    bad = [(city, short)
           for city, short in con.execute("""
               SELECT city, publisher_short FROM liaoning_city_textbook_choice
               WHERE subject='英语'
           """).fetchall()
           if not any(SHORT_TO_FULL.get(short, short) in a for a in allowed)]
    cities = {row[0] for row in con.execute(
        "SELECT city FROM liaoning_city_textbook_choice"
    ).fetchall()}
    missing = EXPECTED_LIAONING_CITIES - cities
    extra = cities - EXPECTED_LIAONING_CITIES
    return [
        finding("publisher_coverage", "FAIL" if bad else "OK",
                target="city_choice ⊆ allowed", expected="0 bad", actual=str(len(bad)),
                note=str(bad[:5]) if bad else "14 地市选用全部在 8 允许版本内"),
        finding("publisher_coverage",
                "FAIL" if missing else ("WARN" if extra else "OK"),
                target="14 地市 完整性", expected=str(sorted(EXPECTED_LIAONING_CITIES)),
                actual=str(sorted(cities)),
                note=f"missing={sorted(missing)} extra={sorted(extra)}"),
    ]
