-- migrate:up
-- Login identities for an account. One row per authentication method: today
-- ('password', email, argon2 hash); later ('google', subject, NULL) and other
-- providers slot in with no schema change. The account is the identity-agnostic
-- root; this table is how a human proves they own it on the web.
CREATE TABLE account_identities (
    id         UUID        PRIMARY KEY,
    account_id UUID        NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    provider   TEXT        NOT NULL,
    identifier TEXT        NOT NULL,
    secret     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, identifier)
);

CREATE INDEX idx_account_identities_account ON account_identities (account_id);

-- migrate:down
DROP TABLE account_identities;
