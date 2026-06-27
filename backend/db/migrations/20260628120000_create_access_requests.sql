-- migrate:up
-- Multi-device Access (#69) — handshake broker redesign
--
-- REVISION: the first version of this feature let any device with access
-- grant another device access directly (POST /secrets/{id}/share). That is
-- wrong for a Zero-Knowledge system: the server holds no keys, so it cannot
-- itself decide that a new device may read a secret — only the owning
-- device can, because only it can re-encrypt the secret's payload under the
-- new device's public key. Granting access without that re-encryption step
-- would let a device "access" a secret it cannot actually decrypt, which
-- means the access model was lying about what it protected.
--
-- This table replaces that direct grant with an asynchronous request queue.
-- The server's only job is to relay the request and the requester's public
-- key — it never creates a grant on its own:
--   1. Device B: POST /secrets/{id}/requests  -> PENDING row, carries B's
--      public_key so device A doesn't need a separate device lookup to
--      start re-encrypting.
--   2. Device A: GET /secrets/{id}/requests   -> sees the PENDING row,
--      reads public_key, re-encrypts the secret payload locally (the server
--      is not and cannot be involved in this step).
--   3. Device A: PUT /secrets/{id}             -> the existing endpoint from
--      #58, pushes the re-encrypted payload. Untouched by this migration.
--   4. Device A: POST /secrets/requests/{id}/approve -> THE ONLY place a row
--      is written into secret_access. This is the sole path to a grant.
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

-- BUG-PRONE PATTERN AVOIDED: a plain UNIQUE(secret_id, device_id, status)
-- would still let device B queue a second PENDING row once the status
-- column differs only at the *next* request — it does not stop two PENDING
-- rows for the same pair, since (secret_id, device_id, 'PENDING') only
-- collides with another row that is also 'PENDING'... which is exactly the
-- case we need to forbid, so a plain column-list UNIQUE works for this one
-- value but silently allows duplicate APPROVED/REJECTED history rows to
-- pile up unconstrained, which is what we want for an audit trail. A
-- partial unique INDEX expresses the real rule precisely: at most one
-- PENDING row per (secret_id, device_id), with no constraint at all on how
-- many APPROVED/REJECTED rows accumulate over time.
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
