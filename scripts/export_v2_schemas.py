#!/usr/bin/env python3
"""Regenerate checked-in JSON Schemas from canonical Pydantic contracts."""

from __future__ import annotations

import json
from pathlib import Path

from backend.v2.api.openapi import CANONICAL_MODELS
from backend.v2.bootstrap import create_app


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "rework" / "contracts"
OUTPUT = CONTRACTS / "generated"
def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, model in CANONICAL_MODELS.items():
        schema = model.model_json_schema(by_alias=True, mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:inversor:{name}:v2"
        path = OUTPUT / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    openapi = create_app().openapi()
    (CONTRACTS / "openapi.json").write_text(
        json.dumps(openapi, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
