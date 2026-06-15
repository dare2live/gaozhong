"""共享 DB helper for API routes (架构 §0 Rule 1: API 是薄壳)."""
from __future__ import annotations

import fcntl
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
DB_WRITE_LOCK_PATH = ROOT / "data" / "db" / "gaozhong.duckdb.write.lock"


def db_ro() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB 不存在, 先跑 python3 scripts/init_db.py — {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=True)


@contextmanager
def db_write(timeout_s: float = 10.0, poll_s: float = 0.1) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open a serialized runtime write connection.

    DuckDB has a single-writer constraint. Runtime POST/write routes should use
    this helper instead of opening independent write connections.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB 不存在, 先跑 python3 scripts/init_db.py — {DB_PATH}")
    DB_WRITE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    with DB_WRITE_LOCK_PATH.open("w", encoding="utf-8") as lock_fh:
        while True:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"DuckDB write lock timeout: {DB_WRITE_LOCK_PATH}")
                time.sleep(poll_s)
        con = duckdb.connect(str(DB_PATH), read_only=False)
        try:
            yield con
        finally:
            con.close()
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def rows_to_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]
