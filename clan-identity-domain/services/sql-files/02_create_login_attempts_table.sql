-- ============================================================================
-- Table: login_attempts
-- Database: auth_db (auth_service)
-- Description: Tracks all login attempts for security monitoring and audit
--              Used for rate limiting, suspicious activity detection, and compliance
-- ============================================================================

CREATE TABLE IF NOT EXISTS login_attempts (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User reference (UUID from admin_service.usersetup_basic - no FK constraint)
    user_id UUID,
    
    -- Attempt details
    email_or_username VARCHAR(255) NOT NULL,
    attempt_type VARCHAR(50) NOT NULL DEFAULT 'password' CHECK (attempt_type IN ('password', 'otp', '2fa', 'sso', 'biometric')),
    
    -- Result
    is_successful BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason VARCHAR(100),
    
    -- Client information
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    
    -- Device fingerprint (for detecting suspicious activity)
    device_fingerprint VARCHAR(255),
    
    -- Location (based on IP geolocation)
    country VARCHAR(100),
    city VARCHAR(100),
    
    -- Risk assessment
    risk_score VARCHAR(10),
    is_suspicious BOOLEAN NOT NULL DEFAULT FALSE,
    suspicious_reason VARCHAR(255),
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for login_attempts table
-- ============================================================================

-- Index on user_id for user-specific lookups
CREATE INDEX IF NOT EXISTS idx_login_attempts_user_id ON login_attempts(user_id);

-- Index on email_or_username for tracking attempts by identifier
CREATE INDEX IF NOT EXISTS idx_login_attempts_email_username ON login_attempts(email_or_username);

-- Index on ip_address for IP-based rate limiting
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_address ON login_attempts(ip_address);

-- Index on created_at for time-based queries and cleanup
CREATE INDEX IF NOT EXISTS idx_login_attempts_created_at ON login_attempts(created_at);

-- Composite index for recent failed attempts (rate limiting)
CREATE INDEX IF NOT EXISTS idx_login_attempts_failed_recent 
    ON login_attempts(email_or_username, is_successful, created_at)
    WHERE is_successful = FALSE;

-- Index on is_suspicious for security monitoring
CREATE INDEX IF NOT EXISTS idx_login_attempts_suspicious 
    ON login_attempts(is_suspicious, created_at)
    WHERE is_suspicious = TRUE;

-- Composite index for IP-based rate limiting
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_recent 
    ON login_attempts(ip_address, created_at, is_successful);

-- Index on device_fingerprint for device tracking
CREATE INDEX IF NOT EXISTS idx_login_attempts_device_fingerprint 
    ON login_attempts(device_fingerprint)
    WHERE device_fingerprint IS NOT NULL;

-- ============================================================================
-- Partitioning setup (optional - for high volume)
-- ============================================================================

-- Uncomment below if you want to partition by month for better performance
-- This is recommended for systems with high login volume

/*
-- Convert to partitioned table
CREATE TABLE IF NOT EXISTS login_attempts_partitioned (
    LIKE login_attempts INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create partitions for current and next 3 months
CREATE TABLE login_attempts_2024_01 PARTITION OF login_attempts_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE login_attempts_2024_02 PARTITION OF login_attempts_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Add more partitions as needed
*/

-- ============================================================================
-- Automatic cleanup function (optional)
-- ============================================================================

-- Function to delete login attempts older than 90 days
CREATE OR REPLACE FUNCTION cleanup_old_login_attempts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM login_attempts
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-login-attempts', '0 2 * * *', 'SELECT cleanup_old_login_attempts()');

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE login_attempts IS 'Tracks all login attempts for security monitoring, rate limiting, and audit compliance';
COMMENT ON COLUMN login_attempts.id IS 'Primary key (UUID)';
COMMENT ON COLUMN login_attempts.user_id IS 'Reference to admin_service.usersetup_basic.id (no FK constraint)';
COMMENT ON COLUMN login_attempts.email_or_username IS 'Email or username used in the login attempt';
COMMENT ON COLUMN login_attempts.attempt_type IS 'Type of authentication: password, otp, 2fa, sso, biometric';
COMMENT ON COLUMN login_attempts.is_successful IS 'Whether the login attempt was successful';
COMMENT ON COLUMN login_attempts.failure_reason IS 'Reason for failure: invalid_credentials, account_locked, 2fa_required, etc.';
COMMENT ON COLUMN login_attempts.ip_address IS 'IP address of the login attempt (IPv4/IPv6)';
COMMENT ON COLUMN login_attempts.device_fingerprint IS 'Unique device identifier for tracking';
COMMENT ON COLUMN login_attempts.risk_score IS 'Risk score (0-100) calculated from various factors';
COMMENT ON COLUMN login_attempts.is_suspicious IS 'Flag indicating suspicious activity detected';
