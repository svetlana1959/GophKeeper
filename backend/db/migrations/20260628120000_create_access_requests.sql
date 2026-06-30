-- migrate:up
-- Multi-device Access (#69): an asynchronous request queue for sharing a secret
-- with a new device. The server only relays the request; a grant is written into
-- secret_access only when an already-trusted device approves (see
-- services/access_request_service.py).
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

-- At most one PENDING request per (secret_id, device_id); settled (APPROVED/
-- REJECTED) rows accumulate freely as history. A partial unique index expresses
-- exactly this — a plain column-list UNIQUE could not.
CREATE UNIQUE INDEX IF NOT EXISTS uq_access_requests_pending
    ON access_requests (secret_id, device_id)
    WHERE status = 'PENDING';

-- Hot paths: "what's pending for this secret" (device A polling) and "what's
-- pending for this device" (device B checking its own requests).
CREATE INDEX IF NOT EXISTS idx_access_requests_secret_id ON access_requests (secret_id);
CREATE INDEX IF NOT EXISTS idx_access_requests_device_id ON access_requests (device_id);

-- migrate:down
DROP TABLE IF EXISTS access_requests;
DROP TYPE IF EXISTS access_request_status;
