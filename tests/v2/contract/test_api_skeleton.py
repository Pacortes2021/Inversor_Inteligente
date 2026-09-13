from __future__ import annotations

import sqlite3

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


def test_sqlite_linked_version_is_explicit_and_wal_gate_is_honest() -> None:
    version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    assert len(version) == 3
    assert has_wal_reset_fix() is (version >= (3, 53, 0))
