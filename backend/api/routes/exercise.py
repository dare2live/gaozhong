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


def api_exercise_l2(qs: dict) -> dict:
    ver = qs.get("version", ["waiyan"])[0]
    vol = qs.get("volume", [None])[0]
    if not vol:
        return {"error": "missing ?volume= (e.g. bixiu_1)"}
    try:
        n = min(int(qs.get("n", ["20"])[0]), 100)
    except ValueError:
        n = 20
    seed_str = qs.get("seed", [None])[0]
    seed = int(seed_str) if seed_str and seed_str.isdigit() else None
    con = db_ro()
    try:
        return exercise_poc.generate_l2_quiz(con, ver, vol, n=n, seed=seed)
    finally:
        con.close()


def api_exercise_l4(qs: dict) -> dict:
    province = qs.get("province", ["辽宁"])[0]
    try:
        year_min = int(qs.get("year_min", ["2020"])[0])
        n = min(int(qs.get("n", ["25"])[0]), 100)
    except ValueError:
        year_min, n = 2020, 25
    seed_str = qs.get("seed", [None])[0]
    seed = int(seed_str) if seed_str and seed_str.isdigit() else None
    con = db_ro()
    try:
        return exercise_poc.generate_l4_paper(con, province=province,
                                                year_min=year_min, n=n, seed=seed)
    finally:
        con.close()


def api_exercise_cloze(qs: dict) -> dict:
    from backend.services.exercise import cloze
    unit = qs.get("unit", [None])[0]
    try: n = min(int(qs.get("n", ["10"])[0]), 20)
    except ValueError: n = 10
    seed_str = qs.get("seed", [None])[0]
    seed = int(seed_str) if seed_str and seed_str.isdigit() else None
    con = db_ro()
    try:
        return cloze.generate_cloze(con, unit_id=unit, n_blanks=n, seed=seed)
    finally: con.close()


def api_exercise_grammar_fill(qs: dict) -> dict:
    from backend.services.exercise import grammar_fill
    unit = qs.get("unit", [None])[0]
    try: n = min(int(qs.get("n", ["10"])[0]), 20)
    except ValueError: n = 10
    seed_str = qs.get("seed", [None])[0]
    seed = int(seed_str) if seed_str and seed_str.isdigit() else None
    con = db_ro()
    try:
        return grammar_fill.generate_grammar_fill(con, unit_id=unit, n_blanks=n, seed=seed)
    finally: con.close()


def api_exercise_applied_templates(_qs: dict) -> dict:
    from backend.services.exercise import applied
    con = db_ro()
    try: return applied.list_applied_templates(con)
    finally: con.close()


def api_exercise_narrative_passages(_qs: dict) -> dict:
    from backend.services.exercise import applied
    con = db_ro()
    try: return applied.list_narrative_passages(con)
    finally: con.close()


def api_exercise_predicted(qs: dict) -> dict:
    from backend.services.exercise import predicted
    try: total = min(int(qs.get("n", ["30"])[0]), 80)
    except ValueError: total = 30
    seed_s = qs.get("seed", [None])[0]
    seed = int(seed_s) if seed_s and seed_s.isdigit() else None
    con = db_ro()
    try: return predicted.generate_predicted_paper(con, total=total, seed=seed)
    finally: con.close()


ROUTES = {
    "/api/exercise/l1": api_exercise_l1,
    "/api/exercise/l2": api_exercise_l2,
    "/api/exercise/l4": api_exercise_l4,
    "/api/exercise/cloze": api_exercise_cloze,
    "/api/exercise/grammar_fill": api_exercise_grammar_fill,
    "/api/exercise/applied_templates": api_exercise_applied_templates,
    "/api/exercise/narrative_passages": api_exercise_narrative_passages,
    "/api/exercise/predicted": api_exercise_predicted,
}
