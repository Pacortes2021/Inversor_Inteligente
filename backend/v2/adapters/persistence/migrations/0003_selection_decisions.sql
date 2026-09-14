CREATE TABLE selection_decisions (
    selection_decision_id TEXT PRIMARY KEY,
    issuer_id TEXT NOT NULL REFERENCES issuers(issuer_id) ON DELETE RESTRICT,
    instrument_id TEXT REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    listing_id TEXT REFERENCES listings(listing_id) ON DELETE RESTRICT,
    concept TEXT NOT NULL,
    period_end TEXT NOT NULL,
    as_of TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    selected_fact_id TEXT REFERENCES observations(fact_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX selection_decisions_lookup ON selection_decisions(
    issuer_id, instrument_id, listing_id, concept, period_end, as_of
);

CREATE TABLE selection_candidates (
    selection_decision_id TEXT NOT NULL REFERENCES selection_decisions(selection_decision_id) ON DELETE RESTRICT,
    fact_id TEXT NOT NULL REFERENCES observations(fact_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY(selection_decision_id, fact_id),
    UNIQUE(selection_decision_id, ordinal)
);

CREATE TRIGGER selection_decisions_are_immutable_update
BEFORE UPDATE ON selection_decisions BEGIN
    SELECT RAISE(ABORT, 'selection decisions are immutable');
END;
CREATE TRIGGER selection_decisions_are_immutable_delete
BEFORE DELETE ON selection_decisions BEGIN
    SELECT RAISE(ABORT, 'selection decisions are immutable');
END;
