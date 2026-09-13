#!/usr/bin/env python3
"""Regenerate checked-in JSON Schemas from canonical Pydantic contracts."""

from __future__ import annotations

import json
from pathlib import Path

from backend.v2.domain import (
    Assessment,
    DatasetSnapshot,
    DepositaryRelation,
    ErrorEnvelope,
    Fact,
    FcffSimulationRequest,
    Instrument,
    Issuer,
    Listing,
    ProviderResult,
    ProviderSymbol,
    ScenarioSetRevision,
    ShareBasis,
)
from backend.v2.bootstrap import create_app


OUTPUT = Path("docs/rework/contracts/generated")
MODELS = {
    "assessment": Assessment,
    "dataset-snapshot": DatasetSnapshot,
    "depositary-relation": DepositaryRelation,
    "error-envelope": ErrorEnvelope,
    "fact-model": Fact,
    "fcff-simulation-request-model": FcffSimulationRequest,
    "instrument": Instrument,
    "issuer": Issuer,
    "listing": Listing,
    "provider-result": ProviderResult,
    "provider-symbol": ProviderSymbol,
    "scenario-set-revision": ScenarioSetRevision,
    "share-basis": ShareBasis,
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    component_schemas = {}
    for name, model in MODELS.items():
        schema = model.model_json_schema(by_alias=True, mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:inversor:{name}:v2"
        path = OUTPUT / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        component_schemas[name] = _component_refs(schema, name)

    openapi = create_app().openapi()
    openapi.setdefault("components", {}).setdefault("schemas", {}).update(component_schemas)
    (Path("docs/rework/contracts") / "openapi.json").write_text(
        json.dumps(openapi, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _component_refs(value, component_name: str):
    """Keep each model's private $defs addressable inside OpenAPI components."""

    if isinstance(value, dict):
        return {
            key: (
                item.replace("#/$defs/", f"#/components/schemas/{component_name}/$defs/")
                if key == "$ref" and isinstance(item, str)
                else _component_refs(item, component_name)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_component_refs(item, component_name) for item in value]
    return value


if __name__ == "__main__":
    main()
