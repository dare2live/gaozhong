"""GET /api/exercise/l1?unit=... — L1 课时单选题生成 (PoC)."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.exercise import poc as exercise_poc


def api_exercise_l1(qs: dict) -> dict:
    unit_id = qs.get("unit", [None])[0]
    if not unit_id:
        return {"error": "missing ?unit=<concept_id> (e.g. unit:waiyan/bixiu_1/U1)"}
    try:
        n = min(int(qs.get("n", ["5"])[0]), 30)
    except ValueError:
        n = 5
    seed_str = qs.get("seed", [None])[0]
    seed = int(seed_str) if seed_str and seed_str.isdigit() else None
    con = db_ro()
    try:
        return exercise_poc.generate_l1_quiz(con, unit_id, n=n, seed=seed)
    finally:
        con.close()


ROUTES = {"/api/exercise/l1": api_exercise_l1}
