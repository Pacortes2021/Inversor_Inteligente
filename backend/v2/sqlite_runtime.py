"""Linked SQLite capability check kept separate from future persistence."""

from __future__ import annotations

import sqlite3


# The WAL-reset corruption fix shipped in 3.51.3 and was backported to
# 3.50.7 and 3.44.6. M0 does not enable WAL on an affected branch.
WAL_RESET_FIX_VERSION = (3, 51, 3)
WAL_RESET_BACKPORTS = {(3, 50): 7, (3, 44): 6}


def linked_version() -> tuple[int, int, int]:
    parts = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    if len(parts) != 3:
        raise RuntimeError(f"unexpected SQLite version: {sqlite3.sqlite_version}")
    return parts


def has_wal_reset_fix(version: tuple[int, int, int] | None = None) -> bool:
    version = linked_version() if version is None else version
    if version >= WAL_RESET_FIX_VERSION:
        return True
    required_patch = WAL_RESET_BACKPORTS.get(version[:2])
    return required_patch is not None and version[2] >= required_patch
