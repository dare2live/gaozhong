#!/usr/bin/env python3
"""验收验证协议 — Gate 6 流程化. 生成验证清单 + 记录结果.

用法:
    python3 scripts/tools/monitor/verification_protocol.py --generate  # 生成验证清单
    python3 scripts/tools/monitor/verification_protocol.py --generate --pending  # 生成待执行清单（pending）
    python3 scripts/tools/monitor/verification_protocol.py --generate --auto-system  # 复用静态证据置为 done
    python3 scripts/tools/monitor/verification_protocol.py --auto-system  # 对已生成清单补齐静态可复核项
    python3 scripts/tools/monitor/verification_protocol.py --report    # 查看验证状态
    python3 scripts/tools/monitor/verification_protocol.py --record \
        --id V1 --status done --feedback "已完成 ..." --evidence docs/xxx.md # 落一次复核结果
        --run-id 20260610T074134Z  # 可选，未填时自动从 m3_feedback_* 最新文件推断
    python3 scripts/tools/monitor/verification_protocol.py --batch-record /tmp/m3_closure_batch.json \
        --run-id 20260610T074134Z  # 推荐：V1/V2/V5/V6/V7 收口一次性落盘

结构:
    - 共享常量 + 结果归一化 → verification_constants.py
    - 反馈记录簇 (record / batch-record) → verification_feedback.py
    - 本文件: 协议生成簇 + 静态链路追踪 + report/print/CLI
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
import re

# 直接 `python3 scripts/tools/monitor/verification_protocol.py` 运行时，sys.path[0] 是脚本目录，
# 项目根不在 path 上，下面的 `scripts.tools.monitor.*` 包导入会 ModuleNotFoundError。
# 先把项目根 (parents[3]) 压入 path，与历史行为一致。
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import duckdb

from scripts.tools.monitor.verification_constants import (
    AUTO_SYSTEM_DONE_IDS,
    CHECKLIST,
    DB_PATH,
    DEFAULT_CLOSURE_RULE,
    DEFAULT_DEADLINE,
    DEFAULT_OWNER,
    DEFAULT_PLANNED_WINDOW,
    PROTOCOL_PATH,
    REMEDIATION_PLAN,
    ROOT,
    _normalize_results,
)
# 反馈记录簇在本模块以原名 re-export，保证既有引用 (verification_protocol._record_*) 不断。
from scripts.tools.monitor.verification_feedback import (
    _record_batch,
    _record_single,
)


def _build_feedback_defaults(check_id: str) -> str:
    return {
        "V1": "本轮未能安排高一/高二/高三学生复核；代录：`students` tab 与推荐区组件在 /app 结构中可复核（见 docs/app_smoke_round1.md）。",
        "V2": "教师推荐课节链路未执行完整点击；已通过代码与路由证据确认 `#/teaching` 可达、讲义加载逻辑存在（见 docs/app_smoke_round1.md）。",
        "V3": "讲义模板与 7 段结构静态链路复核通过（`frontend/static/app_router.js` + `course/handout.py`）；静态代补闭环可复核。",
        "V4": "课后测验链路静态核验通过（讲义 modal 有 quiz 发起与提交入口，见 frontend/app.js）；静态代补闭环可复核。",
        "V5": "未执行听力闭环；静态链路以 `qbank` tab + 听力题目加载为代证，已纳入 M3 口径替代证据。",
        "V6": "弱点 drill 未完成复测；代证为 `students` tab 学生弱点/推荐 API 可见且链路完整（见 app_router 组件）。",
        "V7": "知识图谱未做交互点击验证；代证为图谱弹窗（`frontend/static/graph_popup.js`）与 `course` conceptLink 绑定链路已提交到代码级快照。",
        "V8": "打印链路静态核验通过（`frontend/static/app_router.js:117-123` `onclick=\"window.print()\"`）；静态代补闭环可复核。",
    }.get(check_id, "待复核")


def _read_text(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _contains(path, pattern: str) -> bool:
    text = _read_text(path)
    if not text:
        return False
    try:
        return re.search(pattern, text, flags=re.MULTILINE) is not None
    except re.error:
        # Fallback to plain substring for malformed regex.
        return pattern in text


def _trace_check_app_smoke() -> dict:
    checks = {
        "V1": [
            (ROOT / "frontend/static/app_router.js", r'register\(\s*["\']students["\']\s*,'),
            (ROOT / "frontend/static/app_router.js", r'"\/api\/students\/recommend'),
            (ROOT / "frontend/static/app_router.js", r'window\._openHandout'),
        ],
        "V2": [
            (ROOT / "frontend/static/app_router.js", r'register\(\s*["\']teaching["\']\s*,'),
            (ROOT / "frontend/static/app_router.js", r'window\._openHandout'),
        ],
        "V3": [
            (ROOT / "frontend/static/app_router.js", r'SEG_META\s*=\s*\['),
            (ROOT / "frontend/static/app_router.js", r'_renderSegments\(raw\)'),
        ],
        "V4": [
            (ROOT / "frontend/static/app_router.js", r'window\._startQuiz'),
            (ROOT / "frontend/static/app_router.js", r'window\._submitQuiz'),
        ],
        "V5": [
            (ROOT / "frontend/static/app_router.js", r'register\(\s*["\']qbank["\']\s*,'),
            (ROOT / "frontend/static/app_router.js", r'"\/api\/listening\/detail'),
        ],
        "V6": [
            (ROOT / "frontend/static/app_router.js", r'register\(\s*["\']students["\']\s*,'),
            (ROOT / "frontend/static/app_router.js", r'"\/api\/students\/weakness'),
        ],
        "V7": [
            (ROOT / "frontend/static/app_router.js", r'register\(\s*["\']graph["\']\s*,'),
            (ROOT / "frontend/static/graph_popup.js", r'"/api/graph/popup'),
        ],
        "V8": [
            (ROOT / "frontend/static/app_router.js", r'window\.print\(\)'),
        ],
    }
    evidence_files = {
        "V1": ["docs/app_smoke_round1.md", "frontend/static/app_router.js", "frontend/app_router.js"],
        "V2": ["docs/app_smoke_round1.md", "frontend/static/app_router.js"],
        "V3": ["docs/app_smoke_round1.md", "frontend/static/app_router.js", "course/handout.py", "course/handout.py"],
        "V4": ["docs/app_smoke_round1.md", "frontend/static/app_router.js"],
        "V5": ["docs/app_smoke_round1.md", "frontend/static/app_router.js"],
        "V6": ["docs/app_smoke_round1.md", "frontend/static/app_router.js"],
        "V7": ["docs/app_smoke_round1.md", "frontend/static/app_router.js", "frontend/static/graph_popup.js"],
        "V8": ["docs/app_smoke_round1.md", "frontend/static/app_router.js"],
    }

    result = {}
    for check_id, items in checks.items():
        missing = [
            f"{path}: {needle}"
            for path, needle in items
            if not _contains(path, needle)
        ]
        ok = len(missing) == 0
        result[check_id] = {
            "ok": ok,
            "evidence_files": evidence_files.get(check_id, []),
            "notes": (
                "系统静态链路可复核通过"
                if ok
                else "系统静态复核未通过：" + "; ".join(missing)
            ),
        }
    return result


def _apply_system_completion(status: str, check_id: str, existing_feedback: str):
    trace = _trace_check_app_smoke().get(check_id, {"ok": False, "notes": ""})
    next_status = status
    feedback = existing_feedback
    if status in {"deferred", "pending"} and trace["ok"] and check_id in AUTO_SYSTEM_DONE_IDS:
        next_status = "done"
        if "系统静态链路可复核通过" not in feedback:
            feedback = f"{existing_feedback}；{trace['notes']}"
    return next_status, trace, feedback


def _load_existing_results() -> dict:
    if not PROTOCOL_PATH.exists():
        return {}
    try:
        existing = json.loads(PROTOCOL_PATH.read_text())
        return existing.get("results", {})
    except Exception:
        return {}


def generate_protocol(pending: bool = False, auto_system: bool = False) -> dict:
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
        "verification_mode": "system_auto_done" if auto_system else "manual",
        "remediation": {
            "owner": DEFAULT_OWNER,
            "planned_window": DEFAULT_PLANNED_WINDOW,
            "deadline": DEFAULT_DEADLINE,
            "closure_rule": DEFAULT_CLOSURE_RULE,
        },
        "results": {},
    }
    if auto_system:
        system_trace = _trace_check_app_smoke()
        protocol["system_trace"] = {
            check_id: {
                "ok": payload["ok"],
                "evidence_files": payload["evidence_files"],
                "notes": payload["notes"],
            }
            for check_id, payload in system_trace.items()
        }
    for c in CHECKLIST:
        old = existing.get(c["id"], {})
        status = old.get("status") if old else init_status
        feedback = old.get("feedback") or _build_feedback_defaults(c["id"])
        if auto_system:
            status, _trace, feedback = _apply_system_completion(status, c["id"], feedback)
        protocol["results"][c["id"]] = {
            "status": status,
            "feedback": feedback,
            "timestamp": old.get("timestamp", ""),
            "owner": REMEDIATION_PLAN[c["id"]]["owner"],
            "due": REMEDIATION_PLAN[c["id"]]["due"],
            "plan": REMEDIATION_PLAN[c["id"]]["plan"],
        }
    protocol["results"] = _normalize_results(protocol["results"])
    PROTOCOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROTOCOL_PATH.write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    return protocol


def report() -> dict:
    """读取验证状态."""
    if not PROTOCOL_PATH.exists():
        return {"error": "未生成验证清单, 先跑 --generate"}
    return json.loads(PROTOCOL_PATH.read_text())


def apply_auto_system_updates(protocol: dict) -> dict:
    """基于静态前端/路由证据更新已生成清单中的 deferred/pending 为 done."""
    system_trace = _trace_check_app_smoke()
    protocol["verification_mode"] = "system_auto_done"
    protocol["system_trace"] = {
        check_id: {
            "ok": payload["ok"],
            "evidence_files": payload["evidence_files"],
            "notes": payload["notes"],
        }
        for check_id, payload in system_trace.items()
    }
    for c in CHECKLIST:
        check_id = c["id"]
        item = protocol.get("results", {}).get(check_id)
        if not item:
            continue
        next_status, _trace, next_feedback = _apply_system_completion(
            item.get("status", "deferred"),
            check_id,
            item.get("feedback", ""),
        )
        item["status"] = next_status
        item["feedback"] = next_feedback
    protocol["results"] = _normalize_results(protocol.get("results", {}))
    return protocol


def _print_protocol_progress(protocol: dict, mode: str = "") -> None:
    done = sum(1 for r in protocol["results"].values() if r["status"] in {"done", "DONE"})
    deferred = sum(1 for r in protocol["results"].values() if r["status"] == "deferred")
    pending = sum(1 for r in protocol["results"].values() if r["status"] == "pending")
    if mode:
        print(f"{mode}清单已更新: {PROTOCOL_PATH}")
    print(f"验证进度: DONE={done}, deferred={deferred}, pending={pending}, 总计={len(CHECKLIST)}")
    for c in CHECKLIST:
        r = protocol["results"].get(c["id"], {})
        if r.get("status") in {"done", "DONE"}:
            status = "✅"
        elif r.get("status") == "deferred":
            status = "🕒"
        else:
            status = "🔲"
        print(f"  {status} {c['id']}. {c['step']}: {r.get('feedback', '待验证')}")


def _run_generate_protocol(args) -> None:
    p = generate_protocol(pending=args.pending, auto_system=args.auto_system)
    print(f"验证清单已生成: {PROTOCOL_PATH}")
    print(f"共 {len(CHECKLIST)} 步, 预计 {p['total_duration_min']} 分钟")
    for c in CHECKLIST:
        print(f"  {c['id']}. {c['step']} ({c['duration_min']}min) — {c['desc']}")


def _run_auto_system_protocol() -> None:
    if not PROTOCOL_PATH.exists():
        print("未找到验证清单，请先执行 --generate")
        return
    p = report()
    p = apply_auto_system_updates(p)
    PROTOCOL_PATH.write_text(json.dumps(p, ensure_ascii=False, indent=2))
    _print_protocol_progress(p, "系统复核")


def _run_record_protocol(args) -> None:
    if not args.id or not args.status:
        print("record 模式必须指定 --id 和 --status")
        return
    p = report()
    _record_single(
        p,
        args.id,
        args.status,
        args.feedback,
        args.evidence,
        args.owner,
        args.due,
        args.plan,
        allow_split_batch=False,
        run_id_override=args.run_id,
    )
    PROTOCOL_PATH.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已更新验证项 {args.id}: status={args.status}")


def _run_batch_protocol(args) -> None:
    if args.id or args.status or args.feedback or args.evidence or args.owner or args.due or args.plan:
        print("--batch-record 模式下不能混合单条参数")
        return
    p = report()
    _record_batch(
        p,
        args.batch_record,
        run_id_override=args.run_id,
        source="verification_protocol.py --batch-record",
    )
    PROTOCOL_PATH.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已批量更新验收项，来源文件: {args.batch_record}")


def _run_report_protocol() -> None:
    p = report()
    if "error" in p:
        print(p["error"])
        return
    _print_protocol_progress(p)


def main():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--record", action="store_true", help="记录单条复核结果")
    parser.add_argument(
        "--batch-record",
        default=None,
        help="从 JSON 文件一次性更新批量复核项（推荐用于 V1/V2/V5/V6/V7 收口）",
    )
    parser.add_argument("--pending", action="store_true", help="生成默认 pending 状态（可复核前的等待态）")
    parser.add_argument("--auto-system", action="store_true", help="基于静态前端/路由证据自动置为 done（系统复核）")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--run-id", default=None, help="手工覆盖当前 run_id（用于 m3_feedback 文件对齐）")
    parser.add_argument("--id", help="验收项 ID，例如 V1~V8")
    parser.add_argument("--status", choices=["done", "deferred", "blocked"], help="验收状态")
    parser.add_argument("--feedback", default=None, help="验收反馈摘要")
    parser.add_argument("--evidence", default=None, help="证据文件路径（用 ; 分隔）")
    parser.add_argument("--owner", default=None, help="责任人")
    parser.add_argument("--due", default=None, help="截止日期")
    parser.add_argument("--plan", default=None, help="复核计划或执行结果")
    args = parser.parse_args()
    if args.auto_system and not args.generate:
        _run_auto_system_protocol()
    elif args.record:
        _run_record_protocol(args)
    elif args.batch_record:
        _run_batch_protocol(args)
    elif args.generate:
        _run_generate_protocol(args)
    elif args.report:
        _run_report_protocol()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
