from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.v2.adapters.persistence import Database, FactRepository, RawStore
from backend.v2.adapters.providers.sec import SecHttpResponse, SecProvider, SecRateLimiter
from backend.v2.jobs import CacheRepository, JobRepository, RefreshRequest, Worker
from backend.v2.domain import SecCapture


FIXTURES = Path("tests/v2/fixtures/sec")
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self, responses: dict[str, SecHttpResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def get(self, url: str, *, headers, timeout: float) -> SecHttpResponse:
        self.calls.append((url, dict(headers), timeout))
        return self.responses[url]


class NoWaitLimiter:
    def __init__(self) -> None:
        self.calls = 0

    def acquire(self) -> None:
        self.calls += 1


def response(name: str, *, status: int = 200, headers: dict[str, str] | None = None):
    return SecHttpResponse(
        status,
        (FIXTURES / name).read_bytes() if status == 200 else b"limited",
        headers or {"Content-Type": "application/json; charset=utf-8"},
    )


def request(capability: str, resource_key: str, **parameters) -> RefreshRequest:
    return RefreshRequest.model_validate(
        {
            "provider": "sec",
            "capability": capability,
            "resourceKey": resource_key,
            "parserVersion": "sec-r09-v1",
            "parameters": parameters,
        }
    )


@pytest.fixture
def provider_parts(tmp_path):
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    limiter = NoWaitLimiter()
    return database, FactRepository(database), RawStore(tmp_path), limiter


def make_provider(provider_parts, transport: FakeTransport) -> SecProvider:
    _, documents, raw_store, limiter = provider_parts
    return SecProvider(
        contact="tests@example.invalid",
        raw_store=raw_store,
        documents=documents,
        transport=transport,
        rate_limiter=limiter,
        clock=lambda: NOW,
    )


def test_resolves_exact_ticker_to_cik_and_identifies_backend_request(provider_parts) -> None:
    url = "https://www.sec.gov/files/company_tickers.json"
    transport = FakeTransport({url: response("company_tickers.json")})
    provider = make_provider(provider_parts, transport)

    result = provider.fetch(request("identity", "synx"))

    assert result.status == "success"
    assert result.data[0].identities[0].cik == "0000000123"
    assert result.data[0].identities[0].ticker == "SYNX"
    assert transport.calls[0][1]["User-Agent"] == "InversorInteligente/2.0 (tests@example.invalid)"
    assert transport.calls[0][0].startswith("https://www.sec.gov/")


def test_submissions_preserve_accession_publication_and_original_document(provider_parts) -> None:
    database, documents, raw_store, limiter = provider_parts
    url = "https://data.sec.gov/submissions/CIK0000000123.json"
    transport = FakeTransport(
        {url: response("CIK0000000123.submissions.json")}
    )
    provider = make_provider(provider_parts, transport)

    first = provider.fetch(request("submissions", "123"))
    repeated = provider.fetch(request("submissions", "123"))

    filing = first.data[0].filings[0]
    assert filing.accession_number == "0000000123-26-000001"
    assert filing.filing_date.isoformat() == "2026-02-20"
    assert filing.report_date.isoformat() == "2025-12-31"
    assert filing.acceptance_datetime == datetime(2026, 2, 20, 12, 34, 56, tzinfo=timezone.utc)
    assert repeated.data[0].document.document_id == first.data[0].document.document_id
    assert raw_store.read(first.data[0].document.sha256) == (
        FIXTURES / "CIK0000000123.submissions.json"
    ).read_bytes()
    assert documents.get_document(first.data[0].document.document_id) is not None
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM documents").fetchone()[0] == 1
    assert limiter.calls == 2


def test_companyfacts_preserve_taxonomy_units_periods_and_non_usd(provider_parts) -> None:
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json"
    provider = make_provider(
        provider_parts,
        FakeTransport({url: response("CIK0000000123.companyfacts.json")}),
    )

    result = provider.fetch(request("companyfacts", "issuer-a", cik="123"))

    assert result.status == "success"
    capture = result.data[0]
    assert capture.cik == "0000000123"
    assert {fact.taxonomy for fact in capture.facts} == {"us-gaap", "synx"}
    assert {fact.unit for fact in capture.facts} == {"USD", "EUR", "shares", "subscribers"}
    eur = next(fact for fact in capture.facts if fact.unit == "EUR")
    assert eur.value == "900000"
    assert eur.start.isoformat() == "2025-01-01"
    assert eur.end.isoformat() == "2025-12-31"
    assert eur.fiscal_year == 2025
    assert eur.accession_number == "0000000123-26-000001"


def test_typed_sec_capture_runs_through_persistent_worker_cache(provider_parts) -> None:
    database, _, _, _ = provider_parts
    url = "https://data.sec.gov/submissions/CIK0000000123.json"
    provider = make_provider(
        provider_parts,
        FakeTransport({url: response("CIK0000000123.submissions.json")}),
    )
    jobs = JobRepository(database)
    cache = CacheRepository(database)
    refresh = request("submissions", "123")
    job = jobs.enqueue("sec-submissions-123", refresh, now=NOW)
    worker = Worker(
        worker_id="sec-worker", jobs=jobs, cache=cache, providers={"sec": provider}
    )

    assert worker.run_once(now=NOW) is True
    assert jobs.get(job.job_id).status == "succeeded"
    cached = cache.last_valid(refresh)
    assert cached is not None
    assert cached[0]["filings"][0]["accessionNumber"] == "0000000123-26-000001"


def test_rate_limit_result_honours_retry_after_without_replacing_data(provider_parts) -> None:
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json"
    transport = FakeTransport(
        {url: SecHttpResponse(429, b"slow down", {"Retry-After": "120"})}
    )
    provider = make_provider(provider_parts, transport)

    result = provider.fetch(request("companyfacts", "123"))

    assert result.status == "failure"
    assert result.error == "rate_limited"
    assert result.retry_after_seconds == 120
    assert result.data == []
    with provider_parts[0].connect() as connection:
        assert connection.execute("SELECT count(*) FROM documents").fetchone()[0] == 0


def test_invalid_json_is_preserved_but_reported_as_invalid(provider_parts) -> None:
    url = "https://data.sec.gov/submissions/CIK0000000123.json"
    transport = FakeTransport(
        {url: SecHttpResponse(200, b"not-json", {"Content-Type": "application/json"})}
    )
    provider = make_provider(provider_parts, transport)

    result = provider.fetch(request("submissions", "123"))

    assert result.status == "failure"
    assert result.error == "invalid_payload"
    with provider_parts[0].connect() as connection:
        assert connection.execute("SELECT count(*) FROM documents").fetchone()[0] == 1


def test_shared_rate_limiter_enforces_configured_interval() -> None:
    state = {"now": 10.0}
    sleeps: list[float] = []

    def monotonic() -> float:
        return state["now"]

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        state["now"] += seconds

    limiter = SecRateLimiter(2, monotonic=monotonic, sleep=sleep)
    limiter.acquire()
    limiter.acquire()

    assert sleeps == [pytest.approx(0.5)]


def test_sec_provider_requires_identified_contact(provider_parts) -> None:
    _, documents, raw_store, _ = provider_parts
    with pytest.raises(ValueError, match="identified email"):
        SecProvider(contact="anonymous", raw_store=raw_store, documents=documents)


def test_sec_capture_rejects_child_from_another_cik_or_document(provider_parts) -> None:
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json"
    capture = make_provider(
        provider_parts,
        FakeTransport({url: response("CIK0000000123.companyfacts.json")}),
    ).fetch(request("companyfacts", "123")).data[0]
    wrong_cik = capture.facts[0].model_copy(update={"cik": "0000000456"})
    wrong_document = capture.facts[0].model_copy(update={"document_id": "other-document"})

    with pytest.raises(ValueError, match="capture CIK"):
        SecCapture.model_validate(
            capture.model_copy(update={"facts": [wrong_cik]}).model_dump(mode="json")
        )
    with pytest.raises(ValueError, match="capture document"):
        SecCapture.model_validate(
            capture.model_copy(update={"facts": [wrong_document]}).model_dump(mode="json")
        )
