-- migrate:up
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS devices (
    id          UUID         PRIMARY KEY,
    device_name VARCHAR(255) NOT NULL,
    public_key  TEXT         NOT NULL,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE devices;
