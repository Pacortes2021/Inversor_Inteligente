"""Shared primitives for canonical v2 contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints


DECIMAL_PATTERN = r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$"
NONNEGATIVE_DECIMAL_PATTERN = r"^(0|[1-9][0-9]*)(\.[0-9]+)?$"
DecimalString = Annotated[str, StringConstraints(pattern=DECIMAL_PATTERN)]
NonnegativeDecimalString = Annotated[
    str, StringConstraints(pattern=NONNEGATIVE_DECIMAL_PATTERN)
]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=160)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CanonicalModel(BaseModel):
    """Base model with stable JSON aliases and no unrecognised fields."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
        allow_inf_nan=False,
    )


def decimal_value(value: str) -> Decimal:
    """Parse a contract decimal and reject non-finite values."""

    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid canonical decimal") from exc
    if not parsed.is_finite():
        raise ValueError("canonical decimals must be finite")
    return parsed


def utc_datetime(value: datetime) -> datetime:
    """Require an aware timestamp and normalise it to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc)


def jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True, exclude_none=False)


def next_anniversary(start: date) -> date:
    """One-year anniversary, mapping leap day to February 28."""

    try:
        return start.replace(year=start.year + 1)
    except ValueError:
        return start.replace(year=start.year + 1, day=28)
