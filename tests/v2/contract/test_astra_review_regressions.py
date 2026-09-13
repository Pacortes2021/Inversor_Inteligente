from __future__ import annotations

import json
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from backend.v2.contracts import CONTRACT_DIR
from backend.v2.domain import Fact, ShareBasis, validate_lineage


def fact_example() -> dict:
    return json.loads((CONTRACT_DIR / "fact.example.json").read_text(encoding="utf-8"))


def test_canonical_scale_is_literal_one_in_model_and_generated_schema() -> None:
    payload = fact_example()
    payload["scale"] = 1000
    with pytest.raises(ValidationError):
        Fact.model_validate(payload)

    schema = json.loads(
        (CONTRACT_DIR / "generated" / "fact-model.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(payload))

    for non_integer_one in (True, 1.0):
        payload["scale"] = non_integer_one
        with pytest.raises(ValidationError):
            Fact.model_validate(payload)


def test_second_precision_publication_cannot_follow_retrieval() -> None:
    payload = fact_example()
    payload["publishedAt"] = "2026-09-13T23:59:59Z"
    payload["retrievedAt"] = "2026-09-13T10:00:00Z"
    with pytest.raises(ValidationError, match="publishedAt must not be after retrievedAt"):
        Fact.model_validate(payload)


def test_date_precision_publication_does_not_invent_a_time() -> None:
    payload = fact_example()
    payload["publishedAt"] = "2026-02-20"
    payload["timestampPrecision"] = "date"
    fact = Fact.model_validate(payload)
    assert fact.published_at.isoformat() == "2026-02-20"
    assert fact.published_at.__class__.__name__ == "date"


def test_locator_without_identifiable_source_is_not_evidence() -> None:
    payload = fact_example()
    payload["evidence"] = [
        {
            "provider": "synthetic",
            "documentId": None,
            "url": None,
            "locator": "page 1",
            "sha256": None,
        }
    ]
    with pytest.raises(ValidationError, match="locator alone is insufficient"):
        Fact.model_validate(payload)


def derived_fact_payload() -> dict:
    payload = fact_example()
    payload.update(
        factId="derived-fx",
        value="900000000",
        currency="CLP",
        originalValue="1000000",
        originalUnit="USD",
        originalScale=1,
        origin="derived",
        evidence=[],
        inputFactIds=["reported-input", "fx-missing"],
        transformation={
            "kind": "fx",
            "name": "currency-conversion",
            "version": "v1",
            "parameters": {
                "sourceCurrency": "USD",
                "targetCurrency": "CLP",
                "operation": "multiply",
            },
            "fxFactId": "fx-missing",
            "shareBasisId": None,
            "adjustmentIds": [],
        },
    )
    return payload


def test_fx_fact_is_a_traversed_lineage_dependency() -> None:
    reported_payload = fact_example()
    reported_payload["factId"] = "reported-input"
    reported = Fact.model_validate(reported_payload)
    derived = Fact.model_validate(derived_fact_payload())
    with pytest.raises(ValueError, match="unknown input fact fx-missing"):
        validate_lineage([reported, derived])


def test_fx_transformation_requires_typed_parameters() -> None:
    payload = derived_fact_payload()
    payload["transformation"]["parameters"] = {}
    with pytest.raises(ValidationError):
        Fact.model_validate(payload)


def test_split_share_basis_requires_positive_reconciled_pre_and_post_shares() -> None:
    payload = {
        "shareBasisId": "basis-1",
        "instrumentId": "instrument-1",
        "asOf": "2026-09-13",
        "kind": "split_adjusted",
        "totalShares": "200",
        "components": [
            {
                "componentId": "common",
                "kind": "common",
                "shares": "200",
                "treatment": "included_in_denominator",
                "evidenceId": "evidence-1",
            }
        ],
        "splitFactor": "2",
        "preActionShares": "100",
        "postActionShares": "200",
        "targetDate": "2026-09-13",
        "corporateActionId": "split-1",
        "version": "v1",
    }
    assert ShareBasis.model_validate(payload).total_shares == "200"

    invalid = deepcopy(payload)
    invalid["splitFactor"] = "0"
    with pytest.raises(ValidationError, match="splitFactor must be positive"):
        ShareBasis.model_validate(invalid)

    invalid = deepcopy(payload)
    invalid["postActionShares"] = "199"
    with pytest.raises(ValidationError, match="preActionShares"):
        ShareBasis.model_validate(invalid)
