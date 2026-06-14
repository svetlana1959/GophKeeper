-- migrate:up
CREATE TABLE IF NOT EXISTS devices (
    id          TEXT         PRIMARY KEY,
    device_name VARCHAR(255) NOT NULL,
    public_key  TEXT         NOT NULL,
    is_active   BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP
);

-- migrate:down
DROP TABLE devices
