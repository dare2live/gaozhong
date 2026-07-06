"""POST /api/student_answers — 学生端最小闭环写入 (2026-07-06 数据关联设计审查批次6).

坑: 学生端(student.js)原来提交答题只在浏览器本地计分, 从不写库 — student_answers 表
100%demo数据, weakness画像永远吃不到真实作答, "学情反哺教学"这条北极星能力名存实亡。
本端点打通写入; real学生走独立student_id(前端localStorage生成'real-'前缀), 不复用
既有5个demo学生(demo数据determinism不能被真实答题污染, source字段全程物理隔离)。

GET(无body)按契约探测返回 {"error": "POST body required"}(allow_error, 与本项目其它
POST-body端点如 /api/placement/score 同款契约模式), 真实写入走 POST。
"""
from __future__ import annotations

import json

from backend.api.db import db_write


def api_submit_student_answers(qs: dict, body: bytes | None = None) -> dict:
    if not body:
        return {"error": "POST body required: {student_id, name, city, answers: [...]}"}
    try:
        data = json.loads(body)
    except Exception as e:
        return {"error": f"bad JSON: {e}"}
    student_id = (data.get("student_id") or "").strip()
    if not student_id:
        return {"error": "missing student_id"}
    answers = data.get("answers") or []
    if not isinstance(answers, list):
        return {"error": "answers must be a list"}
    from backend.services.students import submit_real_answers
    with db_write() as con:
        return submit_real_answers(con, student_id, data.get("name") or "", data.get("city") or "", answers)


ROUTES = {"/api/student_answers": api_submit_student_answers}
