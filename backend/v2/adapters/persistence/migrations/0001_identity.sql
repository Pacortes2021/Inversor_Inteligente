CREATE TABLE issuers (
    issuer_id TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    domicile_country TEXT NOT NULL CHECK(length(domicile_country) = 2),
    identifiers_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE instruments (
    instrument_id TEXT PRIMARY KEY,
    issuer_id TEXT NOT NULL REFERENCES issuers(issuer_id) ON DELETE RESTRICT,
    type TEXT NOT NULL,
    share_class TEXT,
    rights_summary TEXT,
    isin TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX instruments_by_issuer ON instruments(issuer_id);

CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    mic TEXT NOT NULL,
    symbol TEXT NOT NULL,
    currency TEXT NOT NULL CHECK(length(currency) = 3),
    timezone TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'inactive')),
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    CHECK(valid_to IS NULL OR valid_to >= valid_from),
    UNIQUE(mic, symbol, valid_from)
);
CREATE INDEX listings_by_instrument ON listings(instrument_id);
CREATE INDEX listings_by_symbol ON listings(symbol, mic, valid_to);

CREATE TABLE provider_symbols (
    provider TEXT NOT NULL,
    capability TEXT NOT NULL,
    provider_symbol TEXT NOT NULL,
    listing_id TEXT NOT NULL REFERENCES listings(listing_id) ON DELETE RESTRICT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    resolution_evidence_id TEXT NOT NULL,
    CHECK(valid_to IS NULL OR valid_to >= valid_from),
    PRIMARY KEY(provider, capability, provider_symbol, valid_from),
    UNIQUE(provider, capability, listing_id, valid_from)
);
CREATE INDEX provider_symbols_current ON provider_symbols(provider, capability, provider_symbol, valid_to);

CREATE TABLE depositary_relations (
    relation_id TEXT PRIMARY KEY,
    adr_instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    underlying_instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    adr_shares INTEGER NOT NULL CHECK(adr_shares > 0),
    underlying_shares INTEGER NOT NULL CHECK(underlying_shares > 0),
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    evidence_id TEXT NOT NULL,
    CHECK(adr_instrument_id <> underlying_instrument_id),
    CHECK(valid_to IS NULL OR valid_to >= valid_from)
);

CREATE TABLE share_bases (
    share_basis_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    as_of TEXT NOT NULL,
    kind TEXT NOT NULL,
    total_shares TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL
);
