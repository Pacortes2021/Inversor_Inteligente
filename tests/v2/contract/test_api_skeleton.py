from __future__ import annotations

import sqlite3
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.v2.bootstrap import create_app
from backend.v2.sqlite_runtime import has_wal_reset_fix


def test_health_and_openapi_are_typed(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.get("/api/v2/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["data_directory_configured"] is True
    assert payload["sqlite_version"] == sqlite3.sqlite_version
    assert payload["sqlite_wal_reset_fix"] is has_wal_reset_fix()

    openapi = client.get("/openapi.json").json()
    assert openapi["info"]["title"] == "Inversor Inteligente API v2"
    assert "/api/v2/health" in openapi["paths"]
    assert "fact-model" in openapi["components"]["schemas"]
    checked_in = json.loads(Path("docs/rework/contracts/openapi.json").read_text(encoding="utf-8"))
    assert openapi == checked_in


def test_sqlite_linked_version_is_explicit_and_wal_gate_is_honest() -> None:
    version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    assert len(version) == 3
    expected = (
        version >= (3, 51, 3)
        or (version[:2] == (3, 50) and version[2] >= 7)
        or (version[:2] == (3, 44) and version[2] >= 6)
    )
    assert has_wal_reset_fix() is expected


def test_sqlite_wal_fix_recognises_official_release_and_backports() -> None:
    assert has_wal_reset_fix((3, 51, 2)) is False
    assert has_wal_reset_fix((3, 51, 3)) is True
    assert has_wal_reset_fix((3, 50, 6)) is False
    assert has_wal_reset_fix((3, 50, 7)) is True
    assert has_wal_reset_fix((3, 44, 5)) is False
    assert has_wal_reset_fix((3, 44, 6)) is True
    assert has_wal_reset_fix((3, 49, 9)) is False
    assert has_wal_reset_fix((3, 52, 0)) is True
