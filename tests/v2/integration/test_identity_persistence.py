from __future__ import annotations

import sqlite3

import pytest

from backend.v2.adapters.persistence import Database, IdentityRepository
from backend.v2.domain import DepositaryRelation, Instrument, Issuer, Listing, ProviderSymbol
from backend.v2.sqlite_runtime import has_wal_reset_fix


def issuer(identifier: str = "issuer-1") -> Issuer:
    return Issuer.model_validate(
        {"issuerId": identifier, "legalName": f"Synthetic {identifier}", "domicileCountry": "US", "identifiers": []}
    )


def instrument(identifier: str, issuer_id: str = "issuer-1", share_class: str = "A") -> Instrument:
    return Instrument.model_validate(
        {
            "instrumentId": identifier,
            "issuerId": issuer_id,
            "type": "common_stock",
            "shareClass": share_class,
            "rightsSummary": None,
            "isin": None,
        }
    )


def listing(identifier: str, instrument_id: str, mic: str, symbol: str) -> Listing:
    return Listing.model_validate(
        {
            "listingId": identifier,
            "instrumentId": instrument_id,
            "mic": mic,
            "symbol": symbol,
            "currency": "USD",
            "timezone": "America/New_York",
            "status": "active",
            "validFrom": "2020-01-01",
            "validTo": None,
        }
    )


@pytest.fixture
def repository(tmp_path) -> IdentityRepository:
    database = Database(tmp_path / "v2.sqlite3")
    assert database.migrate() == [1]
    assert database.migrate() == []
    return IdentityRepository(database)


def test_classes_and_listings_do_not_collide(repository: IdentityRepository) -> None:
    repository.put_issuer(issuer())
    repository.add_instrument(instrument("instrument-a", share_class="A"))
    repository.add_instrument(instrument("instrument-b", share_class="B"))
    repository.add_listing(listing("listing-xnas", "instrument-a", "XNAS", "SYN"))
    repository.add_listing(listing("listing-xnys", "instrument-b", "XNYS", "SYN"))

    assert repository.get_listing("listing-xnas").instrument_id == "instrument-a"
    assert repository.get_listing("listing-xnys").instrument_id == "instrument-b"


def test_provider_ticker_rename_preserves_history(repository: IdentityRepository) -> None:
    repository.put_issuer(issuer())
    repository.add_instrument(instrument("instrument-a"))
    repository.add_listing(listing("listing-a", "instrument-a", "XNAS", "NEW"))
    for symbol, valid_from, valid_to in (
        ("OLD", "2020-01-01", "2023-12-31"),
        ("NEW", "2024-01-01", None),
    ):
        repository.add_provider_symbol(
            ProviderSymbol.model_validate(
                {
                    "provider": "synthetic",
                    "capability": "prices",
                    "providerSymbol": symbol,
                    "listingId": "listing-a",
                    "validFrom": valid_from,
                    "validTo": valid_to,
                    "resolutionEvidenceId": f"evidence-{symbol.lower()}",
                }
            )
        )
    history = repository.provider_symbol_history("synthetic", "prices", "listing-a")
    assert [item.provider_symbol for item in history] == ["OLD", "NEW"]


def test_foreign_keys_reject_orphans(repository: IdentityRepository) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        repository.add_instrument(instrument("orphan", issuer_id="missing"))


def test_adr_relation_uses_distinct_instruments(repository: IdentityRepository) -> None:
    repository.put_issuer(issuer())
    repository.add_instrument(instrument("underlying"))
    repository.add_instrument(
        Instrument.model_validate(
            {
                "instrumentId": "adr",
                "issuerId": "issuer-1",
                "type": "adr",
                "shareClass": None,
                "rightsSummary": None,
                "isin": None,
            }
        )
    )
    repository.add_depositary_relation(
        DepositaryRelation.model_validate(
            {
                "relationId": "relation-1",
                "adrInstrumentId": "adr",
                "underlyingInstrumentId": "underlying",
                "adrShares": 1,
                "underlyingShares": 2,
                "validFrom": "2020-01-01",
                "validTo": None,
                "evidenceId": "evidence-1",
            }
        )
    )


def test_connection_enables_foreign_keys_and_keeps_unsafe_wal_off(tmp_path) -> None:
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    with database.connect() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        expected_mode = "wal" if has_wal_reset_fix() else "delete"
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == expected_mode
