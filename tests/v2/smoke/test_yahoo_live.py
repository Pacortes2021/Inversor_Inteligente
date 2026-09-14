from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import os

import pytest

from backend.v2.adapters.persistence import Database, FactRepository, RawStore
from backend.v2.adapters.providers.yahoo import YahooProvider
from backend.v2.jobs import RefreshRequest


pytestmark = pytest.mark.network


@pytest.mark.skipif(
    os.getenv("RUN_YAHOO_SMOKE") != "1",
    reason="set RUN_YAHOO_SMOKE=1 to exercise the live secondary provider",
)
def test_live_yahoo_price_capture_is_identified_and_dated(tmp_path) -> None:
    end = date.today()
    start = end - timedelta(days=10)
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    provider = YahooProvider(
        raw_store=RawStore(tmp_path),
        documents=FactRepository(database),
        clock=lambda: datetime.now(timezone.utc),
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
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        }
    )

    result = provider.fetch(request)

    assert result.status == "success", result.model_dump(mode="json")
    assert result.data[0].provider_label == "Yahoo Finance via yfinance"
    assert any(item.basis == "raw" for item in result.data[0].prices)
