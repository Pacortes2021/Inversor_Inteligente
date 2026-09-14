DROP INDEX cache_resource;

CREATE TRIGGER observations_require_coherent_identity
BEFORE INSERT ON observations BEGIN
    SELECT CASE
        WHEN NEW.instrument_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM instruments
            WHERE instrument_id = NEW.instrument_id AND issuer_id = NEW.issuer_id
        ) THEN RAISE(ABORT, 'fact instrument does not belong to issuer')
    END;
    SELECT CASE
        WHEN NEW.listing_id IS NOT NULL AND (
            NEW.instrument_id IS NULL OR NOT EXISTS (
                SELECT 1 FROM listings
                WHERE listing_id = NEW.listing_id AND instrument_id = NEW.instrument_id
            )
        ) THEN RAISE(ABORT, 'fact listing does not belong to instrument')
    END;
    SELECT CASE
        WHEN json_extract(NEW.payload_json, '$.context.shareBasisId') IS NOT NULL
          AND (
            NEW.instrument_id IS NULL OR NOT EXISTS (
                SELECT 1 FROM share_bases
                WHERE share_basis_id = json_extract(NEW.payload_json, '$.context.shareBasisId')
                  AND instrument_id = NEW.instrument_id
            )
          ) THEN RAISE(ABORT, 'fact share basis does not belong to instrument')
    END;
    SELECT CASE
        WHEN json_extract(NEW.payload_json, '$.transformation.shareBasisId') IS NOT NULL
          AND (
            NEW.instrument_id IS NULL OR NOT EXISTS (
                SELECT 1 FROM share_bases
                WHERE share_basis_id = json_extract(NEW.payload_json, '$.transformation.shareBasisId')
                  AND instrument_id = NEW.instrument_id
            )
          ) THEN RAISE(ABORT, 'fact transformation share basis does not belong to instrument')
    END;
    SELECT CASE
        WHEN json_extract(NEW.payload_json, '$.transformation.shareBasisId') IS NOT NULL
          AND json_extract(NEW.payload_json, '$.context.shareBasisId')
              IS NOT json_extract(NEW.payload_json, '$.transformation.shareBasisId')
        THEN RAISE(ABORT, 'fact context and transformation share bases do not match')
    END;
END;

CREATE TRIGGER listings_reject_overlapping_symbol_ranges
BEFORE INSERT ON listings
WHEN EXISTS (
    SELECT 1 FROM listings
    WHERE mic = NEW.mic
      AND symbol = NEW.symbol
      AND COALESCE(valid_to, '9999-12-31') >= NEW.valid_from
      AND COALESCE(NEW.valid_to, '9999-12-31') >= valid_from
)
BEGIN
    SELECT RAISE(ABORT, 'listing symbol validity ranges overlap');
END;

CREATE TRIGGER provider_symbols_reject_overlapping_ranges
BEFORE INSERT ON provider_symbols
WHEN EXISTS (
    SELECT 1 FROM provider_symbols
    WHERE provider = NEW.provider
      AND capability = NEW.capability
      AND (provider_symbol = NEW.provider_symbol OR listing_id = NEW.listing_id)
      AND COALESCE(valid_to, '9999-12-31') >= NEW.valid_from
      AND COALESCE(NEW.valid_to, '9999-12-31') >= valid_from
)
BEGIN
    SELECT RAISE(ABORT, 'provider symbol validity ranges overlap');
END;
