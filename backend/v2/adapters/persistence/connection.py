"""SQLite connection policy and numbered migration runner."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ...sqlite_runtime import has_wal_reset_fix


MIGRATIONS = Path(__file__).with_name("migrations")


class Database:
    def __init__(self, path: Path, *, busy_timeout_ms: int = 5_000) -> None:
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=self.busy_timeout_ms / 1000)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_ms)}")
        # The locked Python runtime is affected by WAL-reset. Keep rollback
        # journal until the explicit runtime gate becomes true.
        connection.execute(f"PRAGMA journal_mode = {'WAL' if has_wal_reset_fix() else 'DELETE'}")
        return connection

    @contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> list[int]:
        applied_now: list[int] = []
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            version = int(path.name.split("_", 1)[0])
            with self.connect() as connection:
                present = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
                ).fetchone()
                if present:
                    continue
                script = path.read_text(encoding="utf-8")
                safe_name = path.name.replace("'", "''")
                connection.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + script
                    + f"\nINSERT INTO schema_migrations(version, name) VALUES ({version}, '{safe_name}');\n"
                    + "COMMIT;"
                )
                applied_now.append(version)
        return applied_now

    def applied_versions(self) -> list[int]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        return [int(row["version"]) for row in rows]
