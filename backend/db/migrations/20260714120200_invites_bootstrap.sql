-- migrate:up
-- The invite now carries the code-bound trust bootstrap (docs/sync_design.md §11).
-- The inviter (client) generates the code and uploads a roster of its trusted
-- devices, each MAC'd under the code, so the joiner can adopt them as anchors
-- without trusting the server. On join, the device's join MAC and id are recorded
-- so the inviter can later verify who redeemed the code and vouch for it.
ALTER TABLE invites ADD COLUMN roster_json      TEXT NOT NULL DEFAULT '[]';
ALTER TABLE invites ADD COLUMN join_mac         TEXT NOT NULL DEFAULT '';
ALTER TABLE invites ADD COLUMN joined_device_id UUID REFERENCES devices (id) ON DELETE SET NULL;

-- migrate:down
ALTER TABLE invites DROP COLUMN roster_json;
ALTER TABLE invites DROP COLUMN join_mac;
ALTER TABLE invites DROP COLUMN joined_device_id;
