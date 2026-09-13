from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_DIR = Path("docs/rework/contracts/generated")


def test_every_generated_contract_is_valid_draft_2020_12() -> None:
    paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    assert len(paths) >= 12
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(schema)


def test_openapi_contains_every_canonical_contract() -> None:
    openapi = json.loads(Path("docs/rework/contracts/openapi.json").read_text(encoding="utf-8"))
    assert openapi["openapi"].startswith("3.1")
    components = openapi["components"]["schemas"]
    expected = {path.name.removesuffix(".schema.json") for path in SCHEMA_DIR.glob("*.schema.json")}
    assert expected.issubset(components)
