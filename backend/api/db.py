"""共享 DB helper for API routes (架构 §0 Rule 1: API 是薄壳)."""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"


def db_ro() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB 不存在, 先跑 python3 scripts/init_db.py — {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=True)


def rows_to_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]
