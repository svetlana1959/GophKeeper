-- migrate:up
-- Single-use pairing codes for linking a new device into an account. Only the
-- hash of the code is stored, so a database leak never reveals usable codes.
CREATE TABLE invites (
    id          UUID        PRIMARY KEY,
    account_id  UUID        NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    code_hash   TEXT        NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invites_account ON invites (account_id);

-- migrate:down
DROP TABLE invites;
