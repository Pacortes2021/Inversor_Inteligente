"""Immutable persistence for deterministic selection decisions."""

from __future__ import annotations

from ...domain.common import canonical_json, jsonable
from ...domain.policies import SelectionDecision
from .connection import Database


class SelectionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, decision: SelectionDecision) -> SelectionDecision:
        payload = canonical_json(jsonable(decision))
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT payload_json FROM selection_decisions WHERE selection_decision_id = ?",
                (decision.selection_decision_id,),
            ).fetchone()
            if existing is not None:
                stored = SelectionDecision.model_validate_json(existing["payload_json"])
                if stored.content_hash != decision.content_hash:
                    raise ValueError("selection decision IDs are immutable")
                return stored
            query = decision.query
            connection.execute(
                """
                INSERT INTO selection_decisions(
                    selection_decision_id, issuer_id, instrument_id, listing_id,
                    concept, period_end, as_of, mode, status, selected_fact_id,
                    policy_version, payload_json, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.selection_decision_id,
                    query.issuer_id,
                    query.instrument_id,
                    query.listing_id,
                    query.concept,
                    query.period.end.isoformat(),
                    query.as_of.isoformat(),
                    query.mode,
                    decision.status,
                    decision.selected_fact_id,
                    decision.policy_version,
                    payload,
                    decision.content_hash,
                ),
            )
            for ordinal, fact_id in enumerate(decision.candidate_fact_ids):
                connection.execute(
                    "INSERT INTO selection_candidates(selection_decision_id, fact_id, ordinal) VALUES (?, ?, ?)",
                    (decision.selection_decision_id, fact_id, ordinal),
                )
        return decision

    def get(self, decision_id: str) -> SelectionDecision | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM selection_decisions WHERE selection_decision_id = ?",
                (decision_id,),
            ).fetchone()
        return None if row is None else SelectionDecision.model_validate_json(row["payload_json"])
