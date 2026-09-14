"""Read-only provider capability evidence report."""

from __future__ import annotations

from fastapi import FastAPI

from ..application.capabilities import CapabilityReport, provider_capability_report


def install_capability_routes(app: FastAPI) -> None:
    @app.get("/api/v2/capabilities", response_model=CapabilityReport)
    def get_capabilities() -> CapabilityReport:
        return provider_capability_report()
