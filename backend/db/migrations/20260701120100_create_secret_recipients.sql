-- migrate:up
-- Which devices each secret is sealed to (the age recipient set, mirrored
-- server-side for authorization). A device only pulls secrets it is a recipient
-- of; this is the authorization layer on top of the cryptographic one.
CREATE TABLE secret_recipients (
    secret_id UUID NOT NULL REFERENCES secrets (id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES devices (id) ON DELETE CASCADE,
    PRIMARY KEY (secret_id, device_id)
);

CREATE INDEX idx_secret_recipients_device ON secret_recipients (device_id);

-- migrate:down
DROP TABLE secret_recipients;
