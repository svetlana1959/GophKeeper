-- migrate:up
-- BUG FIX: on some environments the `id` columns were created as TEXT by an
-- earlier version of the migration files, before the domain model switched
-- to UUID. dbmate only runs new migration files, it never re-runs or diffs
-- an already-applied one — so those databases were stuck with the old
-- column type even after the .sql files in this repo were updated to say
-- `UUID`. This migration brings any such database in line.
--
-- The casts are safe no-ops if the columns are already UUID, and convert
-- correctly if they are TEXT/VARCHAR containing valid UUID strings.

ALTER TABLE secrets
    ALTER COLUMN id TYPE UUID USING id::uuid;

ALTER TABLE devices
    ALTER COLUMN id TYPE UUID USING id::uuid;

-- migrate:down
ALTER TABLE secrets
    ALTER COLUMN id TYPE TEXT USING id::text;

ALTER TABLE devices
    ALTER COLUMN id TYPE TEXT USING id::text;
