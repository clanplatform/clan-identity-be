#!/bin/bash
# Script to create auth_users table inside the Docker PostgreSQL container

echo "========================================================================"
echo "Creating auth_users table in Docker PostgreSQL"
echo "========================================================================"

# Run SQL command inside the PostgreSQL Docker container
docker exec -it clan-identity-postgres psql -U postgres -d auth_service << 'EOF'

-- Create auth_users table if it doesn't exist
CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    
    -- Organizational Structure (UUIDs, no FK constraints)
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_auth_users_user_setup_id ON auth_users(user_setup_id);
CREATE INDEX IF NOT EXISTS ix_auth_users_employee_id ON auth_users(employee_id);
CREATE INDEX IF NOT EXISTS ix_auth_users_username ON auth_users(username);
CREATE INDEX IF NOT EXISTS ix_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS ix_auth_users_status ON auth_users(status);

-- Verify tables
\dt

-- Show auth_users structure
\d auth_users

-- Show row count
SELECT COUNT(*) as row_count FROM auth_users;

EOF

echo ""
echo "========================================================================"
echo "✓ Table creation complete!"
echo "========================================================================"
