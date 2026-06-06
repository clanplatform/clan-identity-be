-- ============================================================================
-- Table: sessions
-- Database: auth_db (auth_service)
-- Description: Stores user login sessions for tracking active sessions
--              Used for session management, device tracking, and security
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User reference (UUID from admin_service.usersetup_basic - no FK constraint)
    user_id UUID NOT NULL,
    
    -- Token information
    access_token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    
    -- Session status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_reason VARCHAR(100),
    
    -- Device information
    device_id VARCHAR(255),
    device_type VARCHAR(50) CHECK (device_type IN ('web', 'mobile', 'tablet', 'desktop', 'api')),
    device_name VARCHAR(255),
    device_fingerprint VARCHAR(255),
    
    -- Client information
    ip_address VARCHAR(45),
    user_agent TEXT,
    browser VARCHAR(100),
    os VARCHAR(100),
    
    -- Location (based on IP geolocation)
    country VARCHAR(100),
    city VARCHAR(100),
    
    -- Trust status
    is_trusted BOOLEAN NOT NULL DEFAULT FALSE,
    trusted_at TIMESTAMPTZ,
    
    -- Activity tracking
    last_activity TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity_ip VARCHAR(45),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

-- ============================================================================
-- Indexes for sessions table
-- ============================================================================

-- Index on user_id for user-specific session lookups
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Index on access_token_hash for token validation
CREATE INDEX IF NOT EXISTS idx_sessions_access_token_hash ON sessions(access_token_hash);

-- Index on refresh_token_hash for token refresh operations
CREATE INDEX IF NOT EXISTS idx_sessions_refresh_token_hash ON sessions(refresh_token_hash)
    WHERE refresh_token_hash IS NOT NULL;

-- Composite index for active sessions per user
CREATE INDEX IF NOT EXISTS idx_sessions_user_active 
    ON sessions(user_id, is_active, expires_at)
    WHERE is_active = TRUE AND is_revoked = FALSE;

-- Index on expires_at for cleanup and expiration checks
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Index on is_active for filtering active sessions
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active)
    WHERE is_active = TRUE;

-- Index on device_id for device-based queries
CREATE INDEX IF NOT EXISTS idx_sessions_device_id ON sessions(device_id)
    WHERE device_id IS NOT NULL;

-- Index on device_fingerprint for device tracking
CREATE INDEX IF NOT EXISTS idx_sessions_device_fingerprint ON sessions(device_fingerprint)
    WHERE device_fingerprint IS NOT NULL;

-- Index on last_activity for session timeout checks
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);

-- Composite index for trusted device sessions
CREATE INDEX IF NOT EXISTS idx_sessions_trusted 
    ON sessions(user_id, is_trusted, device_fingerprint)
    WHERE is_trusted = TRUE;

-- ============================================================================
-- Automatic session expiration function
-- ============================================================================

-- Function to automatically revoke expired sessions
CREATE OR REPLACE FUNCTION auto_revoke_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    revoked_count INTEGER;
BEGIN
    UPDATE sessions
    SET 
        is_active = FALSE,
        is_revoked = TRUE,
        revoked_reason = 'expired',
        revoked_at = CURRENT_TIMESTAMP
    WHERE 
        expires_at < CURRENT_TIMESTAMP
        AND is_active = TRUE
        AND is_revoked = FALSE;
    
    GET DIAGNOSTICS revoked_count = ROW_COUNT;
    
    RETURN revoked_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function to cleanup old revoked sessions
-- ============================================================================

-- Function to delete revoked sessions older than 30 days
CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions
    WHERE 
        is_revoked = TRUE
        AND revoked_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (requires pg_cron extension)
-- SELECT cron.schedule('auto-revoke-sessions', '*/15 * * * *', 'SELECT auto_revoke_expired_sessions()');
-- SELECT cron.schedule('cleanup-old-sessions', '0 3 * * *', 'SELECT cleanup_old_sessions()');

-- ============================================================================
-- Function to revoke all sessions for a user
-- ============================================================================

CREATE OR REPLACE FUNCTION revoke_user_sessions(p_user_id UUID, p_reason VARCHAR DEFAULT 'manual')
RETURNS INTEGER AS $$
DECLARE
    revoked_count INTEGER;
BEGIN
    UPDATE sessions
    SET 
        is_active = FALSE,
        is_revoked = TRUE,
        revoked_reason = p_reason,
        revoked_at = CURRENT_TIMESTAMP
    WHERE 
        user_id = p_user_id
        AND is_active = TRUE
        AND is_revoked = FALSE;
    
    GET DIAGNOSTICS revoked_count = ROW_COUNT;
    
    RETURN revoked_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Trigger to update last_activity
-- ============================================================================

CREATE OR REPLACE FUNCTION update_session_last_activity()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.last_activity <> OLD.last_activity THEN
        NEW.last_activity = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sessions_last_activity
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    WHEN (NEW.last_activity IS DISTINCT FROM OLD.last_activity)
    EXECUTE FUNCTION update_session_last_activity();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE sessions IS 'User login sessions for tracking active sessions, devices, and security';
COMMENT ON COLUMN sessions.id IS 'Primary key (UUID)';
COMMENT ON COLUMN sessions.user_id IS 'Reference to admin_service.usersetup_basic.id (no FK constraint)';
COMMENT ON COLUMN sessions.access_token_hash IS 'Hashed access token (SHA-256)';
COMMENT ON COLUMN sessions.refresh_token_hash IS 'Hashed refresh token (SHA-256)';
COMMENT ON COLUMN sessions.is_active IS 'Whether the session is currently active';
COMMENT ON COLUMN sessions.is_revoked IS 'Whether the session has been revoked';
COMMENT ON COLUMN sessions.revoked_reason IS 'Reason for revocation: manual, expired, security, logout';
COMMENT ON COLUMN sessions.device_type IS 'Type of device: web, mobile, tablet, desktop, api';
COMMENT ON COLUMN sessions.device_fingerprint IS 'Unique device identifier';
COMMENT ON COLUMN sessions.is_trusted IS 'Whether this is a trusted device';
COMMENT ON COLUMN sessions.expires_at IS 'Session expiration timestamp';
COMMENT ON COLUMN sessions.last_activity IS 'Last activity timestamp for idle timeout';
