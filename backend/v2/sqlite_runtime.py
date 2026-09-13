"""Linked SQLite capability check kept separate from future persistence."""

from __future__ import annotations

import sqlite3


# SQLite 3.53.0 fixed the WAL-reset corruption bug. M0 does not enable WAL;
# M1 must use a runtime at or above this floor before doing so.
WAL_RESET_FIX_VERSION = (3, 53, 0)


def linked_version() -> tuple[int, int, int]:
    parts = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    if len(parts) != 3:
        raise RuntimeError(f"unexpected SQLite version: {sqlite3.sqlite_version}")
    return parts


def has_wal_reset_fix() -> bool:
    return linked_version() >= WAL_RESET_FIX_VERSION
