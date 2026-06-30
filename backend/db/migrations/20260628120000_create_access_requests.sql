-- migrate:up
DO $$ BEGIN
    CREATE TYPE access_request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS access_requests (
    id          UUID PRIMARY KEY,
    secret_id   UUID NOT NULL REFERENCES secrets(id) ON DELETE CASCADE,
    device_id   UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    status      access_request_status NOT NULL DEFAULT 'PENDING',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One pending request per device/secret; settled rows remain as history.
CREATE UNIQUE INDEX IF NOT EXISTS uq_access_requests_pending
    ON access_requests (secret_id, device_id)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_access_requests_secret_id ON access_requests (secret_id);
CREATE INDEX IF NOT EXISTS idx_access_requests_device_id ON access_requests (device_id);

-- migrate:down
DROP TABLE IF EXISTS access_requests;
DROP TYPE IF EXISTS access_request_status;
