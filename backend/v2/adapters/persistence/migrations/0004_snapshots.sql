CREATE TABLE snapshots (
    dataset_snapshot_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id) ON DELETE RESTRICT,
    listing_id TEXT NOT NULL REFERENCES listings(listing_id) ON DELETE RESTRICT,
    quote_currency TEXT NOT NULL,
    as_of TEXT NOT NULL,
    price_fact_id TEXT NOT NULL REFERENCES observations(fact_id) ON DELETE RESTRICT,
    fx_fact_id TEXT REFERENCES observations(fact_id) ON DELETE RESTRICT,
    share_basis_id TEXT NOT NULL REFERENCES share_bases(share_basis_id) ON DELETE RESTRICT,
    selection_policy_version TEXT NOT NULL,
    period_policy_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX snapshots_lookup ON snapshots(instrument_id, listing_id, as_of);

CREATE TABLE snapshot_facts (
    dataset_snapshot_id TEXT NOT NULL REFERENCES snapshots(dataset_snapshot_id) ON DELETE RESTRICT,
    fact_id TEXT NOT NULL REFERENCES observations(fact_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY(dataset_snapshot_id, fact_id),
    UNIQUE(dataset_snapshot_id, ordinal)
);

CREATE TABLE snapshot_selections (
    dataset_snapshot_id TEXT NOT NULL REFERENCES snapshots(dataset_snapshot_id) ON DELETE RESTRICT,
    selection_decision_id TEXT NOT NULL REFERENCES selection_decisions(selection_decision_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY(dataset_snapshot_id, selection_decision_id),
    UNIQUE(dataset_snapshot_id, ordinal)
);

CREATE TRIGGER snapshots_are_immutable_update
BEFORE UPDATE ON snapshots BEGIN
    SELECT RAISE(ABORT, 'snapshots are immutable');
END;
CREATE TRIGGER snapshots_are_immutable_delete
BEFORE DELETE ON snapshots BEGIN
    SELECT RAISE(ABORT, 'snapshots are immutable');
END;
CREATE TRIGGER snapshot_facts_are_immutable_update
BEFORE UPDATE ON snapshot_facts BEGIN
    SELECT RAISE(ABORT, 'snapshot membership is immutable');
END;
CREATE TRIGGER snapshot_facts_are_immutable_delete
BEFORE DELETE ON snapshot_facts BEGIN
    SELECT RAISE(ABORT, 'snapshot membership is immutable');
END;
CREATE TRIGGER snapshot_selections_are_immutable_update
BEFORE UPDATE ON snapshot_selections BEGIN
    SELECT RAISE(ABORT, 'snapshot membership is immutable');
END;
CREATE TRIGGER snapshot_selections_are_immutable_delete
BEFORE DELETE ON snapshot_selections BEGIN
    SELECT RAISE(ABORT, 'snapshot membership is immutable');
END;
