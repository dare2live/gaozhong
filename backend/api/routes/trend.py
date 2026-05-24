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


def api_trend_question_type(_qs: dict) -> list[dict]:
    from backend.services.trend import question_type_year_trend
    con = db_ro()
    try: return question_type_year_trend(con)
    finally: con.close()


def api_trend_vocab_growth(_qs: dict) -> dict:
    from backend.services.trend import vocab_year_growth
    con = db_ro()
    try: return vocab_year_growth(con)
    finally: con.close()


def api_trend_rising_words(qs: dict) -> list[dict]:
    from backend.services.trend import top_rising_words
    try: n = min(int(qs.get("n", ["20"])[0]), 100)
    except ValueError: n = 20
    con = db_ro()
    try: return top_rising_words(con, top_n=n)
    finally: con.close()


ROUTES = {
    "/api/trend/summary": api_trend_summary,
    "/api/trend/top_words": api_trend_top_words,
    "/api/trend/question_type_trend": api_trend_question_type,
    "/api/trend/vocab_growth": api_trend_vocab_growth,
    "/api/trend/rising_words": api_trend_rising_words,
}
