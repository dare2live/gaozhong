#!/usr/bin/env python3
"""验收验证协议 — 共享常量 + 纯结果归一化 helper.

被 verification_protocol.py 与 verification_feedback.py 共用，避免循环 import。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
PROTOCOL_PATH = ROOT / "data" / "reports" / "verification_protocol.json"
DEFAULT_OWNER = "项目用户侧 + 研发协同"
DEFAULT_DEADLINE = "2026-06-17T18:00:00+08:00"
DEFAULT_PLANNED_WINDOW = "2026-06-16 18:00-2026-06-17 18:00"
DEFAULT_CLOSURE_RULE = "任一 defer 补齐后改为 DONE；超期仍未补齐时保持 deferred 并更新 goal.md 风险条目"
M3_FEEDBACK_TEMPLATE = "m3_feedback_{run_id}.json"
RUN_ID_GLOB = "m3_feedback_*.json"

CHECKLIST = [
    {"id": "V1", "step": "摸底测验", "desc": "学生完成 G1/G2/G3 摸底测验, 系统推荐课节",
     "url": "/app#/students", "duration_min": 10},
    {"id": "V2", "step": "查看推荐课节", "desc": "点击推荐课节, 查看讲义内容",
     "url": "/app#/teaching", "duration_min": 5},
    {"id": "V3", "step": "上课 (讲义)", "desc": "阅读一节完整讲义 (7 段), 检查内容可读性",
     "url": "/app#/teaching → 点课节", "duration_min": 15},
    {"id": "V4", "step": "课后测验", "desc": "点击'课后测验'按钮, 完成 10 题, 系统批改",
     "url": "讲义 modal 底部", "duration_min": 10},
    {"id": "V5", "step": "听力练习", "desc": "进入 C tab, 播放听力, 展开原文, 做题",
     "url": "/app#/qbank", "duration_min": 10},
    {"id": "V6", "step": "查看弱点", "desc": "进入 E tab, 查看弱点分析 + 推送课节",
     "url": "/app#/students → 点学生", "duration_min": 5},
    {"id": "V7", "step": "知识图谱", "desc": "点击概念链接, 弹出关联图 + 真题",
     "url": "/app#/graph 或讲义内 concept link", "duration_min": 5},
    {"id": "V8", "step": "打印讲义", "desc": "点击打印按钮, 检查 PDF 输出",
     "url": "讲义 modal → 打印按钮", "duration_min": 3},
]

REMEDIATION_PLAN = {
    "V1": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "完成 1 次学生复核 session，补齐推荐课节/弱点推送映射"},
    "V2": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "安排教师选课节演示并补齐可视化与可读性反馈"},
    "V3": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "安排至少一节讲义核心流程的学习复核并记录阅读中断点与耗时"},
    "V4": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "执行至少 1 次课后测验（建议 10 题）并记录提交/批改过程"},
    "V5": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "安排至少 1 条听力题完整播放-答题-结果流程"},
    "V6": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "触发弱点 drill 并确认课节推荐输出合理性"},
    "V7": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "点击 1~2 个 conceptLink，确认 popup 与真题可见且可返回"},
    "V8": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "点击打印按钮，确认输出 PDF/打印行为可用且无报错"},
}

# 只把纯静态可复核项置为 done：V3/V4/V8 有可复核源码证据，其他项暂置 deferred。
AUTO_SYSTEM_DONE_IDS = {"V3", "V4", "V8"}
CLOSURE_BATCH_IDS = {"V1", "V2", "V5", "V6", "V7"}


def _needs_real_user_completion(status: str, feedback: str) -> bool:
    if status not in {"done", "DONE"}:
        return False
    text = (feedback or "").lower()
    return any(flag in text for flag in ("未完成", "未执行", "代录", "待复核"))


def _normalize_results(results: dict) -> dict:
    for check_id, item in results.items():
        if _needs_real_user_completion(item.get("status", ""), item.get("feedback", "")):
            item["status"] = "deferred"
            item["feedback"] = (
                (item.get("feedback", "").strip() + "；")
                if item.get("feedback", "").strip() and not item.get("feedback", "").strip().endswith("；")
                else item.get("feedback", "").strip()
            ) + "复核未完成，先保留为 deferred."
            item["notes"] = "复测未完成前不计入关闭态"
    return results
