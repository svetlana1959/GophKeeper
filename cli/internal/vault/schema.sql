CREATE TABLE IF NOT EXISTS trusted_devices (
    id          TEXT PRIMARY KEY,        -- device UUID
    device_name TEXT NOT NULL,           -- human-readable name
    public_key  TEXT NOT NULL UNIQUE,    -- age public key (age1...)
    is_active   INTEGER NOT NULL DEFAULT 1,
    updated_at  INTEGER NOT NULL         -- unix nanoseconds
);

-- The current local device only (1:1 with trusted_devices).
CREATE TABLE IF NOT EXISTS local_device (
    device_id     TEXT PRIMARY KEY REFERENCES trusted_devices(id) ON DELETE CASCADE,
    stored_key    BLOB NOT NULL,         -- age private key at rest (PIN-encrypted or plaintext+0600)
    pin_protected INTEGER NOT NULL DEFAULT 0,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
