"""学习者轻闭环 API — 摸底缺口 → 课程高亮."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.learner import gap_highlights


def api_learner_gap_highlights(qs: dict) -> dict:
    sid = (qs.get("student_id", [None])[0] or qs.get("id", [None])[0] or "").strip()
    con = db_ro()
    try:
        return gap_highlights(con, sid)
    finally:
        con.close()


ROUTES = {
    "/api/learner/gap_highlights": api_learner_gap_highlights,
}
