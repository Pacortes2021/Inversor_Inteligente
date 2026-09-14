from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import socket

from fastapi.testclient import TestClient
import pytest

from backend.v2.adapters.persistence import (
    Database,
    FactRepository,
    IdentityRepository,
    RawStore,
    SelectionRepository,
    SnapshotRepository,
)
from backend.v2.adapters.providers.yahoo import (
    YahooHistoryRow,
    YahooProvider,
    YahooSnapshot,
)
from backend.v2.application import ingest_us_snapshot
from backend.v2.bootstrap import create_app
from backend.v2.domain import (
    Document,
    Instrument,
    Issuer,
    Listing,
    ProviderSymbol,
    SecCapture,
    SecUnitFact,
    ShareBasis,
)
from backend.v2.jobs import RefreshRequest


FIXTURE = Path("tests/v2/fixtures/sec/msft-2025-curated.json")
AS_OF = datetime(2026, 9, 14, 15, 0, tzinfo=timezone.utc)


class FrozenYahooClient:
    def fetch(self, *, symbol: str, start: date, end: date, timeout: float) -> YahooSnapshot:
        return YahooSnapshot(
            rows=(
                YahooHistoryRow(date(2026, 9, 10), "500", "499", "0", "0"),
                YahooHistoryRow(date(2026, 9, 11), "505", "504", "0", "0"),
            ),
            metadata={
                "currency": "USD",
                "exchangeTimezoneName": "America/New_York",
                "exchangeName": "NMS",
                "fullExchangeName": "NasdaqGS",
                "currentTradingPeriod": {
                    "regular": {
                        "start": datetime(2026, 9, 11, 13, 30, tzinfo=timezone.utc),
                        "end": datetime(2026, 9, 11, 20, 0, tzinfo=timezone.utc),
                    }
                },
            },
        )


def seed_identity(database: Database) -> None:
    identities = IdentityRepository(database)
    identities.put_issuer(
        Issuer.model_validate(
            {
                "issuerId": "msft",
                "legalName": "Microsoft Corporation",
                "domicileCountry": "US",
                "identifiers": [
                    {
                        "type": "cik",
                        "value": "0000789019",
                        "sourceUrl": "https://www.sec.gov/files/company_tickers.json",
                    }
                ],
            }
        )
    )
    identities.add_instrument(
        Instrument(
            instrumentId="msft-common",
            issuerId="msft",
            type="common_stock",
            shareClass="common",
            rightsSummary=None,
            isin=None,
        )
    )
    identities.add_listing(
        Listing(
            listingId="msft-xnas",
            instrumentId="msft-common",
            mic="XNAS",
            symbol="MSFT",
            currency="USD",
            timezone="America/New_York",
            status="active",
            validFrom="1986-03-13",
            validTo=None,
        )
    )
    identities.add_provider_symbol(
        ProviderSymbol(
            provider="yahoo",
            capability="prices",
            providerSymbol="MSFT",
            listingId="msft-xnas",
            validFrom="1986-03-13",
            validTo=None,
            resolutionEvidenceId="msft-yahoo-symbol-resolution",
        )
    )
    identities.add_share_basis(
        ShareBasis.model_validate(
            {
                "shareBasisId": "msft-fy2025-reported",
                "instrumentId": "msft-common",
                "asOf": "2025-06-30",
                "kind": "as_reported",
                "totalShares": "7434000000",
                "components": [
                    {
                        "componentId": "msft-common-outstanding",
                        "kind": "common_outstanding",
                        "shares": "7434000000",
                        "treatment": "included_in_denominator",
                        "evidenceId": "msft-2025-10k-eps-note",
                    }
                ],
                "version": "msft-basis-r12-v1",
            }
        )
    )


def sec_capture(raw_store: RawStore) -> SecCapture:
    raw = FIXTURE.read_bytes()
    payload = json.loads(raw)
    blob = raw_store.put(raw)
    document = Document(
        documentId="sec-msft-2025-curated",
        provider="sec",
        sha256=blob.sha256,
        relativePath=blob.relative_path,
        sourceUrl=payload["companyfactsUrl"],
        mediaType="application/json",
        fetchedAt=payload["fetchedAt"],
        sizeBytes=blob.size_bytes,
    )
    observations = [
        SecUnitFact.model_validate(
            {
                "cik": payload["cik"],
                "taxonomy": "us-gaap",
                "label": item["tag"],
                "description": "Curated SEC reconciliation observation",
                "accessionNumber": payload["accessionNumber"],
                "documentId": document.document_id,
                **item,
            }
        )
        for item in payload["observations"]
    ]
    return SecCapture(
        capability="companyfacts",
        cik=payload["cik"],
        document=document,
        facts=observations,
        entityName="MICROSOFT CORPORATION",
    )


def yahoo_capture(raw_store: RawStore, facts: FactRepository):
    provider = YahooProvider(
        raw_store=raw_store,
        documents=facts,
        client=FrozenYahooClient(),
        clock=lambda: AS_OF,
    )
    request = RefreshRequest.model_validate(
        {
            "provider": "yahoo",
            "capability": "prices",
            "resourceKey": "MSFT",
            "parserVersion": "yahoo-r11-v1",
            "parameters": {
                "issuerId": "msft",
                "instrumentId": "msft-common",
                "listingId": "msft-xnas",
                "mic": "XNAS",
                "currency": "USD",
                "timezone": "America/New_York",
                "start": "2026-09-10",
                "end": "2026-09-11",
            },
        }
    )
    result = provider.fetch(request)
    assert result.status == "success"
    return result.data[0]


def test_first_us_snapshot_ingests_and_replays_with_exact_sources_offline(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    database = Database(data_dir / "v2.sqlite3")
    database.migrate()
    seed_identity(database)
    raw_store = RawStore(data_dir)
    facts = FactRepository(database)
    sec = sec_capture(raw_store)
    yahoo = yahoo_capture(raw_store, facts)
    kwargs = {
        "sec_capture": sec,
        "yahoo_capture": yahoo,
        "issuer_id": "msft",
        "instrument_id": "msft-common",
        "listing_id": "msft-xnas",
        "quote_currency": "USD",
        "share_basis_id": "msft-fy2025-reported",
        "as_of": AS_OF,
        "identities": IdentityRepository(database),
        "facts": facts,
        "selections": SelectionRepository(database),
        "snapshots": SnapshotRepository(database),
    }

    first = ingest_us_snapshot(**kwargs)
    repeated = ingest_us_snapshot(**kwargs)

    assert repeated.snapshot.dataset_snapshot_id == first.snapshot.dataset_snapshot_id
    assert len(first.facts) == 11
    assert next(item for item in first.facts if item.concept == "price.close").value == "505"
    assert next(item for item in first.facts if item.concept == "revenue").value == "281724000000"

    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network access")),
    )
    client = TestClient(create_app(data_dir))
    response = client.get(f"/api/v2/snapshots/{first.snapshot.dataset_snapshot_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot"]["contentHash"] == first.snapshot.content_hash
    revenue = next(item for item in body["facts"] if item["concept"] == "revenue")
    assert revenue["evidence"][0]["provider"] == "sec"
    document_id = revenue["evidence"][0]["documentId"]
    document = client.get(f"/api/v2/documents/{document_id}")
    assert document.status_code == 200
    assert document.json()["sourceUrl"] == (
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json"
    )
    assert len(document.json()["sha256"]) == 64


def test_capability_api_reports_evidence_levels_without_a_global_audit_claim(tmp_path) -> None:
    response = TestClient(create_app(tmp_path)).get("/api/v2/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluatedOn"] == "2026-09-14"
    assert {item["evidenceLevel"] for item in body["records"]} == {
        "deterministic_replay",
        "sample_reconciled",
    }
    assert "100%" not in response.text
    assert all(item["liveSmokeStatus"] == "not_run" for item in body["records"])


def test_snapshot_ingest_rejects_sec_or_yahoo_identity_drift(tmp_path) -> None:
    data_dir = tmp_path / "data"
    database = Database(data_dir / "v2.sqlite3")
    database.migrate()
    seed_identity(database)
    raw_store = RawStore(data_dir)
    facts = FactRepository(database)
    sec = sec_capture(raw_store)
    yahoo = yahoo_capture(raw_store, facts)
    common = {
        "issuer_id": "msft",
        "instrument_id": "msft-common",
        "listing_id": "msft-xnas",
        "quote_currency": "USD",
        "share_basis_id": "msft-fy2025-reported",
        "as_of": AS_OF,
        "identities": IdentityRepository(database),
        "facts": facts,
        "selections": SelectionRepository(database),
        "snapshots": SnapshotRepository(database),
    }
    wrong_sec = sec.model_copy(
        update={
            "cik": "0001065280",
            "facts": [item.model_copy(update={"cik": "0001065280"}) for item in sec.facts],
        }
    )
    wrong_prices = [
        item.model_copy(update={"provider_symbol": "MSFQ"}) for item in yahoo.prices
    ]
    wrong_yahoo = yahoo.model_copy(update={"prices": wrong_prices})

    with pytest.raises(ValueError, match="CIK does not match"):
        ingest_us_snapshot(sec_capture=wrong_sec, yahoo_capture=yahoo, **common)
    with pytest.raises(ValueError, match="symbol or MIC does not match"):
        ingest_us_snapshot(sec_capture=sec, yahoo_capture=wrong_yahoo, **common)


def test_snapshot_selects_latest_restated_candidate_per_exact_context(tmp_path) -> None:
    data_dir = tmp_path / "data"
    database = Database(data_dir / "v2.sqlite3")
    database.migrate()
    seed_identity(database)
    raw_store = RawStore(data_dir)
    facts = FactRepository(database)
    sec = sec_capture(raw_store)
    original_revenue = next(item for item in sec.facts if item.tag.startswith("Revenue"))
    restated_revenue = original_revenue.model_copy(
        update={
            "value": "281725000000",
            "filed": date(2026, 8, 1),
            "accession_number": "0000950170-26-000001",
        }
    )
    restated_capture = sec.model_copy(update={"facts": [*sec.facts, restated_revenue]})

    result = ingest_us_snapshot(
        sec_capture=restated_capture,
        yahoo_capture=yahoo_capture(raw_store, facts),
        issuer_id="msft",
        instrument_id="msft-common",
        listing_id="msft-xnas",
        quote_currency="USD",
        share_basis_id="msft-fy2025-reported",
        as_of=AS_OF,
        identities=IdentityRepository(database),
        facts=facts,
        selections=SelectionRepository(database),
        snapshots=SnapshotRepository(database),
    )

    revenue = next(item for item in result.facts if item.concept == "revenue")
    assert revenue.value == "281725000000"
    revenue_decision = next(
        item for item in result.decisions if item.query.concept == "revenue"
    )
    assert len(revenue_decision.candidate_fact_ids) == 2
    assert len(result.facts) == 11
