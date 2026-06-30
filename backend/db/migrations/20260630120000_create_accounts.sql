-- migrate:up
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE accounts (
    id              UUID        PRIMARY KEY,
    recovery_pubkey TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE accounts;
