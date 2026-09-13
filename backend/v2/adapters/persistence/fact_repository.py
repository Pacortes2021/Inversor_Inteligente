"""Immutable document and canonical fact repository."""

from __future__ import annotations

import hashlib
import json
import sqlite3

from ...domain import Document, Fact
from ...domain.common import jsonable
from .connection import Database
from .identity_repository import canonical_json


class FactRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add_document(self, document: Document) -> Document:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE provider = ? AND sha256 = ?",
                (document.provider, document.sha256),
            ).fetchone()
            if row:
                return self._document_from_row(row)
            connection.execute(
                """
                INSERT INTO documents(
                    document_id, provider, sha256, relative_path, source_url,
                    media_type, fetched_at, size_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.document_id,
                    document.provider,
                    document.sha256,
                    document.relative_path,
                    str(document.source_url) if document.source_url else None,
                    document.media_type,
                    document.fetched_at.isoformat(),
                    document.size_bytes,
                ),
            )
        return document

    def get_document(self, document_id: str) -> Document | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        return None if row is None else self._document_from_row(row)

    def add_fact(self, fact: Fact) -> Fact:
        payload = canonical_json(jsonable(fact))
        content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT payload_json, content_hash FROM observations WHERE fact_id = ?",
                (fact.fact_id,),
            ).fetchone()
            if existing:
                if existing["content_hash"] != content_hash:
                    raise ValueError("fact IDs are immutable")
                return Fact.model_validate_json(existing["payload_json"])

            provider_key = fact.evidence[0].provider if fact.evidence else None
            connection.execute(
                """
                INSERT INTO observations(
                    fact_id, issuer_id, instrument_id, listing_id, concept,
                    value_decimal, unit, currency, availability, period_kind,
                    period_start, period_end, period_label, published_at,
                    first_seen_at, retrieved_at, origin, provider_key,
                    payload_json, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.fact_id,
                    fact.issuer_id,
                    fact.instrument_id,
                    fact.listing_id,
                    fact.concept,
                    fact.value,
                    fact.unit,
                    fact.currency,
                    fact.availability,
                    fact.period.kind,
                    fact.period.start.isoformat() if fact.period.start else None,
                    fact.period.end.isoformat(),
                    fact.period.label,
                    fact.published_at.isoformat() if fact.published_at else None,
                    fact.first_seen_at.isoformat(),
                    fact.retrieved_at.isoformat(),
                    fact.origin,
                    provider_key,
                    payload,
                    content_hash,
                ),
            )
            for input_id in fact.fact_dependency_ids():
                connection.execute(
                    "INSERT INTO observation_inputs(fact_id, input_fact_id) VALUES (?, ?)",
                    (fact.fact_id, input_id),
                )
            for ordinal, evidence in enumerate(fact.evidence):
                if evidence.document_id is not None:
                    document = connection.execute(
                        "SELECT provider, sha256 FROM documents WHERE document_id = ?",
                        (evidence.document_id,),
                    ).fetchone()
                    if document is None:
                        raise ValueError(f"unknown evidence document {evidence.document_id}")
                    if document["provider"] != evidence.provider:
                        raise ValueError("evidence provider does not match its document")
                    if evidence.sha256 is not None and document["sha256"] != evidence.sha256:
                        raise ValueError("evidence hash does not match its document")
                connection.execute(
                    """
                    INSERT INTO evidence_links(
                        fact_id, ordinal, provider, document_id, url, locator, sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact.fact_id,
                        ordinal,
                        evidence.provider,
                        evidence.document_id,
                        str(evidence.url) if evidence.url else None,
                        evidence.locator,
                        evidence.sha256,
                    ),
                )
        return fact

    def get_fact(self, fact_id: str) -> Fact | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM observations WHERE fact_id = ?", (fact_id,)
            ).fetchone()
        return None if row is None else Fact.model_validate_json(row["payload_json"])

    def list_facts(self, *, issuer_id: str, concept: str) -> list[Fact]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM observations
                WHERE issuer_id = ? AND concept = ?
                ORDER BY period_end, published_at, first_seen_at, fact_id
                """,
                (issuer_id, concept),
            ).fetchall()
        return [Fact.model_validate_json(row["payload_json"]) for row in rows]

    def fact_count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT count(*) FROM observations").fetchone()[0])

    @staticmethod
    def _document_from_row(row: sqlite3.Row) -> Document:
        return Document.model_validate(dict(row))
