"""Durable immutable snapshots and offline replay bundles."""

from __future__ import annotations

from ...domain.common import canonical_json, jsonable
from ...domain.facts import Fact
from ...domain.policies import SelectionDecision
from ...domain.snapshots import DatasetSnapshot
from .connection import Database


class SnapshotRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, snapshot: DatasetSnapshot, decision_ids: list[str]) -> DatasetSnapshot:
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("snapshot decision IDs must be unique")
        decision_ids = sorted(decision_ids)
        payload = canonical_json(jsonable(snapshot))
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT payload_json FROM snapshots WHERE dataset_snapshot_id = ?",
                (snapshot.dataset_snapshot_id,),
            ).fetchone()
            if existing is not None:
                stored = DatasetSnapshot.model_validate_json(existing["payload_json"])
                if stored.content_hash != snapshot.content_hash:
                    raise ValueError("snapshot IDs are immutable")
                stored_decisions = [
                    row["selection_decision_id"]
                    for row in connection.execute(
                        "SELECT selection_decision_id FROM snapshot_selections WHERE dataset_snapshot_id = ? ORDER BY ordinal",
                        (snapshot.dataset_snapshot_id,),
                    )
                ]
                if stored_decisions != decision_ids:
                    raise ValueError("snapshot decision membership is immutable")
                return stored
            listing = connection.execute(
                "SELECT instrument_id, currency FROM listings WHERE listing_id = ?",
                (snapshot.listing_id,),
            ).fetchone()
            if listing is None or listing["instrument_id"] != snapshot.instrument_id:
                raise ValueError("snapshot listing does not belong to its instrument")
            if listing["currency"] != snapshot.quote_currency:
                raise ValueError("snapshot quote currency does not match its listing")
            basis = connection.execute(
                "SELECT instrument_id FROM share_bases WHERE share_basis_id = ?",
                (snapshot.share_basis_id,),
            ).fetchone()
            if basis is None or basis["instrument_id"] != snapshot.instrument_id:
                raise ValueError("snapshot share basis does not belong to its instrument")
            facts = []
            for fact_id in snapshot.fact_ids:
                row = connection.execute(
                    "SELECT payload_json FROM observations WHERE fact_id = ?", (fact_id,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"unknown snapshot fact {fact_id}")
                facts.append(Fact.model_validate_json(row["payload_json"]))
            by_id = {fact.fact_id: fact for fact in facts}
            price = by_id.get(snapshot.price_fact_id)
            if (
                price is None
                or price.instrument_id != snapshot.instrument_id
                or price.listing_id != snapshot.listing_id
                or price.currency != snapshot.quote_currency
                or not price.concept.startswith("price.")
            ):
                raise ValueError("persisted price does not match snapshot identity")
            selected_ids: set[str] = set()
            for decision_id in decision_ids:
                row = connection.execute(
                    "SELECT payload_json FROM selection_decisions WHERE selection_decision_id = ?",
                    (decision_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"unknown selection decision {decision_id}")
                decision = SelectionDecision.model_validate_json(row["payload_json"])
                if (
                    decision.selected_fact_id is None
                    or decision.policy_version != snapshot.selection_policy_version
                    or decision.query.as_of != snapshot.as_of
                ):
                    raise ValueError("selection decision is incompatible with snapshot")
                selected_ids.add(decision.selected_fact_id)
            if selected_ids != set(snapshot.fact_ids):
                raise ValueError("selection decisions must resolve every snapshot fact exactly")
            connection.execute(
                """
                INSERT INTO snapshots(
                    dataset_snapshot_id, instrument_id, listing_id, quote_currency,
                    as_of, price_fact_id, fx_fact_id, share_basis_id,
                    selection_policy_version, period_policy_version, payload_json, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.dataset_snapshot_id,
                    snapshot.instrument_id,
                    snapshot.listing_id,
                    snapshot.quote_currency,
                    snapshot.as_of.isoformat(),
                    snapshot.price_fact_id,
                    snapshot.fx_fact_id,
                    snapshot.share_basis_id,
                    snapshot.selection_policy_version,
                    snapshot.period_policy_version,
                    payload,
                    snapshot.content_hash,
                ),
            )
            for ordinal, fact_id in enumerate(snapshot.fact_ids):
                connection.execute(
                    "INSERT INTO snapshot_facts(dataset_snapshot_id, fact_id, ordinal) VALUES (?, ?, ?)",
                    (snapshot.dataset_snapshot_id, fact_id, ordinal),
                )
            for ordinal, decision_id in enumerate(decision_ids):
                connection.execute(
                    "INSERT INTO snapshot_selections(dataset_snapshot_id, selection_decision_id, ordinal) VALUES (?, ?, ?)",
                    (snapshot.dataset_snapshot_id, decision_id, ordinal),
                )
        return snapshot

    def get(self, snapshot_id: str) -> DatasetSnapshot | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM snapshots WHERE dataset_snapshot_id = ?", (snapshot_id,)
            ).fetchone()
        return None if row is None else DatasetSnapshot.model_validate_json(row["payload_json"])

    def facts(self, snapshot_id: str) -> list[Fact]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT observations.payload_json FROM snapshot_facts
                JOIN observations USING(fact_id)
                WHERE dataset_snapshot_id = ? ORDER BY snapshot_facts.ordinal
                """,
                (snapshot_id,),
            ).fetchall()
        return [Fact.model_validate_json(row["payload_json"]) for row in rows]

    def decisions(self, snapshot_id: str) -> list[SelectionDecision]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT selection_decisions.payload_json FROM snapshot_selections
                JOIN selection_decisions USING(selection_decision_id)
                WHERE dataset_snapshot_id = ? ORDER BY snapshot_selections.ordinal
                """,
                (snapshot_id,),
            ).fetchall()
        return [SelectionDecision.model_validate_json(row["payload_json"]) for row in rows]
