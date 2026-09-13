"""Versioned scenario and assumption contracts; no valuation engine lives here."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, DecimalString, Identifier, decimal_value, utc_datetime
from .errors import ContractViolation, ErrorCode


class AssumptionOrigin(str, Enum):
    USER = "user"
    POLICY_TEMPLATE = "policy_template"
    DERIVED = "derived"


class Assumption(CanonicalModel):
    assumption_id: Identifier
    name: Identifier
    value: DecimalString
    unit: Identifier
    origin: AssumptionOrigin
    rationale: str = Field(min_length=1)
    evidence_ids: list[Identifier] = Field(min_length=1)


class Scenario(CanonicalModel):
    scenario_id: Identifier
    name: Identifier
    assumptions: list[Assumption] = Field(min_length=1)
    probability: DecimalString | None = None

    @model_validator(mode="after")
    def probability_domain(self) -> "Scenario":
        if self.probability is not None and not Decimal("0") <= decimal_value(self.probability) <= Decimal("1"):
            raise ValueError("probability must be between zero and one")
        assumption_ids = [item.assumption_id for item in self.assumptions]
        if len(assumption_ids) != len(set(assumption_ids)):
            raise ValueError("assumption IDs must be unique inside a scenario")
        return self


class ScenarioSetRevision(CanonicalModel):
    scenario_set_revision: Identifier
    instrument_id: Identifier
    revision: int = Field(ge=1)
    created_at: datetime
    author: Identifier
    scenarios: list[Scenario] = Field(min_length=1)

    @field_validator("created_at")
    @classmethod
    def created_at_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)

    @model_validator(mode="after")
    def probabilities_are_complete_or_absent(self) -> "ScenarioSetRevision":
        probabilities = [scenario.probability for scenario in self.scenarios]
        supplied = [value for value in probabilities if value is not None]
        if supplied and len(supplied) != len(probabilities):
            raise ContractViolation(
                ErrorCode.PROBABILITIES_MUST_SUM_TO_ONE,
                "probabilities must be supplied for every scenario or none",
                "/scenarios",
            )
        if supplied and sum(decimal_value(value) for value in supplied) != Decimal("1"):
            raise ContractViolation(
                ErrorCode.PROBABILITIES_MUST_SUM_TO_ONE,
                "scenario probabilities must sum exactly to one",
                "/scenarios",
            )
        scenario_ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario IDs must be unique")
        return self
