"""Deterministic selection by exact semantics and information cutoff."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone

from ..domain.common import canonical_json, jsonable
from ..domain.facts import Availability, Fact
from ..domain.policies import (
    FactSelectionQuery,
    SelectionDecision,
    SelectionPolicy,
    SelectionStatus,
)
from .reconcile import compare_candidates


def available_at(fact: Fact) -> datetime:
    if isinstance(fact.published_at, datetime):
        return fact.published_at
    if isinstance(fact.published_at, date):
        # A date-only disclosure cannot safely be used during that date.
        return datetime.combine(fact.published_at + timedelta(days=1), time.min, timezone.utc)
    return fact.first_seen_at


def _same_semantics(fact: Fact, query: FactSelectionQuery) -> bool:
    return all(
        (
            fact.issuer_id == query.issuer_id,
            fact.instrument_id == query.instrument_id,
            fact.listing_id == query.listing_id,
            fact.concept == query.concept,
            fact.unit == query.unit,
            fact.currency == query.currency,
            fact.period == query.period,
            fact.context == query.context,
        )
    )


def _provider(fact: Fact) -> str:
    return fact.evidence[0].provider if fact.evidence else "~unknown"


def _latest_per_provider(facts: list[Fact]) -> list[Fact]:
    latest: dict[str, Fact] = {}
    for fact in facts:
        provider = _provider(fact)
        previous = latest.get(provider)
        order = (available_at(fact), fact.first_seen_at, fact.fact_id)
        if previous is None or order > (available_at(previous), previous.first_seen_at, previous.fact_id):
            latest[provider] = fact
    return list(latest.values())


def _priority_key(fact: Fact, policy: SelectionPolicy) -> tuple[int, float, str]:
    provider = _provider(fact)
    try:
        priority = policy.provider_priority.index(provider)
    except ValueError:
        priority = len(policy.provider_priority)
    return priority, -available_at(fact).timestamp(), fact.fact_id


def select_fact(
    facts: list[Fact], query: FactSelectionQuery, policy: SelectionPolicy
) -> SelectionDecision:
    eligible = sorted(
        [fact for fact in facts if _same_semantics(fact, query) and available_at(fact) <= query.as_of],
        key=lambda fact: fact.fact_id,
    )
    resolved_candidates = _latest_per_provider(eligible)
    available = [
        fact for fact in resolved_candidates if fact.availability == Availability.AVAILABLE
    ]
    differences = compare_candidates(available, policy)

    if any(item.material for item in differences):
        status = SelectionStatus.CONFLICT
        selected = None
        rule = "material_conflict_blocks"
    elif available:
        status = SelectionStatus.SELECTED
        selected = min(available, key=lambda fact: _priority_key(fact, policy)).fact_id
        rule = "compatible_provider_priority"
    else:
        status = SelectionStatus.MISSING
        selected = None
        rule = "no_available_candidate"

    seed = {
        "query": jsonable(query),
        "policy": jsonable(policy),
        "candidateFactIds": [fact.fact_id for fact in eligible],
        "selectedFactId": selected,
        "status": status,
        "rule": rule,
        "differences": [jsonable(item) for item in differences],
    }
    content_hash = hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()
    return SelectionDecision(
        selectionDecisionId=f"selection-{content_hash[:24]}",
        query=query,
        policyVersion=policy.version,
        candidateFactIds=seed["candidateFactIds"],
        selectedFactId=selected,
        status=status,
        rule=rule,
        differences=differences,
        contentHash=content_hash,
    )
