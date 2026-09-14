"""Serve the same canonical contract components that are checked into Git."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from ..domain import (
    Assessment,
    CorporateAction,
    DatasetSnapshot,
    DepositaryRelation,
    ErrorEnvelope,
    Fact,
    FcffSimulationRequest,
    Instrument,
    Issuer,
    Listing,
    MarketCalendarCoverage,
    MarketPrice,
    MarketSession,
    ProviderResult,
    ProviderSymbol,
    ScenarioSetRevision,
    SecCapture,
    ShareBasis,
    YahooCapture,
)


CANONICAL_MODELS: dict[str, type[BaseModel]] = {
    "assessment": Assessment,
    "corporate-action": CorporateAction,
    "dataset-snapshot": DatasetSnapshot,
    "depositary-relation": DepositaryRelation,
    "error-envelope": ErrorEnvelope,
    "fact-model": Fact,
    "fcff-simulation-request-model": FcffSimulationRequest,
    "instrument": Instrument,
    "issuer": Issuer,
    "listing": Listing,
    "market-calendar-coverage": MarketCalendarCoverage,
    "market-price": MarketPrice,
    "market-session": MarketSession,
    "provider-result": ProviderResult,
    "provider-symbol": ProviderSymbol,
    "scenario-set-revision": ScenarioSetRevision,
    "sec-capture": SecCapture,
    "share-basis": ShareBasis,
    "yahoo-capture": YahooCapture,
}


def component_refs(value: Any, component_name: str) -> Any:
    """Keep each model's private $defs addressable inside OpenAPI components."""

    if isinstance(value, str) and value.startswith("#/$defs/"):
        return value.replace("#/$defs/", f"#/components/schemas/{component_name}/$defs/", 1)
    if isinstance(value, dict):
        return {key: component_refs(item, component_name) for key, item in value.items()}
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
