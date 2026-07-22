-- migrate:up
-- A device may declare when it should expire (an idle TTL it sets at enroll and
-- extends via heartbeat). NULL means "never" — CLI devices don't expire. A
-- background reaper deletes devices past their expiry; ON DELETE CASCADE on
-- secret_recipients and trust_certs cleans up after them. The server never needs
-- to know a device is a browser: the device declares its own lifetime.
ALTER TABLE devices ADD COLUMN expires_at TIMESTAMPTZ;
CREATE INDEX idx_devices_expires_at ON devices (expires_at) WHERE expires_at IS NOT NULL;

-- migrate:down
DROP INDEX idx_devices_expires_at;
ALTER TABLE devices DROP COLUMN expires_at;
