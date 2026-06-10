#!/usr/bin/env python3
"""真人验证协议 — Gate 6 流程化. 生成验证清单 + 记录结果.

用法:
    python3 scripts/tools/monitor/verification_protocol.py --generate  # 生成验证清单
    python3 scripts/tools/monitor/verification_protocol.py --generate --pending  # 生成待执行清单（pending）
    python3 scripts/tools/monitor/verification_protocol.py --report    # 查看验证状态
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
PROTOCOL_PATH = ROOT / "data" / "reports" / "verification_protocol.json"
DEFAULT_OWNER = "项目用户侧 + 研发协同"
DEFAULT_DEADLINE = "2026-06-17T18:00:00+08:00"
DEFAULT_PLANNED_WINDOW = "2026-06-16 18:00-2026-06-17 18:00"
DEFAULT_CLOSURE_RULE = "任一 defer 真实场景补齐后改为 DONE；超期仍未补齐时保持 deferred 并更新 goal.md 风险条目"

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
    "V3": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "真人跟读至少一节讲义核心流程并记录阅读中断点与耗时"},
    "V4": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "执行至少 1 次课后测验（建议 10 题）并记录提交/批改过程"},
    "V5": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "安排真人进行至少 1 条听力题完整播放-答题-结果流程"},
    "V6": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "真人触发弱点 drill 并确认课节推荐输出合理性"},
    "V7": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "真人点击 1~2 个 conceptLink，确认 popup 与真题可见且可返回"},
    "V8": {"owner": "项目用户侧", "due": DEFAULT_DEADLINE, "plan": "真人点按打印按钮，确认输出 PDF/打印行为可用且无报错"},
}


def _build_feedback_defaults(check_id: str) -> str:
    return {
        "V1": "本轮未能安排高一/高二/高三学生真人摸底验收；代录：`students` tab 与推荐区组件在 /app 结构中可复核（见 docs/app_smoke_round1.md）。",
        "V2": "教师推荐课节链路未执行真人点击；已通过代码与路由证据确认 `#/teaching` 可达、讲义加载逻辑存在（见 docs/app_smoke_round1.md）。",
        "V3": "未完成 1 名学生真实阅读流程；代录依据为讲义模板与 7 段结构静态可达（`frontend/static/app_router.js` + `course/handout.py`）。",
        "V4": "课后测验未执行真人交互；可回放链路存在（讲义 modal 有 quiz 发起与提交入口，见 frontend/app.js）。",
        "V5": "未执行真人听力闭环；静态链路以 `qbank` tab + 听力题目加载为代证，已纳入 M3 口径替代证据。",
        "V6": "弱点 drill 未真人复测；代证为 `students` tab 学生弱点/推荐 API 可见且链路完整（见 app_router 组件）。",
        "V7": "知识图谱未做真人点击验证；代证为图谱弹窗（`frontend/static/graph_popup.js`）与 `course` conceptLink 绑定链路已提交到代码级快照。",
        "V8": "打印按钮未真人点按；代证为 `frontend/static/app_router.js:117-123` 里的 `onclick=\"window.print()\"`，可复现源码路径。",
    }.get(check_id, "待真人复核")


def _load_existing_results() -> dict:
    if not PROTOCOL_PATH.exists():
        return {}
    try:
        existing = json.loads(PROTOCOL_PATH.read_text())
        return existing.get("results", {})
    except Exception:
        return {}


def generate_protocol(pending: bool = False) -> dict:
    """生成验证清单 JSON."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        stats = {
            "questions": con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0],
            "courses": con.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
            "students": con.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        }
    finally:
        con.close()
    existing = _load_existing_results()
    init_status = "pending" if pending else "deferred"
    protocol = {
        "generated_at": datetime.now().isoformat(),
        "system_stats": stats,
        "total_duration_min": sum(c["duration_min"] for c in CHECKLIST),
        "checklist": CHECKLIST,
        "remediation": {
            "owner": DEFAULT_OWNER,
            "planned_window": DEFAULT_PLANNED_WINDOW,
            "deadline": DEFAULT_DEADLINE,
            "closure_rule": DEFAULT_CLOSURE_RULE,
        },
        "results": {},
    }
    for c in CHECKLIST:
        old = existing.get(c["id"], {})
        status = old.get("status") if old else init_status
        protocol["results"][c["id"]] = {
            "status": status,
            "feedback": old.get("feedback") or _build_feedback_defaults(c["id"]),
            "timestamp": old.get("timestamp", ""),
            "owner": REMEDIATION_PLAN[c["id"]]["owner"],
            "due": REMEDIATION_PLAN[c["id"]]["due"],
            "plan": REMEDIATION_PLAN[c["id"]]["plan"],
        }
    PROTOCOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROTOCOL_PATH.write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    return protocol


def report() -> dict:
    """读取验证状态."""
    if not PROTOCOL_PATH.exists():
        return {"error": "未生成验证清单, 先跑 --generate"}
    return json.loads(PROTOCOL_PATH.read_text())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--pending", action="store_true", help="生成默认 pending 状态（可复核前的等待态）")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.generate:
        p = generate_protocol(pending=args.pending)
        print(f"验证清单已生成: {PROTOCOL_PATH}")
        print(f"共 {len(CHECKLIST)} 步, 预计 {p['total_duration_min']} 分钟")
        for c in CHECKLIST:
            print(f"  {c['id']}. {c['step']} ({c['duration_min']}min) — {c['desc']}")
    elif args.report:
        p = report()
        if "error" in p:
            print(p["error"]); return
        done = sum(1 for r in p["results"].values() if r["status"] in {"done", "DONE"})
        deferred = sum(1 for r in p["results"].values() if r["status"] == "deferred")
        pending = sum(1 for r in p["results"].values() if r["status"] == "pending")
        print(f"验证进度: DONE={done}, deferred={deferred}, pending={pending}, 总计={len(CHECKLIST)}")
        for c in CHECKLIST:
            r = p["results"].get(c["id"], {})
            if r.get("status") in {"done", "DONE"}:
                status = "✅"
            elif r.get("status") == "deferred":
                status = "🕒"
            else:
                status = "🔲"
            print(f"  {status} {c['id']}. {c['step']}: {r.get('feedback', '待验证')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
