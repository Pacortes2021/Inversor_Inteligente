from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.v2.adapters.persistence import Database, FactRepository, RawStore
from backend.v2.adapters.providers.yahoo import (
    YahooHistoryRow,
    YahooProvider,
    YahooSnapshot,
)
from backend.v2.jobs import CacheRepository, JobRepository, RefreshRequest, Worker


NOW = datetime(2026, 9, 14, 15, 0, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, snapshot: YahooSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = []

    def fetch(self, *, symbol: str, start: date, end: date, timeout: float) -> YahooSnapshot:
        self.calls.append((symbol, start, end, timeout))
        return self.snapshot


class FailingClient:
    def fetch(self, *, symbol: str, start: date, end: date, timeout: float) -> YahooSnapshot:
        raise RuntimeError("Yahoo unavailable")


@pytest.fixture
def snapshot() -> YahooSnapshot:
    return YahooSnapshot(
        rows=(
            YahooHistoryRow(date(2025, 1, 2), "100", "48", "0", "0"),
            YahooHistoryRow(date(2025, 1, 3), "52", "50", "1.25", "2"),
        ),
        metadata={
            "currency": "USD",
            "exchangeTimezoneName": "America/New_York",
            "exchangeName": "NMS",
            "fullExchangeName": "NasdaqGS",
            "currentTradingPeriod": {
                "regular": {
                    "start": datetime(2025, 1, 3, 14, 30, tzinfo=timezone.utc),
                    "end": datetime(2025, 1, 3, 21, 0, tzinfo=timezone.utc),
                }
            },
        },
    )


@pytest.fixture
def stores(tmp_path):
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    return database, FactRepository(database), RawStore(tmp_path)


def request(capability: str = "prices") -> RefreshRequest:
    return RefreshRequest.model_validate(
        {
            "provider": "yahoo",
            "capability": capability,
            "resourceKey": "MSFT",
            "parserVersion": "yahoo-r11-v1",
            "parameters": {
                "issuerId": "msft",
                "instrumentId": "msft-common",
                "listingId": "msft-xnas",
                "mic": "XNAS",
                "currency": "USD",
                "timezone": "America/New_York",
                "start": "2025-01-02",
                "end": "2025-01-03",
            },
        }
    )


def provider(stores, client) -> YahooProvider:
    _, documents, raw_store = stores
    return YahooProvider(
        raw_store=raw_store,
        documents=documents,
        client=client,
        clock=lambda: NOW,
    )


def test_prices_keep_raw_split_adjusted_and_total_return_distinct(stores, snapshot) -> None:
    client = FakeClient(snapshot)
    result = provider(stores, client).fetch(request("prices"))

    assert result.status == "success"
    capture = result.data[0]
    assert capture.provider_label == "Yahoo Finance via yfinance"
    first_day = [item for item in capture.prices if item.session_date == date(2025, 1, 2)]
    assert {item.basis: item.value for item in first_day} == {
        "raw": "100",
        "split_adjusted": "50",
        "total_return": "48",
    }
    split_adjusted = next(item for item in first_day if item.basis == "split_adjusted")
    assert split_adjusted.split_adjustment_as_of == date(2025, 1, 3)
    assert client.calls == [("MSFT", date(2025, 1, 2), date(2025, 1, 3), 30)]
    normalized = stores[2].read(capture.document.sha256)
    assert b'"format":"yahoo-normalized-v1"' in normalized
    assert capture.document.media_type == "application/vnd.inversor.yahoo-normalized+json"


def test_session_preserves_configured_mic_and_yahoo_exchange_code_separately(stores, snapshot) -> None:
    result = provider(stores, FakeClient(snapshot)).fetch(request("session"))

    session = result.data[0].sessions[0]
    assert session.mic == "XNAS"
    assert session.source_exchange_code == "NMS"
    assert session.timezone == "America/New_York"
    assert session.opens_at == datetime(2025, 1, 3, 14, 30, tzinfo=timezone.utc)
    assert session.closes_at == datetime(2025, 1, 3, 21, 0, tzinfo=timezone.utc)


def test_calendar_is_observed_coverage_not_an_official_exchange_schedule(stores, snapshot) -> None:
    result = provider(stores, FakeClient(snapshot)).fetch(request("calendar"))

    calendar = result.data[0].calendars[0]
    assert calendar.observed_session_dates == [date(2025, 1, 2), date(2025, 1, 3)]
    assert calendar.official_schedule is False
    assert calendar.coverage_start == date(2025, 1, 2)
    assert calendar.coverage_end == date(2025, 1, 3)


def test_actions_are_a_separate_capability_with_typed_semantics(stores, snapshot) -> None:
    result = provider(stores, FakeClient(snapshot)).fetch(request("actions"))

    actions = result.data[0].actions
    assert [(item.kind, item.ex_date) for item in actions] == [
        ("dividend", date(2025, 1, 3)),
        ("split", date(2025, 1, 3)),
    ]
    dividend, split = actions
    assert dividend.amount == "1.25" and dividend.currency == "USD"
    assert split.split_factor == "2" and split.currency is None


def test_metadata_identity_mismatch_is_not_silently_accepted(stores, snapshot) -> None:
    wrong = YahooSnapshot(snapshot.rows, {**snapshot.metadata, "currency": "EUR"})

    result = provider(stores, FakeClient(wrong)).fetch(request("prices"))

    assert result.status == "failure"
    assert result.error == "invalid_payload"
    assert result.data == []


def test_a15_yahoo_failure_keeps_previous_valid_cache(stores, snapshot) -> None:
    database = stores[0]
    jobs = JobRepository(database)
    cache = CacheRepository(database)
    refresh = request("prices")
    first = jobs.enqueue("yahoo-msft-first", refresh, now=NOW)
    first_worker = Worker(
        worker_id="yahoo-worker",
        jobs=jobs,
        cache=cache,
        providers={"yahoo": provider(stores, FakeClient(snapshot))},
    )
    assert first_worker.run_once(now=NOW) is True
    valid_before = cache.last_valid(refresh)
    assert valid_before is not None

    second = jobs.enqueue("yahoo-msft-second", refresh, now=NOW)
    failing_worker = Worker(
        worker_id="yahoo-worker",
        jobs=jobs,
        cache=cache,
        providers={"yahoo": provider(stores, FailingClient())},
    )
    assert failing_worker.run_once(now=NOW) is True

    assert jobs.get(first.job_id).status == "succeeded"
    assert jobs.get(second.job_id).status == "queued"
    assert jobs.get(second.job_id).progress == "retry_scheduled"
    assert cache.last_valid(refresh) == valid_before
    with database.connect() as connection:
        state = connection.execute(
            "SELECT last_error FROM cache_entries WHERE cache_key = ?",
            (cache.key(refresh),),
        ).fetchone()
    assert state["last_error"] == "provider_unavailable"
