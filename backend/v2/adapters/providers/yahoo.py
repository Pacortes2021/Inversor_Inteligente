"""Secondary Yahoo Finance market data through an isolated yfinance client."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable, Mapping, Protocol
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import yfinance as yf

from ...domain import (
    CorporateAction,
    Document,
    MarketCalendarCoverage,
    MarketPrice,
    MarketSession,
    ProviderResult,
    YahooCapture,
)
from ...domain.common import canonical_json
from ...jobs import RefreshRequest
from ..persistence import FactRepository, RawStore


PROVIDER_LABEL = "Yahoo Finance via yfinance"
CAPABILITIES = {"prices", "session", "calendar", "actions"}


@dataclass(frozen=True)
class YahooHistoryRow:
    session_date: date
    close: str
    adjusted_close: str | None
    dividend: str | None
    split_factor: str | None


@dataclass(frozen=True)
class YahooSnapshot:
    rows: tuple[YahooHistoryRow, ...]
    metadata: Mapping[str, object]


class YahooClient(Protocol):
    def fetch(
        self, *, symbol: str, start: date, end: date, timeout: float
    ) -> YahooSnapshot: ...


class YfinanceYahooClient:
    """Keep third-party dataframe and metadata shapes outside the domain layer."""

    def fetch(
        self, *, symbol: str, start: date, end: date, timeout: float
    ) -> YahooSnapshot:
        ticker = yf.Ticker(symbol)
        history = ticker.history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            prepost=False,
            actions=True,
            auto_adjust=False,
            back_adjust=False,
            repair=False,
            keepna=False,
            rounding=False,
            timeout=timeout,
            raise_errors=True,
        )
        rows = []
        for index, record in history.iterrows():
            close = _decimal(record.get("Close"))
            if close is None:
                continue
            rows.append(
                YahooHistoryRow(
                    session_date=pd.Timestamp(index).date(),
                    close=close,
                    adjusted_close=_decimal(record.get("Adj Close")),
                    dividend=_decimal(record.get("Dividends")),
                    split_factor=_decimal(record.get("Stock Splits")),
                )
            )
        return YahooSnapshot(tuple(rows), dict(ticker.get_history_metadata(repair=False)))


@dataclass(frozen=True)
class _YahooIdentity:
    issuer_id: str
    instrument_id: str
    listing_id: str
    mic: str
    currency: str
    timezone: str
    symbol: str
    start: date
    end: date


class _IdentityMismatch(ValueError):
    pass


class YahooProvider:
    def __init__(
        self,
        *,
        raw_store: RawStore,
        documents: FactRepository,
        client: YahooClient | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        timeout_seconds: float = 30,
    ) -> None:
        self.raw_store = raw_store
        self.documents = documents
        self.client = client or YfinanceYahooClient()
        self.clock = clock
        self.timeout_seconds = timeout_seconds

    def fetch(self, request: RefreshRequest) -> ProviderResult[YahooCapture]:
        fetched_at = self.clock()
        try:
            identity = _identity(request)
        except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
            return self._failure(request, "invalid_payload", fetched_at)
        try:
            snapshot = self.client.fetch(
                symbol=identity.symbol,
                start=identity.start,
                end=identity.end,
                timeout=self.timeout_seconds,
            )
        except Exception as error:
            fetched_at = self.clock()
            if "rate" in str(error).lower() or "too many requests" in str(error).lower():
                return self._failure(request, "rate_limited", fetched_at, retry_after=60)
            return self._failure(request, "provider_unavailable", fetched_at)
        fetched_at = self.clock()
        if not snapshot.rows:
            return self._failure(request, "not_covered", fetched_at)
        try:
            _validate_metadata(identity, snapshot.metadata)
            document = self._store_normalized(identity, snapshot, fetched_at)
            capture = _capture(request.capability, identity, snapshot, document)
        except _IdentityMismatch:
            return self._failure(request, "invalid_payload", fetched_at)
        except (KeyError, TypeError, ValueError, InvalidOperation):
            return self._failure(request, "schema_changed", fetched_at)
        return ProviderResult[YahooCapture](
            provider="yahoo",
            capability=request.capability,
            status="success",
            data=[capture],
            source="yahoo_finance_via_yfinance",
            fetchedAt=fetched_at,
            retryAfterSeconds=None,
            error=None,
        )

    def _store_normalized(
        self,
        identity: _YahooIdentity,
        snapshot: YahooSnapshot,
        fetched_at: datetime,
    ) -> Document:
        payload = {
            "format": "yahoo-normalized-v1",
            "providerLabel": PROVIDER_LABEL,
            "request": {
                "symbol": identity.symbol,
                "start": identity.start.isoformat(),
                "end": identity.end.isoformat(),
            },
            "metadata": _metadata_payload(snapshot.metadata),
            "rows": [
                {
                    "sessionDate": row.session_date.isoformat(),
                    "close": row.close,
                    "adjustedClose": row.adjusted_close,
                    "dividend": row.dividend,
                    "splitFactor": row.split_factor,
                }
                for row in snapshot.rows
            ],
        }
        content = canonical_json(payload).encode("utf-8")
        blob = self.raw_store.put(content)
        document = Document(
            documentId=f"yahoo-normalized-{blob.sha256[:24]}",
            provider="yahoo",
            sha256=blob.sha256,
            relativePath=blob.relative_path,
            sourceUrl=f"https://finance.yahoo.com/quote/{quote(identity.symbol, safe='')}/history/",
            mediaType="application/vnd.inversor.yahoo-normalized+json",
            fetchedAt=fetched_at,
            sizeBytes=blob.size_bytes,
        )
        return self.documents.add_document(document)

    @staticmethod
    def _failure(
        request: RefreshRequest,
        error: str,
        fetched_at: datetime,
        *,
        retry_after: int | None = None,
    ) -> ProviderResult[YahooCapture]:
        return ProviderResult[YahooCapture](
            provider="yahoo",
            capability=request.capability,
            status="failure",
            data=[],
            source="yahoo_finance_via_yfinance",
            fetchedAt=fetched_at,
            retryAfterSeconds=retry_after,
            error=error,
        )


def _identity(request: RefreshRequest) -> _YahooIdentity:
    if request.provider != "yahoo" or request.capability not in CAPABILITIES:
        raise ValueError("unsupported Yahoo request")
    parameters = request.parameters
    values = {
        name: str(parameters[name])
        for name in ("issuerId", "instrumentId", "listingId", "mic", "currency", "timezone")
    }
    start = date.fromisoformat(str(parameters["start"]))
    end = date.fromisoformat(str(parameters["end"]))
    if start > end:
        raise ValueError("Yahoo range is inverted")
    if len(values["mic"]) != 4 or len(values["currency"]) != 3:
        raise ValueError("invalid listing identity")
    ZoneInfo(values["timezone"])
    return _YahooIdentity(
        issuer_id=values["issuerId"],
        instrument_id=values["instrumentId"],
        listing_id=values["listingId"],
        mic=values["mic"].upper(),
        currency=values["currency"].upper(),
        timezone=values["timezone"],
        symbol=request.resource_key,
        start=start,
        end=end,
    )


def _validate_metadata(identity: _YahooIdentity, metadata: Mapping[str, object]) -> None:
    provider_currency = str(metadata.get("currency", "")).upper()
    provider_timezone = str(metadata.get("exchangeTimezoneName", ""))
    if provider_currency != identity.currency or provider_timezone != identity.timezone:
        raise _IdentityMismatch("Yahoo metadata does not match configured listing")


def _capture(
    capability: str,
    identity: _YahooIdentity,
    snapshot: YahooSnapshot,
    document: Document,
) -> YahooCapture:
    common = {
        "capability": capability,
        "providerLabel": PROVIDER_LABEL,
        "document": document,
    }
    if capability == "prices":
        return YahooCapture(**common, prices=_prices(identity, snapshot, document))
    if capability == "session":
        return YahooCapture(**common, sessions=[_current_session(identity, snapshot, document.document_id)])
    if capability == "calendar":
        return YahooCapture(
            **common,
            calendars=[
                MarketCalendarCoverage(
                    listingId=identity.listing_id,
                    mic=identity.mic,
                    providerSymbol=identity.symbol,
                    timezone=identity.timezone,
                    coverageStart=identity.start,
                    coverageEnd=identity.end,
                    observedSessionDates=sorted({row.session_date for row in snapshot.rows}),
                    officialSchedule=False,
                    sourceExchangeCode=_source_exchange(snapshot.metadata),
                    documentId=document.document_id,
                )
            ],
        )
    if capability == "actions":
        return YahooCapture(**common, actions=_actions(identity, snapshot, document.document_id))
    raise ValueError("unsupported Yahoo capability")


def _prices(
    identity: _YahooIdentity, snapshot: YahooSnapshot, document: Document
) -> list[MarketPrice]:
    rows = sorted(snapshot.rows, key=lambda item: item.session_date)
    output: list[MarketPrice] = []
    for row in rows:
        common = {
            "issuerId": identity.issuer_id,
            "instrumentId": identity.instrument_id,
            "listingId": identity.listing_id,
            "mic": identity.mic,
            "providerSymbol": identity.symbol,
            "sessionDate": row.session_date,
            "currency": identity.currency,
            "documentId": document.document_id,
        }
        output.append(
            MarketPrice(
                **common,
                value=row.close,
                basis="split_adjusted",
                sourceField="Close",
                splitAdjustmentAsOf=document.fetched_at.date(),
            )
        )
        if row.adjusted_close is not None:
            output.append(
                MarketPrice(
                    **common,
                    value=row.adjusted_close,
                    basis="total_return",
                    sourceField="Adj Close",
                    splitAdjustmentAsOf=None,
                )
            )
    return output


def _actions(
    identity: _YahooIdentity, snapshot: YahooSnapshot, document_id: str
) -> list[CorporateAction]:
    output = []
    for row in sorted(snapshot.rows, key=lambda item: item.session_date):
        dividend = _positive_decimal(row.dividend)
        if dividend is not None:
            output.append(
                CorporateAction(
                    actionId=_action_id(identity.listing_id, "dividend", row.session_date, dividend),
                    listingId=identity.listing_id,
                    mic=identity.mic,
                    providerSymbol=identity.symbol,
                    kind="dividend",
                    exDate=row.session_date,
                    amount=format(dividend, "f"),
                    currency=identity.currency,
                    splitFactor=None,
                    documentId=document_id,
                )
            )
        split = _positive_decimal(row.split_factor)
        if split is not None:
            output.append(
                CorporateAction(
                    actionId=_action_id(identity.listing_id, "split", row.session_date, split),
                    listingId=identity.listing_id,
                    mic=identity.mic,
                    providerSymbol=identity.symbol,
                    kind="split",
                    exDate=row.session_date,
                    amount=None,
                    currency=None,
                    splitFactor=format(split, "f"),
                    documentId=document_id,
                )
            )
    return output


def _current_session(
    identity: _YahooIdentity, snapshot: YahooSnapshot, document_id: str
) -> MarketSession:
    periods = snapshot.metadata["currentTradingPeriod"]
    if not isinstance(periods, Mapping) or not isinstance(periods.get("regular"), Mapping):
        raise ValueError("Yahoo metadata lacks regular session")
    regular = periods["regular"]
    opens_at = _timestamp(regular["start"])
    closes_at = _timestamp(regular["end"])
    session_date = closes_at.astimezone(ZoneInfo(identity.timezone)).date()
    return MarketSession(
        listingId=identity.listing_id,
        mic=identity.mic,
        providerSymbol=identity.symbol,
        sessionDate=session_date,
        timezone=identity.timezone,
        opensAt=opens_at,
        closesAt=closes_at,
        sourceExchangeCode=_source_exchange(snapshot.metadata),
        scheduleSource="yahoo_current_metadata",
        documentId=document_id,
    )


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Yahoo session timestamp lacks timezone")
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Yahoo session timestamp lacks timezone")
        return parsed.astimezone(timezone.utc)
    raise ValueError("unsupported Yahoo session timestamp")


def _metadata_payload(metadata: Mapping[str, object]) -> dict[str, object]:
    periods = metadata.get("currentTradingPeriod")
    regular = periods.get("regular") if isinstance(periods, Mapping) else None
    return {
        "currency": metadata.get("currency"),
        "exchangeTimezoneName": metadata.get("exchangeTimezoneName"),
        "exchangeName": metadata.get("exchangeName"),
        "fullExchangeName": metadata.get("fullExchangeName"),
        "regularSession": (
            {
                "start": _timestamp(regular["start"]).isoformat(),
                "end": _timestamp(regular["end"]).isoformat(),
            }
            if isinstance(regular, Mapping) and "start" in regular and "end" in regular
            else None
        ),
    }


def _source_exchange(metadata: Mapping[str, object]) -> str | None:
    value = metadata.get("exchangeName")
    return None if value is None else str(value)


def _action_id(listing_id: str, kind: str, ex_date: date, value: Decimal) -> str:
    digest = hashlib.sha256(
        f"{listing_id}|{kind}|{ex_date.isoformat()}|{format(value, 'f')}".encode("utf-8")
    ).hexdigest()[:32]
    return f"yahoo-action-{digest}"


def _positive_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    parsed = Decimal(value)
    return parsed if parsed > 0 else None


def _decimal(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        raise ValueError("Yahoo numeric value cannot be boolean")
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("Yahoo numeric value must be finite")
    rendered = format(parsed, "f")
    return "0" if parsed == 0 else rendered
