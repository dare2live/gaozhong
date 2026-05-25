"""设计宪法 API — 前端展示 + 生成管线查询约束."""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services import constitution


def api_constitution_list(qs: dict) -> dict:
    con = db_ro()
    try:
        rules = constitution.load_all(con)
        by_type = {}
        for r in rules:
            by_type.setdefault(r["rule_type"], []).append(r)
        return {"rules": rules, "count": len(rules), "by_type": {k: len(v) for k, v in by_type.items()}}
    finally:
        con.close()


def api_constitution_compliance(qs: dict) -> dict:
    return constitution.check_compliance()


ROUTES = {
    "/api/constitution/list": api_constitution_list,
    "/api/constitution/compliance": api_constitution_compliance,
}
