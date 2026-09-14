"""Read-only immutable snapshot replay endpoint."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ..adapters.persistence import SnapshotRepository
from ..domain import DatasetSnapshot, Fact, SelectionDecision
from ..domain.common import CanonicalModel


class SnapshotDetail(CanonicalModel):
    snapshot: DatasetSnapshot
    facts: list[Fact]
    selection_decisions: list[SelectionDecision]


def install_snapshot_routes(app: FastAPI, repository: SnapshotRepository | None) -> None:
    @app.get("/api/v2/snapshots/{snapshot_id}", response_model=SnapshotDetail)
    def get_snapshot(snapshot_id: str) -> SnapshotDetail:
        if repository is None:
            raise HTTPException(status_code=503, detail="v2 data directory is not configured")
        snapshot = repository.get(snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="snapshot not found")
        return SnapshotDetail(
            snapshot=snapshot,
            facts=repository.facts(snapshot_id),
            selectionDecisions=repository.decisions(snapshot_id),
        )
