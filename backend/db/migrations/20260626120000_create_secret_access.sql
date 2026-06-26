-- migrate:up
--
-- There is no account/auth layer yet (tracked separately), so "trust" is
-- modeled directly between devices and secrets rather than through a user:
-- a device can read/write a secret only if a row exists here granting it.
-- The device that stores a secret is granted access automatically (see
-- SecretService.store); other devices get access only via an explicit grant.
CREATE TABLE IF NOT EXISTS secret_access (
    secret_id  UUID NOT NULL REFERENCES secrets(id) ON DELETE CASCADE,
    device_id  UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (secret_id, device_id)
);

-- Reverse lookup: "all secrets this device can see" is the hot path on every
-- sync, so it needs its own index — the primary key alone only serves
-- "all devices for a secret" efficiently.
CREATE INDEX IF NOT EXISTS idx_secret_access_device_id ON secret_access (device_id);

-- migrate:down
DROP TABLE IF EXISTS secret_access;
