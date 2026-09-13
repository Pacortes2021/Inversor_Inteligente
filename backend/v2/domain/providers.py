"""Typed provider outcomes; empty data and provider failures are distinct."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, Identifier, utc_datetime


T = TypeVar("T")


class ProviderStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


class ProviderError(str, Enum):
    NOT_COVERED = "not_covered"
    NOT_REPORTED = "not_reported"
    RATE_LIMITED = "rate_limited"
    AUTH_REQUIRED = "auth_required"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_PAYLOAD = "invalid_payload"
    SCHEMA_CHANGED = "schema_changed"


class ProviderResult(CanonicalModel, Generic[T]):
    provider: Identifier
    capability: Identifier
    status: ProviderStatus
    data: list[T] = Field(default_factory=list)
    source: Identifier
    fetched_at: datetime
    retry_after_seconds: int | None = Field(default=None, ge=0)
    error: ProviderError | None = None

    @field_validator("fetched_at")
    @classmethod
    def fetched_at_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)

    @model_validator(mode="after")
    def status_and_error_match(self) -> "ProviderResult[T]":
        if self.status == ProviderStatus.SUCCESS and self.error is not None:
            raise ValueError("successful result cannot contain an error")
        if self.status == ProviderStatus.FAILURE and self.error is None:
            raise ValueError("failed result requires an enumerated error")
        if self.status == ProviderStatus.FAILURE and self.data:
            raise ValueError("failed result cannot replace data")
        if self.error == ProviderError.RATE_LIMITED and self.retry_after_seconds is None:
            raise ValueError("rate-limited result requires retryAfterSeconds")
        return self
