"""Typed, loss-aware views over SEC submissions and companyfacts payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, DecimalString, Identifier, utc_datetime
from .documents import Document


class SecFiling(CanonicalModel):
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: Identifier
    filing_date: date
    report_date: date | None
    acceptance_datetime: datetime | None
    primary_document: str | None
    document_id: Identifier

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else utc_datetime(value)


class SecUnitFact(CanonicalModel):
    cik: str = Field(pattern=r"^[0-9]{10}$")
    taxonomy: Identifier
    tag: Identifier
    label: str
    description: str
    unit: Identifier
    value: DecimalString
    start: date | None
    end: date
    filed: date
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: Identifier
    fiscal_year: int | None
    fiscal_period: str | None
    frame: str | None
    document_id: Identifier

    @model_validator(mode="after")
    def ordered_period(self) -> "SecUnitFact":
        if self.start is not None and self.start > self.end:
            raise ValueError("SEC fact start cannot follow end")
        if self.filed < self.end:
            raise ValueError("SEC fact filing date cannot precede period end")
        return self


class SecIdentity(CanonicalModel):
    cik: str = Field(pattern=r"^[0-9]{10}$")
    ticker: Identifier
    title: str
    exchange: str | None
    document_id: Identifier


class SecCapture(CanonicalModel):
    capability: Literal["identity", "submissions", "companyfacts"]
    cik: str | None = Field(default=None, pattern=r"^[0-9]{10}$")
    document: Document
    identities: list[SecIdentity] = Field(default_factory=list)
    filings: list[SecFiling] = Field(default_factory=list)
    facts: list[SecUnitFact] = Field(default_factory=list)
    entity_name: str | None = None

    @model_validator(mode="after")
    def capability_shape(self) -> "SecCapture":
        populated = sum(bool(items) for items in (self.identities, self.filings, self.facts))
        if populated > 1:
            raise ValueError("SEC capture types cannot be mixed")
        if self.capability != "identity" and self.cik is None:
            raise ValueError("SEC filer capture requires CIK")
        if self.capability == "identity" and self.filings + self.facts:
            raise ValueError("identity capture cannot contain filings or facts")
        if self.capability == "submissions" and (self.identities or self.facts):
            raise ValueError("submissions capture can contain only filings")
        if self.capability == "companyfacts" and (self.identities or self.filings):
            raise ValueError("companyfacts capture can contain only facts")
        children = [*self.identities, *self.filings, *self.facts]
        if any(item.document_id != self.document.document_id for item in children):
            raise ValueError("SEC capture children must reference the capture document")
        if self.cik is not None and any(
            getattr(item, "cik", self.cik) != self.cik
            for item in [*self.filings, *self.facts]
        ):
            raise ValueError("SEC capture children must match the capture CIK")
        return self


def decimal_from_sec(value: Any) -> str:
    """Preserve a SEC JSON number as a canonical, finite decimal string."""

    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("SEC fact value must be numeric")
    rendered = str(value)
    if "e" in rendered.lower():
        from decimal import Decimal, InvalidOperation

        try:
            rendered = format(Decimal(rendered), "f")
        except InvalidOperation as error:
            raise ValueError("SEC fact value must be finite") from error
    return rendered
