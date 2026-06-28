package store

const schema = `
CREATE TABLE IF NOT EXISTS trusted_devices (
    id TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    public_key TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS local_device (
    device_id TEXT PRIMARY KEY,
    private_key_encrypted BLOB NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES trusted_devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS secrets (
    id TEXT PRIMARY KEY,
    folder_id TEXT,
    encrypted_payload BLOB NOT NULL,
    nonce BLOB NOT NULL,
    version INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS secret_recipients (
    secret_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    encrypted_dek BLOB NOT NULL,
    PRIMARY KEY (secret_id, device_id),
    FOREIGN KEY (secret_id) REFERENCES secrets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recipients_device ON secret_recipients(device_id);
`
