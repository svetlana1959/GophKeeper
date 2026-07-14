-- migrate:up
-- Append-only log of signed device trust certs (vouch/revoke) — the transport
-- for the M4 trust graph. The server stores certs opaquely and NEVER verifies
-- signatures (clients do); it enforces only that each issuer's issuer_seq is
-- contiguous (the UNIQUE below plus a service-level next==last+1 check), so an
-- issuer's certs form a gap-free chain. log_seq is a global monotonic cursor;
-- clients pull "certs since log_seq" and filter by account_id, mirroring
-- secret_seq.
CREATE SEQUENCE trust_cert_seq;

CREATE TABLE trust_certs (
    id               UUID        PRIMARY KEY,
    account_id       UUID        NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    issuer_device_id UUID        NOT NULL REFERENCES devices (id) ON DELETE CASCADE,
    issuer_seq       BIGINT      NOT NULL,
    kind             TEXT        NOT NULL,
    payload          JSONB       NOT NULL,
    log_seq          BIGINT      NOT NULL DEFAULT nextval('trust_cert_seq'),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (issuer_device_id, issuer_seq)
);

ALTER SEQUENCE trust_cert_seq OWNED BY trust_certs.log_seq;
CREATE INDEX idx_trust_certs_account_log ON trust_certs (account_id, log_seq);

-- migrate:down
DROP TABLE trust_certs;
DROP SEQUENCE IF EXISTS trust_cert_seq;
