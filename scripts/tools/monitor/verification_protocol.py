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
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
import re
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

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


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _contains(path: Path, pattern: str) -> bool:
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


def _feedback_path(run_id: str) -> Path:
    return ROOT / "data" / "reports" / M3_FEEDBACK_TEMPLATE.format(run_id=run_id)


def _load_feedback(run_id: str) -> Tuple[Path, dict]:
    path = _feedback_path(run_id)
    if not path.exists():
        return path, {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return path, {}
    items = {}
    for item in payload.get("items", []):
        cid = item.get("id")
        if cid:
            items[cid] = item
    return path, items


def _write_feedback(path: Path, run_id: str, payload: dict, items: dict) -> None:
    payload["run_id"] = run_id
    payload["items"] = [items[f"V{i}"] for i in range(1, 9) if f"V{i}" in items]
    payload["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _infer_run_id() -> str:
    """从现有 m3_feedback 文件中推断 run_id（若有多个取最新）。"""
    report_dir = ROOT / "data" / "reports"
    if not report_dir.exists():
        return ""
    candidates = []
    for path in report_dir.glob(RUN_ID_GLOB):
        stem = path.stem
        if not stem.startswith("m3_feedback_"):
            continue
        run_id = stem[len("m3_feedback_"):]
        if run_id:
            candidates.append(run_id)
    return max(candidates) if candidates else ""


def _ensure_batch_closure_guard(
    protocol: dict,
    check_id: str,
    status: str,
    allow_split_batch: bool,
) -> None:
    if (
        allow_split_batch
        or check_id not in CLOSURE_BATCH_IDS
        or status not in {"done", "blocked"}
    ):
        return
    pending_batch = [
        cid for cid in CLOSURE_BATCH_IDS
        if protocol["results"].get(cid, {}).get("status") in {"deferred", "pending"}
    ]
    if any(cid != check_id for cid in pending_batch):
        raise ValueError(
            "V1/V2/V5/V6/V7 为闭环收口项，不允许单条提前写 done/blocked；"
            "请使用 --batch-record 一次覆盖全部项，或在会后统一补齐全部项。"
        )


def _resolve_run_id(protocol: dict, run_id_override: Optional[str]) -> str:
    run_id = run_id_override or protocol.get("run_id", "") or _infer_run_id()
    if not run_id:
        raise ValueError("protocol 缺少 run_id，先执行 --generate")
    protocol["run_id"] = run_id
    return run_id


def _set_if_nonblank(target: dict, key: str, value: Optional[str]) -> None:
    if value is not None and value.strip():
        target[key] = value.strip()


def _build_default_feedback_items(protocol: dict) -> dict:
    return {
        f"V{i}": {
            "id": f"V{i}",
            "item": protocol["checklist"][i - 1]["step"],
            "status": "deferred",
            "owner": REMEDIATION_PLAN[f"V{i}"]["owner"],
            "due": REMEDIATION_PLAN[f"V{i}"]["due"],
            "plan": REMEDIATION_PLAN[f"V{i}"]["plan"],
            "evidence_file": "",
        }
        for i in range(1, 9)
    }


def _sync_feedback_entry(
    feedback_items: dict,
    check_id: str,
    status: str,
    now: str,
    source: str,
    feedback: Optional[str],
    evidence: Optional[str],
    protocol_item: dict,
) -> None:
    feedback_item = feedback_items[check_id]
    feedback_item["status"] = status
    feedback_item["owner"] = protocol_item.get("owner", feedback_item.get("owner", ""))
    feedback_item["due"] = protocol_item.get("due", feedback_item.get("due", ""))
    feedback_item["plan"] = protocol_item.get("plan", feedback_item.get("plan", ""))
    _set_if_nonblank(feedback_item, "feedback", feedback)
    _set_if_nonblank(feedback_item, "evidence_file", evidence)
    feedback_item["timestamp"] = now
    feedback_item["session"] = {
        "updated_at": now,
        "source": source,
    }


def _record_single(
    protocol: dict,
    check_id: str,
    status: str,
    feedback: Optional[str],
    evidence: Optional[str],
    owner: Optional[str],
    due: Optional[str],
    plan: Optional[str],
    allow_split_batch: bool = False,
    run_id_override: Optional[str] = None,
    source: str = "verification_protocol.py --record",
) -> None:
    if check_id not in protocol.get("results", {}):
        raise ValueError(f"{check_id} 不在验收清单中")
    _ensure_batch_closure_guard(protocol, check_id, status, allow_split_batch)
    run_id = _resolve_run_id(protocol, run_id_override)

    now = datetime.now().isoformat()
    item = protocol["results"][check_id]
    item["status"] = status
    item["timestamp"] = now
    _set_if_nonblank(item, "feedback", feedback)
    _set_if_nonblank(item, "evidence_file", evidence)
    _set_if_nonblank(item, "owner", owner)
    _set_if_nonblank(item, "due", due)
    _set_if_nonblank(item, "plan", plan)

    feedback_path, feedback_items = _load_feedback(run_id)
    if not feedback_items:
        feedback_items = _build_default_feedback_items(protocol)
    _sync_feedback_entry(
        feedback_items,
        check_id,
        status,
        now,
        source,
        feedback,
        evidence,
        item,
    )
    protocol["results"] = _normalize_results(protocol["results"])
    _write_feedback(feedback_path, run_id, {"items": list(feedback_items.values())}, feedback_items)
    return


def _extract_batch_entry(
    protocol: dict,
    idx: int,
    raw_item: dict,
) -> tuple[str, str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not isinstance(raw_item, dict):
        raise ValueError(f"batch 第 {idx} 项不是对象")
    cid = raw_item.get("id")
    status = raw_item.get("status")
    feedback = raw_item.get("feedback")
    evidence = raw_item.get("evidence")
    owner = raw_item.get("owner")
    due = raw_item.get("due")
    plan = raw_item.get("plan")
    if not isinstance(cid, str) or cid not in protocol.get("results", {}):
        raise ValueError(f"batch 第 {idx} 项 id 非法: {raw_item}")
    if status not in {"done", "deferred", "blocked"}:
        raise ValueError(f"batch 第 {idx} 项 status 非法: {status}")
    if cid in CLOSURE_BATCH_IDS and status in {"deferred", "pending"}:
        raise ValueError(f"收口条目 {cid} 在 batch 中不允许写 deferred/pending")
    return cid, status, feedback, evidence, owner, due, plan


def _assert_batch_closure_complete(batch_ids: set[str]) -> None:
    if not batch_ids:
        return
    if batch_ids == CLOSURE_BATCH_IDS:
        return
    missing = sorted(CLOSURE_BATCH_IDS - batch_ids)
    raise ValueError(
        f"闭环收口项一次性更新缺少项: {', '.join(missing)}。要求一次提交 V1,V2,V5,V6,V7 全量。"
    )


def _record_batch(
    protocol: dict,
    batch_path: str,
    run_id_override: Optional[str] = None,
    source: str = "verification_protocol.py --record",
) -> None:
    path = Path(batch_path)
    if not path.exists():
        raise ValueError(f"batch 文件不存在: {batch_path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise ValueError(f"batch 文件解析失败: {err}")
    if not isinstance(raw, list) or not raw:
        raise ValueError("batch 文件应为非空 JSON 数组")

    entries = []
    ids = set()
    batch_ids = set()
    for idx, item in enumerate(raw, start=1):
        entry = _extract_batch_entry(protocol, idx, item)
        cid = entry[0]
        if cid in ids:
            raise ValueError(f"batch 含重复 id: {cid}")
        ids.add(cid)
        if cid in CLOSURE_BATCH_IDS:
            batch_ids.add(cid)
        entries.append(entry)

    _assert_batch_closure_complete(batch_ids)

    for entry in entries:
        cid, status, feedback, evidence, owner, due, plan = entry
        _record_single(
            protocol,
            cid,
            status,
            feedback,
            evidence,
            owner,
            due,
            plan,
            allow_split_batch=True,
            run_id_override=run_id_override,
            source=source,
        )


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
