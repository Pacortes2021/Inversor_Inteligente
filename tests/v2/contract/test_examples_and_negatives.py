from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.v2.contracts import (
    CONTRACT_DIR,
    apply_json_pointer_replacements,
    validate_payload,
    validate_structure,
)
from backend.v2.domain import Fact, FcffSimulationRequest


def load(name: str):
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("schema_name", "example_name", "model"),
    [
        ("fact", "fact.example.json", Fact),
        ("fcff-request", "fcff-request.example.json", FcffSimulationRequest),
    ],
)
def test_published_examples_pass_both_layers(schema_name, example_name, model) -> None:
    payload = load(example_name)
    parsed, failure = validate_payload(schema_name, payload)
    assert failure is None
    assert isinstance(parsed, model)


@pytest.mark.parametrize("case", load("invalid-cases.json"), ids=lambda case: case["id"])
def test_published_negative_cases_fail_at_declared_layer_and_code(case) -> None:
    base_name = "fact.example.json" if case["schema"] == "fact" else "fcff-request.example.json"
    payload = apply_json_pointer_replacements(load(base_name), case["replace"])
    parsed, failure = validate_payload(case["schema"], payload)
    assert parsed is None
    assert failure is not None
    assert failure.layer == case["expectedLayer"]
    assert failure.code == case["expectedCode"]


def test_missing_remains_null_and_is_not_coerced_to_zero() -> None:
    payload = load("fact.example.json")
    payload.update(value=None, availability="missing", missingReason="not_reported")
    parsed, failure = validate_payload("fact", payload)
    assert failure is None
    assert parsed is not None
    assert parsed.value is None


def test_format_checker_rejects_invalid_dates_and_urls() -> None:
    payload = load("fact.example.json")
    payload["period"]["end"] = "not-a-date"
    failure = validate_structure("fact", payload)
    assert failure is not None and failure.layer == "json_schema"

    payload = load("fact.example.json")
    payload["evidence"][0]["url"] = "not a URI"
    failure = validate_structure("fact", payload)
    assert failure is not None and failure.layer == "json_schema"
