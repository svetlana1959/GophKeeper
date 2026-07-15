CREATE TABLE IF NOT EXISTS trusted_devices (
    id              TEXT PRIMARY KEY,        -- device UUID
    device_name     TEXT NOT NULL,           -- human-readable name
    public_key      TEXT NOT NULL UNIQUE,    -- age public key (age1...)
    sign_public_key TEXT NOT NULL DEFAULT '',-- Ed25519 signing public key (base64), verifies trust certs
    is_active       INTEGER NOT NULL DEFAULT 1,
    updated_at      INTEGER NOT NULL         -- unix nanoseconds
);

-- The current local device only (1:1 with trusted_devices).
CREATE TABLE IF NOT EXISTS local_device (
    device_id       TEXT PRIMARY KEY REFERENCES trusted_devices(id) ON DELETE CASCADE,
    stored_key      BLOB NOT NULL,           -- age private key at rest (PIN-encrypted or plaintext+0600)
    sign_stored_key BLOB NOT NULL DEFAULT x'', -- Ed25519 signing private key at rest, same protection
    pin_protected   INTEGER NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS secrets (
    id         TEXT PRIMARY KEY,         -- secret UUID (matches the server ID)
    folder_id  TEXT,                     -- optional folder/group
    name       TEXT NOT NULL UNIQUE,     -- local lookup key
    payload    BLOB NOT NULL,            -- self-contained age ciphertext
    version    INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at INTEGER NOT NULL          -- unix nanoseconds
);

-- Which devices a secret is sealed to. age embeds the wrapped key in payload,
-- so this is a pure junction (no encrypted_dek).
CREATE TABLE IF NOT EXISTS secret_recipients (
    secret_id TEXT NOT NULL REFERENCES secrets(id)         ON DELETE CASCADE,
    device_id TEXT NOT NULL REFERENCES trusted_devices(id) ON DELETE CASCADE,
    PRIMARY KEY (secret_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_recipients_device ON secret_recipients(device_id);

-- Trust anchors: signing identities this device verified out-of-band (its own at
-- link, plus an inviter's roster via the invite code) and roots the trust graph
-- at. ComputeTrusted starts reachability from these. device_id is the
-- server-assigned id.
CREATE TABLE IF NOT EXISTS trust_anchors (
    device_id TEXT PRIMARY KEY,
    enc_pub   TEXT NOT NULL, -- age public key (also a valid recipient)
    sign_pub  TEXT NOT NULL  -- Ed25519 public key (base64), verifies the anchor's certs
);

-- Invites this device minted, kept until the joiner redeems them so the inviter
-- can verify the join proof under the code and vouch for the joiner. The code is
-- stored locally only (the server never sees it).
CREATE TABLE IF NOT EXISTS pending_invites (
    invite_id  TEXT PRIMARY KEY,
    code       TEXT NOT NULL
);

-- The highest verified cert we have seen from each issuer's chain: its seq and the
-- hash committing the whole prefix below it. Persisted so a hostile relay cannot
-- roll back or withhold an issuer's tail (e.g. suppress a revoke) without the head
-- appearing to regress — which the client then refuses.
CREATE TABLE IF NOT EXISTS trust_heads (
    issuer_id TEXT PRIMARY KEY,
    seq       INTEGER NOT NULL,
    hash      TEXT NOT NULL
);

-- This device's binding to the server account and the pull cursor (single row).
CREATE TABLE IF NOT EXISTS sync_state (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    account_id TEXT NOT NULL,
    device_id  TEXT NOT NULL,       -- server-assigned device id
    cursor     INTEGER NOT NULL DEFAULT 0
);

-- Per-secret reconciliation state against the server. server_version is the
-- version we last reconciled (0 = never pushed); dirty marks a local change
-- awaiting push. A secret with no row here is treated as dirty (never synced).
CREATE TABLE IF NOT EXISTS secret_sync (
    secret_id      TEXT PRIMARY KEY REFERENCES secrets(id) ON DELETE CASCADE,
    server_version INTEGER NOT NULL DEFAULT 0,
    dirty          INTEGER NOT NULL DEFAULT 1
);
