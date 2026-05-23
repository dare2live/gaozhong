"""GET /api/trend/* — 历年高考趋势 (词频 / 题型分布)."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services import trend as tsvc


def api_trend_summary(_qs: dict) -> dict:
    con = db_ro()
    try:
        return tsvc.trend_summary(con)
    finally:
        con.close()


def api_trend_top_words(qs: dict) -> list[dict]:
    try:
        top_n = min(int(qs.get("n", ["50"])[0]), 200)
    except ValueError:
        top_n = 50
    con = db_ro()
    try:
        return tsvc.top_high_freq_words(con, top_n=top_n)
    finally:
        con.close()


ROUTES = {
    "/api/trend/summary": api_trend_summary,
    "/api/trend/top_words": api_trend_top_words,
}
