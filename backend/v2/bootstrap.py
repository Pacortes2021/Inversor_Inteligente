"""FastAPI assembly for the isolated v2 data core."""

from __future__ import annotations

import sqlite3
import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from . import __version__
from .api.openapi import install_canonical_openapi
from .api.facts import install_fact_routes
from .api.snapshots import install_snapshot_routes
from .adapters.persistence import Database, FactRepository, SnapshotRepository
from .sqlite_runtime import has_wal_reset_fix


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    build: str
    schema_version: str
    sqlite_version: str
    sqlite_wal_reset_fix: bool
    data_directory_configured: bool


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="Inversor Inteligente API v2",
        version=__version__,
        description="Verifiable local data core. No financial engine is active.",
    )
    database = Database(data_dir / "v2.sqlite3") if data_dir is not None else None
    if database is not None:
        database.migrate()
    fact_repository = FactRepository(database) if database is not None else None
    snapshot_repository = SnapshotRepository(database) if database is not None else None

    @app.get("/api/v2/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ready",
            build=__version__,
            schema_version="m1-v1",
            sqlite_version=sqlite3.sqlite_version,
            sqlite_wal_reset_fix=has_wal_reset_fix(),
            data_directory_configured=data_dir is not None,
        )

    install_fact_routes(app, fact_repository)
    install_snapshot_routes(app, snapshot_repository)
    install_canonical_openapi(app)
    return app


configured_data_dir = os.environ.get("INVERSOR_DATA_DIR")
app = create_app(Path(configured_data_dir) if configured_data_dir else None)
