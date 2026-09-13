CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK(length(sha256) = 64),
    relative_path TEXT NOT NULL,
    source_url TEXT,
    media_type TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
    UNIQUE(provider, sha256),
    UNIQUE(relative_path)
);

CREATE TABLE observations (
    fact_id TEXT PRIMARY KEY,
    issuer_id TEXT NOT NULL REFERENCES issuers(issuer_id) ON DELETE RESTRICT,
    instrument_id TEXT REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    listing_id TEXT REFERENCES listings(listing_id) ON DELETE RESTRICT,
    concept TEXT NOT NULL,
    value_decimal TEXT,
    unit TEXT NOT NULL,
    currency TEXT,
    availability TEXT NOT NULL,
    period_kind TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT NOT NULL,
    period_label TEXT NOT NULL,
    published_at TEXT,
    first_seen_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    origin TEXT NOT NULL,
    provider_key TEXT,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX observations_selection_key ON observations(
    issuer_id, concept, period_end, unit, currency, instrument_id, listing_id
);
CREATE INDEX observations_available_at ON observations(published_at, first_seen_at, retrieved_at);

CREATE TABLE observation_inputs (
    fact_id TEXT NOT NULL REFERENCES observations(fact_id) ON DELETE RESTRICT,
    input_fact_id TEXT NOT NULL REFERENCES observations(fact_id) ON DELETE RESTRICT,
    PRIMARY KEY(fact_id, input_fact_id),
    CHECK(fact_id <> input_fact_id)
);

CREATE TABLE evidence_links (
    fact_id TEXT NOT NULL REFERENCES observations(fact_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL,
    provider TEXT NOT NULL,
    document_id TEXT REFERENCES documents(document_id) ON DELETE RESTRICT,
    url TEXT,
    locator TEXT,
    sha256 TEXT,
    PRIMARY KEY(fact_id, ordinal)
);

CREATE TRIGGER documents_are_immutable_update
BEFORE UPDATE ON documents BEGIN
    SELECT RAISE(ABORT, 'documents are immutable');
END;
CREATE TRIGGER documents_are_immutable_delete
BEFORE DELETE ON documents BEGIN
    SELECT RAISE(ABORT, 'documents are immutable');
END;
CREATE TRIGGER observations_are_immutable_update
BEFORE UPDATE ON observations BEGIN
    SELECT RAISE(ABORT, 'observations are immutable');
END;
CREATE TRIGGER observations_are_immutable_delete
BEFORE DELETE ON observations BEGIN
    SELECT RAISE(ABORT, 'observations are immutable');
END;
