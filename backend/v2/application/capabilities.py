"""Evidence-level report for provider capabilities; no global audit badge."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from ..domain.common import CanonicalModel, Identifier


class CapabilityRecord(CanonicalModel):
    provider: Identifier
    capability: Identifier
    evidence_level: Literal[
        "documented", "deterministic_replay", "sample_reconciled", "unsupported", "unknown"
    ]
    deterministic_test: bool
    live_smoke_status: Literal["not_run", "passed", "failed", "not_applicable"]
    limitations: list[str] = Field(default_factory=list)


class CapabilityReport(CanonicalModel):
    evaluated_on: date
    records: list[CapabilityRecord]


def provider_capability_report() -> CapabilityReport:
    return CapabilityReport(
        evaluatedOn=date(2026, 9, 14),
        records=[
            CapabilityRecord(
                provider="sec",
                capability="identity_submissions_companyfacts",
                evidenceLevel="deterministic_replay",
                deterministicTest=True,
                liveSmokeStatus="not_run",
                limitations=["Live smoke requires an identified SEC contact."],
            ),
            CapabilityRecord(
                provider="sec",
                capability="initial_us_gaap_mapping",
                evidenceLevel="sample_reconciled",
                deterministicTest=True,
                liveSmokeStatus="not_run",
                limitations=[
                    "MSFT FY2025 and NFLX FY2025 curated excerpts only.",
                    "Extensions and dimensions are not supported.",
                ],
            ),
            CapabilityRecord(
                provider="yahoo",
                capability="prices_sessions_observed_calendar_actions",
                evidenceLevel="deterministic_replay",
                deterministicTest=True,
                liveSmokeStatus="not_run",
                limitations=[
                    "Secondary source via yfinance; no exchange SLA.",
                    "Observed dates are not an official exchange calendar.",
                    "No live smoke result is claimed by the release.",
                ],
            ),
        ],
    )
