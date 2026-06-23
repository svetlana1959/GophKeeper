-- migrate:up
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE secrets (
    id          UUID        PRIMARY KEY,
    account_id  TEXT        NOT NULL,
    ciphertext  BYTEA       NOT NULL,
    version     INTEGER     NOT NULL DEFAULT 1,
    deleted     BOOLEAN     NOT NULL DEFAULT FALSE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_secrets_account ON secrets (account_id);

-- migrate:down
DROP TABLE secrets;
