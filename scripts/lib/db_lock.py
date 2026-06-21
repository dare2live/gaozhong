"""DuckDB 只读连接锁容错 (坑15 流程根治, 共享单点; Rule5 ≥2处复用抽common).

DuckDB 单写者: init_db 重建持写锁时, 校验脚本读连接撞锁报 IOException。那不是"数据错了",
是"DB 正被重建"(瞬时运行态) → 重试自愈, 仍锁则抛 DbLocked, 由调用方返回 exit 3(延后,
stop_gate 视为非阻断, 区别 1=真失败)。data_accuracy_check + junior_accuracy_check 共用此单点。
"""
from __future__ import annotations

import time

import duckdb


class DbLocked(Exception):
    """DB 被其它写连接占用 (疑 init_db 重建中) — 瞬时运行态, 非数据错误."""


def connect_readonly_with_retry(db_path, attempts: int = 4, wait_s: float = 2.0):
    """读连接; 锁冲突重试(瞬时锁自愈), 仍锁抛 DbLocked。其它异常原样抛(只容锁冲突)."""
    last = None
    for _ in range(attempts):
        try:
            return duckdb.connect(str(db_path), read_only=True)
        except Exception as e:  # noqa: BLE001 — 仅锁冲突重试, 其它原样抛
            if "lock" not in str(e).lower():
                raise
            last = e
            time.sleep(wait_s)
    raise DbLocked(str(last))
