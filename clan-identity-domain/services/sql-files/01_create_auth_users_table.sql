-- ============================================================================
-- Table: auth_users
-- Database: auth_db (auth_service)
-- Description: Authentication user table - mirrors usersetup_basic structure
--              Used for local authentication after first password change
-- ============================================================================

CREATE TABLE IF NOT EXISTS auth_users (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to admin_service user (for linking, no FK constraint)
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
    password_changed TIMESTAMPTZ,
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for auth_users table
-- ============================================================================

-- Index on user_setup_id for linking
CREATE INDEX IF NOT EXISTS idx_auth_users_user_setup_id ON auth_users(user_setup_id);

-- Index on email for quick lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);

-- Index on username for quick lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users(username);

-- Index on employee_id
CREATE INDEX IF NOT EXISTS idx_auth_users_employee_id ON auth_users(employee_id);

-- Index on status for filtering
CREATE INDEX IF NOT EXISTS idx_auth_users_status ON auth_users(status);

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

COMMENT ON TABLE auth_users IS 'Authentication user table - mirrors usersetup_basic structure for local authentication';
COMMENT ON COLUMN auth_users.id IS 'Primary key (UUID)';
COMMENT ON COLUMN auth_users.user_setup_id IS 'Reference to admin_service.usersetup_basic.id (no FK constraint)';
COMMENT ON COLUMN auth_users.email IS 'User email address';
COMMENT ON COLUMN auth_users.username IS 'Unique username';
COMMENT ON COLUMN auth_users.password_hash IS 'Bcrypt hashed password';
COMMENT ON COLUMN auth_users.status IS 'Account status: active, inactive, suspended, etc.';
COMMENT ON COLUMN auth_users.manage_roles IS 'Array of role UUIDs user can manage';
COMMENT ON COLUMN auth_users.is_password_change IS 'Flag indicating if user has changed default password';
