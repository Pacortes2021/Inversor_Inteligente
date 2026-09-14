CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    request_json TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'partial', 'succeeded', 'failed', 'cancelled')),
    attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt >= 0),
    max_attempts INTEGER NOT NULL CHECK(max_attempts >= 1),
    progress TEXT NOT NULL,
    lease_owner TEXT,
    lease_expires_at TEXT,
    next_attempt_at TEXT NOT NULL,
    cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0, 1)),
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX jobs_claimable ON jobs(status, next_attempt_at, lease_expires_at);

CREATE TABLE provider_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE RESTRICT,
    attempt INTEGER NOT NULL,
    provider TEXT NOT NULL,
    capability TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    retry_after_seconds INTEGER,
    attempted_at TEXT NOT NULL,
    UNIQUE(job_id, attempt)
);
CREATE TRIGGER provider_attempts_are_immutable_update
BEFORE UPDATE ON provider_attempts BEGIN
    SELECT RAISE(ABORT, 'provider attempts are immutable');
END;
CREATE TRIGGER provider_attempts_are_immutable_delete
BEFORE DELETE ON provider_attempts BEGIN
    SELECT RAISE(ABORT, 'provider attempts are immutable');
END;

CREATE TABLE cache_entries (
    cache_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    capability TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    valid_payload_json TEXT,
    valid_fetched_at TEXT,
    valid_expires_at TEXT,
    last_attempt_at TEXT NOT NULL,
    last_error TEXT,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX cache_resource ON cache_entries(provider, capability, resource_key, parser_version);
