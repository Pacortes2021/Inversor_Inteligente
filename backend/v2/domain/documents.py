"""Immutable source-document metadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, HttpUrl, field_validator

from .common import CanonicalModel, Identifier, Sha256, utc_datetime


class Document(CanonicalModel):
    document_id: Identifier
    provider: Identifier
    sha256: Sha256
    relative_path: str = Field(pattern=r"^raw/[a-f0-9]{2}/[a-f0-9]{64}$")
    source_url: HttpUrl | None
    media_type: str = Field(min_length=1)
    fetched_at: datetime
    size_bytes: int = Field(ge=0)

    @field_validator("fetched_at")
    @classmethod
    def fetched_at_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)
