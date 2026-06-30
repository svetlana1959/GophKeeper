-- migrate:up
CREATE TABLE IF NOT EXISTS secret_access (
    secret_id  UUID NOT NULL REFERENCES secrets(id) ON DELETE CASCADE,
    device_id  UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (secret_id, device_id)
);

-- Sync looks up all secrets visible to a device.
CREATE INDEX IF NOT EXISTS idx_secret_access_device_id ON secret_access (device_id);

-- migrate:down
DROP TABLE IF EXISTS secret_access;