#!/usr/bin/env python3
"""验收验证协议 — 反馈记录簇 (record / batch-record).

从 verification_protocol.py 抽出的反馈落盘逻辑：单条/批量记录复核结果，
同步 m3_feedback_<run_id>.json，并执行闭环收口守卫。
被 verification_protocol.py import；自身不带 CLI。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from scripts.tools.monitor.verification_constants import (
    CLOSURE_BATCH_IDS,
    M3_FEEDBACK_TEMPLATE,
    REMEDIATION_PLAN,
    ROOT,
    RUN_ID_GLOB,
    _normalize_results,
)


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
