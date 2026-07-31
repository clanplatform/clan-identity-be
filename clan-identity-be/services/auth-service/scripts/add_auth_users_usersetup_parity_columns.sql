-- Brings auth_users to field parity with admin-service usersetup_basic by adding
-- the three columns it was missing:
--   user_group_id     UUID       (bare reference)
--   send_invite_email BOOLEAN    (invite flag)
--   allowed_origins   TEXT[]     (per-user redirect targets)
--
-- Run against the auth-service database (clan_identity):
--   psql -h localhost -p 5433 -U postgres -d clan_identity -f <this file>
--
-- Idempotent: ADD COLUMN IF NOT EXISTS.

ALTER TABLE IF EXISTS auth_users ADD COLUMN IF NOT EXISTS user_group_id     UUID;
ALTER TABLE IF EXISTS auth_users ADD COLUMN IF NOT EXISTS send_invite_email BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE IF EXISTS auth_users ADD COLUMN IF NOT EXISTS allowed_origins   TEXT[];
