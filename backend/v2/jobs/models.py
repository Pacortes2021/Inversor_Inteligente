"""Contracts for persistent background work."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..domain.common import CanonicalModel, Identifier, utc_datetime


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RefreshRequest(CanonicalModel):
    provider: Identifier
    capability: Identifier
    resource_key: Identifier
    parser_version: Identifier
    parameters: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=20)


class Job(CanonicalModel):
    job_id: Identifier
    idempotency_key: Identifier
    kind: Identifier
    request: RefreshRequest
    status: JobStatus
    attempt: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    progress: str
    lease_owner: str | None
    lease_expires_at: datetime | None
    next_attempt_at: datetime
    cancel_requested: bool
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("lease_expires_at", "next_attempt_at", "created_at", "updated_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else utc_datetime(value)
