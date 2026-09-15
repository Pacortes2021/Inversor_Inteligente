"""Transactional persistence for canonical identity entities."""

from __future__ import annotations

import hashlib
import json
import sqlite3

from ...domain.identity import (
    DepositaryRelation,
    Instrument,
    Issuer,
    Listing,
    ProviderSymbol,
    ShareBasis,
)
from ...domain.common import canonical_json, jsonable
from .connection import Database


class IdentityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def put_issuer(self, issuer: Issuer) -> None:
        identifiers = canonical_json([jsonable(item) for item in issuer.identifiers])
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO issuers(issuer_id, legal_name, domicile_country, identifiers_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(issuer_id) DO UPDATE SET
                    legal_name = excluded.legal_name,
                    domicile_country = excluded.domicile_country,
                    identifiers_json = excluded.identifiers_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (issuer.issuer_id, issuer.legal_name, issuer.domicile_country, identifiers),
            )

    def add_instrument(self, instrument: Instrument) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO instruments(instrument_id, issuer_id, type, share_class, rights_summary, isin)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    instrument.instrument_id,
                    instrument.issuer_id,
                    instrument.type,
                    instrument.share_class,
                    instrument.rights_summary,
                    instrument.isin,
                ),
            )

    def add_listing(self, listing: Listing) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO listings(
                    listing_id, instrument_id, mic, symbol, currency, timezone, status, valid_from, valid_to
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing.listing_id,
                    listing.instrument_id,
                    listing.mic,
                    listing.symbol,
                    listing.currency,
                    listing.timezone,
                    listing.status,
                    listing.valid_from.isoformat(),
                    listing.valid_to.isoformat() if listing.valid_to else None,
                ),
            )

    def add_provider_symbol(self, symbol: ProviderSymbol) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_symbols(
                    provider, capability, provider_symbol, listing_id,
                    valid_from, valid_to, resolution_evidence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol.provider,
                    symbol.capability,
                    symbol.provider_symbol,
                    symbol.listing_id,
                    symbol.valid_from.isoformat(),
                    symbol.valid_to.isoformat() if symbol.valid_to else None,
                    symbol.resolution_evidence_id,
                ),
            )

    def add_depositary_relation(self, relation: DepositaryRelation) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO depositary_relations(
                    relation_id, adr_instrument_id, underlying_instrument_id,
                    adr_shares, underlying_shares, valid_from, valid_to, evidence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation.relation_id,
                    relation.adr_instrument_id,
                    relation.underlying_instrument_id,
                    relation.adr_shares,
                    relation.underlying_shares,
                    relation.valid_from.isoformat(),
                    relation.valid_to.isoformat() if relation.valid_to else None,
                    relation.evidence_id,
                ),
            )

    def add_share_basis(self, basis: ShareBasis) -> None:
        payload = canonical_json(jsonable(basis))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT content_hash FROM share_bases WHERE share_basis_id = ?",
                (basis.share_basis_id,),
            ).fetchone()
            if existing:
                if existing["content_hash"] != digest:
                    raise ValueError("share basis IDs are immutable")
                return
            connection.execute(
                """
                INSERT INTO share_bases(
                    share_basis_id, instrument_id, as_of, kind, total_shares,
                    payload_json, content_hash, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    basis.share_basis_id,
                    basis.instrument_id,
                    basis.as_of.isoformat(),
                    basis.kind,
                    basis.total_shares,
                    payload,
                    digest,
                    basis.version,
                ),
            )

    def get_listing(self, listing_id: str) -> Listing | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM listings WHERE listing_id = ?", (listing_id,)
            ).fetchone()
        return None if row is None else Listing.model_validate(dict(row))

    def get_issuer(self, issuer_id: str) -> Issuer | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT issuer_id, legal_name, domicile_country, identifiers_json FROM issuers WHERE issuer_id = ?",
                (issuer_id,),
            ).fetchone()
        if row is None:
            return None
        return Issuer.model_validate(
            {
                "issuerId": row["issuer_id"],
                "legalName": row["legal_name"],
                "domicileCountry": row["domicile_country"],
                "identifiers": json.loads(row["identifiers_json"]),
            }
        )

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT instrument_id, issuer_id, type, share_class, rights_summary, isin FROM instruments WHERE instrument_id = ?",
                (instrument_id,),
            ).fetchone()
        return None if row is None else Instrument.model_validate(dict(row))

    def get_share_basis(self, share_basis_id: str) -> ShareBasis | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM share_bases WHERE share_basis_id = ?",
                (share_basis_id,),
            ).fetchone()
        return None if row is None else ShareBasis.model_validate_json(row["payload_json"])

    def provider_symbol_history(self, provider: str, capability: str, listing_id: str) -> list[ProviderSymbol]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT provider, capability, provider_symbol, listing_id,
                       valid_from, valid_to, resolution_evidence_id
                FROM provider_symbols
                WHERE provider = ? AND capability = ? AND listing_id = ?
                ORDER BY valid_from
                """,
                (provider, capability, listing_id),
            ).fetchall()
        return [ProviderSymbol.model_validate(dict(row)) for row in rows]
