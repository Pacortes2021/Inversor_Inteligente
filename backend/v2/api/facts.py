"""Read-only fact and evidence metadata endpoints."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ..adapters.persistence import FactRepository
from ..domain import Document, Fact


def install_fact_routes(app: FastAPI, repository: FactRepository | None) -> None:
    @app.get("/api/v2/facts/{fact_id}", response_model=Fact)
    def get_fact(fact_id: str) -> Fact:
        if repository is None:
            raise HTTPException(status_code=503, detail="v2 data directory is not configured")
        fact = repository.get_fact(fact_id)
        if fact is None:
            raise HTTPException(status_code=404, detail="fact not found")
        return fact

    @app.get("/api/v2/documents/{document_id}", response_model=Document)
    def get_document(document_id: str) -> Document:
        if repository is None:
            raise HTTPException(status_code=503, detail="v2 data directory is not configured")
        document = repository.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="document not found")
        return document
