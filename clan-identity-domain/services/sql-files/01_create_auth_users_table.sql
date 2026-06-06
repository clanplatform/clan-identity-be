-- ============================================================================
-- Table: auth_users
-- Database: auth_db (auth_service)
-- Description: Authentication user table (NOT USED FOR PRIMARY AUTHENTICATION)
--              Users are authenticated against admin_service.usersetup_basic
--              This table is kept for potential future use and caching
-- ============================================================================

CREATE TABLE IF NOT EXISTS auth_users (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to admin_service user (for linking, no FK constraint)
    admin_user_id UUID UNIQUE,
    
    -- Authentication credentials
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Basic user info (cached from admin service)
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    employee_id VARCHAR(50) UNIQUE,
    
    -- Account status
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'locked')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Password management
    password_changed TIMESTAMPTZ,
    is_password_change_required BOOLEAN NOT NULL DEFAULT TRUE,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMPTZ,
    
    -- Login tracking
    last_login TIMESTAMPTZ,
    last_login_ip VARCHAR(45),
    failed_login_attempts VARCHAR(10) NOT NULL DEFAULT '0',
    locked_until TIMESTAMPTZ,
    
    -- Two-factor authentication
    two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    two_factor_backup_codes TEXT,
    
    -- Session management
    current_token TEXT,
    
    -- Roles (cached from admin service for quick access)
    roles UUID[],
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for auth_users table
-- ============================================================================

-- Index on admin_user_id for linking
CREATE INDEX IF NOT EXISTS idx_auth_users_admin_user_id ON auth_users(admin_user_id);

-- Index on email for quick lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);

-- Index on username for quick lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users(username);

-- Index on employee_id
CREATE INDEX IF NOT EXISTS idx_auth_users_employee_id ON auth_users(employee_id);

-- Index on status for filtering
CREATE INDEX IF NOT EXISTS idx_auth_users_status ON auth_users(status);

-- Index on is_active for filtering active users
CREATE INDEX IF NOT EXISTS idx_auth_users_is_active ON auth_users(is_active);

-- Composite index for active user lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_active_status ON auth_users(is_active, status);

-- ============================================================================
-- Trigger for updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_auth_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auth_users_updated_at
    BEFORE UPDATE ON auth_users
    FOR EACH ROW
    EXECUTE FUNCTION update_auth_users_updated_at();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE auth_users IS 'Authentication user table - NOT USED FOR PRIMARY AUTHENTICATION. Users are authenticated against admin_service.usersetup_basic';
COMMENT ON COLUMN auth_users.id IS 'Primary key (UUID)';
COMMENT ON COLUMN auth_users.admin_user_id IS 'Reference to admin_service.usersetup_basic.id (no FK constraint)';
COMMENT ON COLUMN auth_users.email IS 'User email address';
COMMENT ON COLUMN auth_users.username IS 'Unique username';
COMMENT ON COLUMN auth_users.password_hash IS 'Bcrypt hashed password';
COMMENT ON COLUMN auth_users.status IS 'Account status: active, inactive, suspended, locked';
COMMENT ON COLUMN auth_users.is_active IS 'Whether the account is active';
COMMENT ON COLUMN auth_users.is_verified IS 'Whether the email is verified';
COMMENT ON COLUMN auth_users.two_factor_enabled IS 'Whether 2FA is enabled';
COMMENT ON COLUMN auth_users.roles IS 'Array of role UUIDs cached from admin service';
