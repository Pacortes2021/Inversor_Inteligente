"""Minimal M0 FastAPI assembly; no provider, persistence or financial engine."""

from __future__ import annotations

import sqlite3
import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from . import __version__
from .api.openapi import install_canonical_openapi
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
        description="Contract-only M0 skeleton. No financial engine is active.",
    )

    @app.get("/api/v2/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ready",
            build=__version__,
            schema_version="m0-v1",
            sqlite_version=sqlite3.sqlite_version,
            sqlite_wal_reset_fix=has_wal_reset_fix(),
            data_directory_configured=data_dir is not None,
        )

    install_canonical_openapi(app)
    return app


configured_data_dir = os.environ.get("INVERSOR_DATA_DIR")
app = create_app(Path(configured_data_dir) if configured_data_dir else None)
