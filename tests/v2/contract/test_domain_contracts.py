from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.v2.domain import (
    Assessment,
    DatasetSnapshot,
    Issuer,
    ScenarioSetRevision,
    validate_lineage,
)
from backend.v2.domain.facts import Fact


UTC = timezone.utc


def test_identity_distinguishes_country_from_listing_currency() -> None:
    issuer = Issuer.model_validate(
        {
            "issuerId": "issuer-cl-1",
            "legalName": "Emisor sintético",
            "domicileCountry": "CL",
            "identifiers": [{"type": "rut", "value": "synthetic-rut", "sourceUrl": None}],
        }
    )
    assert issuer.domicile_country == "CL"


def test_snapshot_requires_price_and_fx_to_belong_to_selected_facts() -> None:
    payload = {
        "datasetSnapshotId": "snapshot-1",
        "instrumentId": "instrument-1",
        "listingId": "listing-1",
        "quoteCurrency": "CLP",
        "asOf": "2026-09-13T12:00:00Z",
        "factIds": ["price-1"],
        "priceFactId": "price-1",
        "fxFactId": "fx-1",
        "shareBasisId": "basis-1",
        "selectionPolicyVersion": "selection-v1",
        "periodPolicyVersion": "period-v1",
        "contentHash": "1" * 64,
    }
    with pytest.raises(ValidationError, match="fxFactId"):
        DatasetSnapshot.model_validate(payload)


def test_scenario_probabilities_are_all_present_and_sum_to_one() -> None:
    assumption = {
        "assumptionId": "growth-1",
        "name": "growth",
        "value": "0.05",
        "unit": "ratio",
        "origin": "user",
        "rationale": "Synthetic review input",
        "evidenceIds": ["evidence-1"],
    }
    payload = {
        "scenarioSetRevision": "scenarios-r1",
        "instrumentId": "instrument-1",
        "revision": 1,
        "createdAt": "2026-09-13T12:00:00Z",
        "author": "local-user",
        "scenarios": [
            {"scenarioId": "base", "name": "Base", "assumptions": [assumption], "probability": "0.6"},
            {"scenarioId": "bear", "name": "Bear", "assumptions": [{**assumption, "assumptionId": "growth-2"}], "probability": "0.3"},
        ],
    }
    with pytest.raises(ValidationError, match="sum exactly to one"):
        ScenarioSetRevision.model_validate(payload)


def test_assessment_coverage_cannot_turn_two_resolved_points_into_100() -> None:
    payload = {
        "assessmentId": "assessment-1",
        "datasetSnapshotId": "snapshot-1",
        "instrumentId": "instrument-1",
        "listingId": "listing-1",
        "quoteCurrency": "USD",
        "mode": "financial",
        "scenarioSetRevision": "scenario-r1",
        "normalizationRevision": "normalization-r1",
        "thesisRevision": None,
        "portfolioSnapshotId": None,
        "engineVersions": {},
        "policyVersions": {"score": "proposed-v1"},
        "asOf": "2026-09-13T12:00:00Z",
        "results": [],
        "coverage": {
            "possiblePoints": 100,
            "resolvedPoints": 2,
            "creditedPoints": 2,
            "pendingPoints": 98,
            "minimumScore": 2,
            "maximumScore": 100
        },
        "blockers": ["insufficient_coverage"],
        "inputHash": "2" * 64
    }
    assessment = Assessment.model_validate(payload)
    assert assessment.coverage.resolved_points == 2
    assert assessment.coverage.possible_points == 100
    assert assessment.coverage.maximum_score == 100


def test_lineage_rejects_unknown_inputs() -> None:
    base = {
        "factId": "derived-1",
        "issuerId": "issuer-1",
        "instrumentId": None,
        "listingId": None,
        "concept": "revenue.normalized",
        "value": "1000",
        "unit": "money",
        "currency": "USD",
        "scale": 1,
        "originalValue": None,
        "originalUnit": None,
        "originalScale": None,
        "period": {"kind": "duration", "start": "2025-01-01", "end": "2025-12-31", "label": "FY", "fiscalYear": 2025, "fiscalQuarter": None},
        "context": {"consolidated": True, "dimensions": {}, "taxonomy": "synthetic", "tag": "Revenue", "shareBasis": "not_applicable", "shareBasisId": None},
        "publishedAt": None,
        "firstSeenAt": "2026-01-01T00:00:00Z",
        "retrievedAt": "2026-01-01T00:00:00Z",
        "timestampPrecision": "unknown",
        "origin": "derived",
        "availability": "available",
        "missingReason": None,
        "quality": {"freshness": "current", "reconciliation": "not_checked", "validation": "valid"},
        "evidence": [],
        "inputFactIds": ["missing-input"],
        "transformation": {"kind": "normalization", "name": "normalize", "version": "v1", "parameters": {"method": "manual-bridge", "rationale": "Synthetic adjustment"}, "fxFactId": None, "shareBasisId": None, "adjustmentIds": ["adjustment-1"]}
    }
    fact = Fact.model_validate(base)
    with pytest.raises(ValueError, match="unknown input fact"):
        validate_lineage([fact])
