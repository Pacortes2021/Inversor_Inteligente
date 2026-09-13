"""Two-layer JSON Schema and semantic contract validation."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ValidationError

from .domain import Fact, FcffSimulationRequest
from .domain.errors import ContractViolation, ErrorCode


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "docs" / "rework" / "contracts"
TModel = TypeVar("TModel", bound=BaseModel)


@dataclass(frozen=True)
class ValidationFailure:
    layer: str
    code: str
    path: str
    message: str


SCHEMAS: dict[str, tuple[Path, type[BaseModel]]] = {
    "fact": (CONTRACT_DIR / "fact.schema.json", Fact),
    "fcff-request": (CONTRACT_DIR / "fcff-request.schema.json", FcffSimulationRequest),
}


def _pointer(parts: list[Any]) -> str:
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in parts)


def _schema_code(schema_name: str, payload: dict[str, Any], path: str) -> str:
    if schema_name == "fact":
        if payload.get("availability") != "available" and payload.get("value") is not None:
            return ErrorCode.MISSING_MUST_HAVE_NULL_VALUE.value
        if payload.get("concept") in {"price.close", "price.open", "price.high", "price.low"}:
            if not payload.get("listingId") or not payload.get("instrumentId"):
                return ErrorCode.LISTING_REQUIRED.value
    return ErrorCode.VALIDATION_ERROR.value


def validate_structure(schema_name: str, payload: dict[str, Any]) -> ValidationFailure | None:
    schema_path, _ = SCHEMAS[schema_name]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if not errors:
        return None
    error = errors[0]
    path = _pointer(list(error.absolute_path))
    return ValidationFailure(
        layer="json_schema",
        code=_schema_code(schema_name, payload, path),
        path=path,
        message=error.message,
    )


def _semantic_failure(error: ValidationError) -> ValidationFailure:
    first = error.errors(include_url=False)[0]
    cause = (first.get("ctx") or {}).get("error")
    path = _pointer(list(first.get("loc") or ()))
    if isinstance(cause, ContractViolation):
        return ValidationFailure(
            layer="semantic",
            code=cause.code.value,
            path=cause.path or path,
            message=str(cause),
        )
    return ValidationFailure(
        layer="semantic",
        code=ErrorCode.VALIDATION_ERROR.value,
        path=path,
        message=first["msg"],
    )


def validate_payload(schema_name: str, payload: dict[str, Any]) -> tuple[BaseModel | None, ValidationFailure | None]:
    structural = validate_structure(schema_name, payload)
    if structural is not None:
        return None, structural
    _, model = SCHEMAS[schema_name]
    try:
        return model.model_validate(payload), None
    except ValidationError as error:
        return None, _semantic_failure(error)


def apply_json_pointer_replacements(payload: dict[str, Any], replacements: dict[str, Any]) -> dict[str, Any]:
    """Apply the small RFC 6901 replacement subset used by negative fixtures."""

    result = deepcopy(payload)
    for pointer, value in replacements.items():
        parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
        target: Any = result
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        leaf = parts[-1]
        if isinstance(target, list):
            target[int(leaf)] = value
        else:
            target[leaf] = value
    return result
