"""Opt-in live SEC check; never runs as part of deterministic CI."""

from __future__ import annotations

import os

import pytest

from backend.v2.adapters.persistence import Database, FactRepository, RawStore
from backend.v2.adapters.providers import SecProvider
from backend.v2.jobs import RefreshRequest


pytestmark = pytest.mark.network


def sec_request(capability: str, resource_key: str, **parameters) -> RefreshRequest:
    return RefreshRequest.model_validate(
        {
            "provider": "sec",
            "capability": capability,
            "resourceKey": resource_key,
            "parserVersion": "sec-r09-v1",
            "parameters": parameters,
        }
    )


def test_sec_identity_submissions_and_companyfacts_live(tmp_path) -> None:
    if os.environ.get("RUN_SEC_SMOKE") != "1":
        pytest.skip("set RUN_SEC_SMOKE=1 for the explicit live SEC check")
    contact = os.environ.get("SEC_CONTACT_EMAIL")
    if not contact:
        pytest.skip("SEC_CONTACT_EMAIL is required for identified SEC access")

    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    provider = SecProvider(
        contact=contact,
        raw_store=RawStore(tmp_path),
        documents=FactRepository(database),
    )
    identity = provider.fetch(sec_request("identity", "MSFT"))
    assert identity.status == "success" and identity.data[0].identities
    cik = identity.data[0].identities[0].cik

    submissions = provider.fetch(sec_request("submissions", cik))
    companyfacts = provider.fetch(sec_request("companyfacts", cik))
    assert submissions.status == "success" and submissions.data[0].filings
    assert companyfacts.status == "success" and companyfacts.data[0].facts
