-- migrate:up
-- A monotonic per-write sequence is the sync cursor: clients pull "changes since
-- seq". It advances on every insert and update (the repository sets nextval on
-- update), so a modified secret resurfaces to other devices. Global ordering is
-- fine — pulls always filter by account_id.
CREATE SEQUENCE secret_seq;
ALTER TABLE secrets ADD COLUMN seq BIGINT NOT NULL DEFAULT nextval('secret_seq');
ALTER SEQUENCE secret_seq OWNED BY secrets.seq;
CREATE INDEX idx_secrets_account_seq ON secrets (account_id, seq);

-- migrate:down
DROP INDEX idx_secrets_account_seq;
ALTER TABLE secrets DROP COLUMN seq;
DROP SEQUENCE IF EXISTS secret_seq;
