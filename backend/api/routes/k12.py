"""K12 衔接 + 中考 API (inc4 薄壳; 计算在 backend/services/k12.py 单一计算点).

/api/k12/stage_distribution — 各 stage 知识点数 (at_stage 边)
/api/k12/tested_word_stage  — 辽宁高考考查词 按学段占比 ("最少覆盖最大" 实证, 北极星 Phase B)
/api/k12/blueprint          — 10维语法蓝图 (deepens 边; 中考∩高考)
/api/zhongkao/distribution  — 中考题型 + 语篇填空考点 (zhongkao_questions 视图)
/api/zhongkao/exam_focus    — 中考考查重点 (Phase F2; genre/theme/语法/高频词静态分布, 非趋势)
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services import k12


def api_stage_distribution(qs: dict) -> dict:
    con = db_ro()
    try:
        return {"scope": "辽宁/沈阳 K12 (小学→初中→高中)", "layered_by": "stage 维 (at_stage 边)",
                "by_stage": k12.stage_distribution(con),
                "coverage": k12.stage_unstaged_disclosure(con)}  # 未分阶词披露 (审计MEDIUM 防静默截断)
    finally:
        con.close()


def api_tested_word_stage(qs: dict) -> dict:
    con = db_ro()
    try:
        d = k12.tested_word_stage_distribution(con)
        d["scope"] = "辽宁高考离散考点题型考查词(去重)"
        d["caveat"] = "考查口径(出现≠考查); 学段=at_stage边; 未分类=校本超纲/外省词无标准阶, 不估算"
        return d
    finally:
        con.close()


def api_blueprint(qs: dict) -> dict:
    con = db_ro()
    try:
        return k12.blueprint(con)
    finally:
        con.close()


def api_zhongkao_distribution(qs: dict) -> dict:
    con = db_ro()
    try:
        return k12.zhongkao_distribution(con)
    finally:
        con.close()


def api_zhongkao_exam_focus(qs: dict) -> dict:
    con = db_ro()
    try:
        return k12.zhongkao_exam_point_summary(con)
    finally:
        con.close()


ROUTES = {
    "/api/k12/stage_distribution": api_stage_distribution,
    "/api/k12/tested_word_stage": api_tested_word_stage,
    "/api/k12/blueprint": api_blueprint,
    "/api/zhongkao/distribution": api_zhongkao_distribution,
    "/api/zhongkao/exam_focus": api_zhongkao_exam_focus,
}
