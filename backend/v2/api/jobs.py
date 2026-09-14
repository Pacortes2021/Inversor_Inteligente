"""Explicit refresh commands and read-only job status endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Response, status

from ..jobs import Job, JobRepository, RefreshRequest


def install_job_routes(app: FastAPI, repository: JobRepository | None) -> None:
    @app.post("/api/v2/refreshes", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
    def create_refresh(
        request: RefreshRequest,
        response: Response,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=160),
    ) -> Job:
        if repository is None:
            raise HTTPException(status_code=503, detail="v2 data directory is not configured")
        try:
            job = repository.enqueue(idempotency_key, request, now=datetime.now(timezone.utc))
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        response.headers["Location"] = f"/api/v2/jobs/{job.job_id}"
        return job

    @app.get("/api/v2/jobs/{job_id}", response_model=Job)
    def get_job(job_id: str) -> Job:
        if repository is None:
            raise HTTPException(status_code=503, detail="v2 data directory is not configured")
        job = repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.post("/api/v2/jobs/{job_id}/cancel", response_model=Job)
    def cancel_job(job_id: str) -> Job:
        if repository is None:
            raise HTTPException(status_code=503, detail="v2 data directory is not configured")
        job = repository.cancel(job_id, now=datetime.now(timezone.utc))
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job
