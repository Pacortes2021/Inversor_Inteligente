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


def test_every_local_openapi_reference_resolves() -> None:
    openapi = json.loads(Path("docs/rework/contracts/openapi.json").read_text(encoding="utf-8"))

    def strings(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)
        elif isinstance(value, str):
            yield value

    references = [value for value in strings(openapi) if value.startswith("#/")]
    assert references
    for reference in references:
        target = openapi
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            target = target[int(part)] if isinstance(target, list) else target[part]
        assert target is not None
