-- Brings login_attempts up to the LoginAttempt model (the enrichment migration
-- 003 was never applied): adds the tenant/session context, IP-intelligence,
-- device and network columns the login-attempt logger inserts, and converts
-- risk_score from VARCHAR to SMALLINT.
--
-- Without these, every login attempt INSERT fails with
-- 'column "tenant_id" of relation "login_attempts" does not exist'
-- (login still works; attempts just aren't recorded).
--
-- Run against the auth-service database (clan_identity):
--   psql -h localhost -p 5433 -U postgres -d clan_identity -f <this file>
--
-- Idempotent: ADD COLUMN IF NOT EXISTS + a guarded type change.

ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS tenant_id       UUID;
CREATE INDEX IF NOT EXISTS ix_login_attempts_tenant_id ON login_attempts (tenant_id);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS session_id      UUID;

-- Network / IP intelligence
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS ip_type         VARCHAR(10);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS isp             VARCHAR(150);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS region          VARCHAR(100);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS is_vpn          BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS is_proxy        BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS is_tor          BOOLEAN NOT NULL DEFAULT false;

-- Device (parsed from User-Agent)
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS device_type     VARCHAR(20);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS device_name     VARCHAR(100);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS browser         VARCHAR(50);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS browser_version VARCHAR(20);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS os              VARCHAR(50);
ALTER TABLE IF EXISTS login_attempts ADD COLUMN IF NOT EXISTS os_version      VARCHAR(20);

-- risk_score: model uses SMALLINT (0-100); convert only if still non-smallint
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'login_attempts'
          AND column_name = 'risk_score'
          AND data_type <> 'smallint'
    ) THEN
        ALTER TABLE login_attempts
            ALTER COLUMN risk_score TYPE SMALLINT USING NULLIF(risk_score::text, '')::smallint;
    END IF;
END $$;
