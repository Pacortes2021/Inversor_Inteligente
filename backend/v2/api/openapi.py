"""Serve the same canonical contract components that are checked into Git."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from ..domain import (
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


CANONICAL_MODELS: dict[str, type[BaseModel]] = {
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


def component_refs(value: Any, component_name: str) -> Any:
    """Keep each model's private $defs addressable inside OpenAPI components."""

    if isinstance(value, dict):
        return {
            key: (
                item.replace("#/$defs/", f"#/components/schemas/{component_name}/$defs/")
                if key == "$ref" and isinstance(item, str)
                else component_refs(item, component_name)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [component_refs(item, component_name) for item in value]
    return value


def install_canonical_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for name, model in CANONICAL_MODELS.items():
            model_schema = model.model_json_schema(by_alias=True, mode="validation")
            components[name] = component_refs(model_schema, name)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
