-- migrate:up
-- A device now belongs to an account and tracks a trust lifecycle
-- (pending/active/revoked) instead of a bare is_active flag. The public key is
-- the device's server-facing identity, so it must be unique.
ALTER TABLE devices ADD COLUMN account_id UUID REFERENCES accounts (id) ON DELETE CASCADE;
ALTER TABLE devices ADD COLUMN status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE devices ADD COLUMN last_seen_at TIMESTAMPTZ;
ALTER TABLE devices DROP COLUMN is_active;
ALTER TABLE devices ADD CONSTRAINT devices_public_key_key UNIQUE (public_key);
CREATE INDEX idx_devices_account ON devices (account_id);

-- migrate:down
DROP INDEX idx_devices_account;
ALTER TABLE devices DROP CONSTRAINT devices_public_key_key;
ALTER TABLE devices ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE devices DROP COLUMN last_seen_at;
ALTER TABLE devices DROP COLUMN status;
ALTER TABLE devices DROP COLUMN account_id;
