-- Auth Service Database Initialization
-- Creates all tables for auth_service database
-- PostgreSQL 16+

-- ============================================================================
-- Database Creation (run as superuser if needed)
-- ============================================================================
-- CREATE DATABASE auth_service
--     WITH 
--     OWNER = postgres
--     ENCODING = 'UTF8'
--     LC_COLLATE = 'en_US.utf8'
--     LC_CTYPE = 'en_US.utf8'
--     TABLESPACE = pg_default
--     CONNECTION LIMIT = -1;

-- Connect to auth_service database before running below
-- \c auth_service

-- ============================================================================
-- Enable UUID extension
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Table: auth_users
-- Stores authenticated user data (mirrors admin_service.usersetup_basic)
-- Used for local authentication after first password change
-- ============================================================================
CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to admin_service user
    user_setup_id UUID UNIQUE,
    
    -- Personal Information
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    employee_id VARCHAR(50) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(20),
    
    -- Authentication
    password_hash VARCHAR(255) NOT NULL,
    password_changed TIMESTAMP WITH TIME ZONE,
    is_password_change BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Employment Status
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    tem_employee BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Organizational Structure (stored as UUIDs, no FK constraints)
    department UUID,
    division UUID,
    job_code UUID,
    
    -- Role Management
    manage_roles UUID[],
    
    -- Default Settings
    default_dept UUID,
    reporting_to UUID,
    
    -- Entity Access
    entities UUID[],
    default_entity UUID,
    
    -- View Preferences
    view VARCHAR(50),
    dashboard_view VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Table: sessions
-- Manages user sessions and tokens
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User reference (UUID - no FK constraint to allow cross-database reference)
    user_id UUID NOT NULL,
    
    -- Session identification
    session_token VARCHAR(255) NOT NULL UNIQUE,
    refresh_token VARCHAR(255) NOT NULL UNIQUE,
    
    -- Session details
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_type VARCHAR(50),
    device_name VARCHAR(100),
    browser VARCHAR(100),
    os VARCHAR(100),
    
    -- Location
    country VARCHAR(100),
    city VARCHAR(100),
    
    -- Device trust
    device_fingerprint VARCHAR(255),
    is_trusted_device BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Session status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(255),
    
    -- Session timing
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE,
    
    -- Additional metadata
    remember_me BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Table: login_attempts
-- Tracks all login attempts for security monitoring and rate limiting
-- ============================================================================
CREATE TABLE IF NOT EXISTS login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User reference (UUID - may be null for failed attempts)
    user_id UUID,
    
    -- Attempt details
    email_or_username VARCHAR(255) NOT NULL,
    attempt_type VARCHAR(50) NOT NULL DEFAULT 'password',
    
    -- Result
    is_successful BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason VARCHAR(100),
    
    -- Client information
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    
    -- Device fingerprint
    device_fingerprint VARCHAR(255),
    
    -- Location (based on IP)
    country VARCHAR(100),
    city VARCHAR(100),
    
    -- Risk assessment
    risk_score VARCHAR(10),
    is_suspicious BOOLEAN NOT NULL DEFAULT FALSE,
    suspicious_reason VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Indexes for auth_users
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users(username);
CREATE INDEX IF NOT EXISTS idx_auth_users_employee_id ON auth_users(employee_id);
CREATE INDEX IF NOT EXISTS idx_auth_users_status ON auth_users(status);
CREATE INDEX IF NOT EXISTS idx_auth_users_user_setup_id ON auth_users(user_setup_id);
CREATE INDEX IF NOT EXISTS idx_auth_users_status_active ON auth_users(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_auth_users_employee_status ON auth_users(employee_id, status);

-- ============================================================================
-- Indexes for sessions
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_session_token ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_refresh_token ON sessions(refresh_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(user_id, expires_at) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_sessions_cleanup ON sessions(expires_at, is_active) WHERE is_active = true;

-- ============================================================================
-- Indexes for login_attempts
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_login_attempts_user_id ON login_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_login_attempts_email_or_username ON login_attempts(email_or_username);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_address ON login_attempts(ip_address);
CREATE INDEX IF NOT EXISTS idx_login_attempts_created_at ON login_attempts(created_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_user_created ON login_attempts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_created ON login_attempts(ip_address, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_attempts_suspicious ON login_attempts(is_suspicious, created_at DESC) WHERE is_suspicious = true;

-- ============================================================================
-- Trigger: Update updated_at timestamp automatically
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to auth_users
DROP TRIGGER IF EXISTS update_auth_users_updated_at ON auth_users;
CREATE TRIGGER update_auth_users_updated_at
    BEFORE UPDATE ON auth_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to sessions
DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Sample Queries for Verification
-- ============================================================================

-- Check all tables
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Check table structure
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'auth_users'
-- ORDER BY ordinal_position;

-- Check indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename IN ('auth_users', 'sessions', 'login_attempts');

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
COMMENT ON TABLE auth_users IS 'Authenticated users - mirrors admin_service.usersetup_basic for local authentication';
COMMENT ON TABLE sessions IS 'User sessions and JWT tokens for authentication management';
COMMENT ON TABLE login_attempts IS 'Login attempt tracking for security monitoring and rate limiting';

COMMENT ON COLUMN auth_users.user_setup_id IS 'Reference to admin_service.usersetup_basic.id (no FK constraint for cross-database reference)';
COMMENT ON COLUMN auth_users.is_password_change IS 'FALSE means first login, password change required';
COMMENT ON COLUMN sessions.user_id IS 'Reference to user ID (can be from auth_users or admin_service)';
COMMENT ON COLUMN login_attempts.user_id IS 'User ID if identified, NULL for failed username/email attempts';
COMMENT ON COLUMN login_attempts.attempt_type IS 'Type of login attempt: password, otp, 2fa, sso';

-- ============================================================================
-- Grant Permissions (adjust as needed for your environment)
-- ============================================================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO auth_service_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO auth_service_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO auth_service_user;
