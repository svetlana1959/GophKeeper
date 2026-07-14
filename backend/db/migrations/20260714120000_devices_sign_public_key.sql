-- migrate:up
-- Each device gains an Ed25519 signing public key (base64), separate from its age
-- encryption key. It is the identity that verifies the device's trust certs
-- (vouch/revoke) in the M4 trust graph. Nullable-by-default '' so pre-M4 devices
-- and the keyless web plane carry no signing key.
ALTER TABLE devices ADD COLUMN sign_public_key TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE devices DROP COLUMN sign_public_key;
