"""项目地图只读采集层 — 聚合 4 套真相源, 不改任何状态 (read-only).

每个 collect_* 返回纯 dict/list, 失败时返回 {available: False, error: ...} 而非抛栈 (§1.5 不静默吃错误,
但调用方 doctor 不崩)。真相源:
- project_architecture.yaml  → 模块/配置/数据契约 (path/owner/required_files)
- m0_gate_plan.load_gates()   → M0 gate 顺序契约 (planner, 不执行 gate)
- moth assert --repo .         → 声称-实况弹仓 (drift)
- project_architecture_audit  → 架构契约审计 status (block/warn)
- read-only DB                 → 关键计数 + 辽宁年度分布 (D0 样本量透明)
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARCH_YAML = ROOT / "backend" / "config" / "project_architecture.yaml"
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
GATE_PLAN = ROOT / "scripts" / "tools" / "audit" / "m0_gate_plan.py"
ARCH_AUDIT = ROOT / "scripts" / "tools" / "audit" / "project_architecture_audit.py"


def _load_yaml(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


_CONTRACT_SECTIONS = (
    ("module", "module_contracts"),
    ("config", "config_contracts"),
    ("data", "data_zones"),
)


def _module_row(category: str, name: str, spec: dict) -> dict[str, Any]:
    """单条契约 → 行. required_files 是 ROOT-相对路径 (非 path 子文件)."""
    path = spec.get("path")
    exists = (ROOT / path).exists() if path else None
    required = spec.get("required_files") or []
    missing = [f for f in required if not (ROOT / f).exists()]
    return {
        "category": category,
        "name": name,
        "path": path,
        "owner": spec.get("owner_module") or spec.get("owner") or "",
        "exists": exists,
        "missing_required": missing,
    }


def collect_modules() -> list[dict[str, Any]]:
    """project_architecture.yaml 的 module/config/data 契约 → 每条 {path 存在? 必需文件齐?}."""
    arch = _load_yaml(ARCH_YAML)
    return [
        _module_row(category, name, spec)
        for category, key in _CONTRACT_SECTIONS
        for name, spec in (arch.get(key) or {}).items()
    ]


def collect_gates() -> list[dict[str, Any]]:
    """复用 m0_gate_plan.load_gates() (planner, 不执行); 失败返回空 + error 占位."""
    try:
        spec = importlib.util.spec_from_file_location("m0_gate_plan_map", GATE_PLAN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return [{
            "order": g.get("order"),
            "name": g.get("name"),
            "expected": g.get("expected_current_status", ""),
            "failure_action": g.get("failure_action", ""),
            "command": g.get("command", ""),
        } for g in module.load_gates()]
    except Exception as exc:  # gate 契约自身坏掉也要可见, 不静默
        return [{"order": None, "name": "<load_gates 失败>",
                 "error": f"{type(exc).__name__}: {exc}"}]


def collect_drift() -> dict[str, Any]:
    """shell moth assert --repo . → {verdict, pass, fail, error}. moth 未装 → available False."""
    try:
        out = _run(["moth", "assert", "--repo", "."])
    except FileNotFoundError:
        return {"available": False, "error": "moth 未安装"}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    text = (out.stdout or "") + (out.stderr or "")
    m = re.search(r"verdict=(\w+)\s+pass=(\d+)\s+fail=(\d+)\s+error=(\d+)", text)
    if not m:
        return {"available": True, "verdict": "?", "raw_tail": text[-200:]}
    return {
        "available": True,
        "verdict": m.group(1),
        "pass": int(m.group(2)),
        "fail": int(m.group(3)),
        "error": int(m.group(4)),
    }


def collect_arch_audit() -> dict[str, Any]:
    """shell project_architecture_audit.py (stdout JSON) → {status, block, warn}."""
    try:
        out = _run(["python3", str(ARCH_AUDIT.relative_to(ROOT))])
        data = json.loads(out.stdout)
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    summary = data.get("summary", {})
    return {
        "available": True,
        "status": data.get("status"),
        "block": summary.get("block_findings", 0),
        "warn": summary.get("warn_findings", 0),
    }


_STAT_QUERIES = {
    "exam_questions": "SELECT count(*) FROM exam_questions",
    "exam_liaoning": "SELECT count(*) FROM exam_questions WHERE province LIKE '辽宁%'",
    "exam_eol": "SELECT count(*) FROM exam_questions WHERE source_repo LIKE 'eol_xgkii%'",
    "exam_local_pdf": "SELECT count(*) FROM exam_questions WHERE source_repo = 'local_pdf'",
    "question_bank": "SELECT count(*) FROM question_bank",
    "nodes": "SELECT count(*) FROM nodes",
    "edges": "SELECT count(*) FROM edges",
    "question_tags": "SELECT count(*) FROM question_tags",
    "tag_dictionary": "SELECT count(*) FROM tag_dictionary",
    "units": "SELECT count(*) FROM units",
}


def collect_stats() -> dict[str, Any]:
    """read-only DB 关键计数 + 辽宁年度分布 (守 D0: 样本量透明)."""
    if not DB_PATH.exists():
        return {"available": False, "error": "DB 未构建 (先跑 scripts/init_db.py)"}
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        stats: dict[str, Any] = {"available": True}
        for key, sql in _STAT_QUERIES.items():
            stats[key] = con.execute(sql).fetchone()[0]
        rows = con.execute(
            "SELECT year, count(*) FROM exam_questions WHERE province LIKE '辽宁%' "
            "AND year IS NOT NULL GROUP BY year ORDER BY year"
        ).fetchall()
        stats["liaoning_by_year"] = {int(y): int(n) for y, n in rows}
        return stats
    finally:
        con.close()
