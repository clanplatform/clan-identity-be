-- Migration script to update auth_users table schema
-- Adds missing columns required by the AuthUser model

BEGIN;

-- Add user_setup_id if not exists (already done, but keeping for reference)
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS user_setup_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS auth_users_user_setup_id_key ON auth_users(user_setup_id);
CREATE INDEX IF NOT EXISTS ix_auth_users_user_setup_id ON auth_users(user_setup_id);

-- Add missing columns from the model
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS end_date DATE;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS tem_employee BOOLEAN NOT NULL DEFAULT FALSE;

-- Organizational structure
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS department UUID;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS division UUID;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS job_code UUID;

-- Role management
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS manage_roles UUID[];

-- Default settings
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS default_dept UUID;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS reporting_to UUID;

-- Entity access
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS entities UUID[];
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS default_entity UUID;

-- View preferences
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS view VARCHAR(50);
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS dashboard_view VARCHAR(50);

-- Rename is_password_change_required to is_password_change if needed
-- Note: The model uses is_password_change (TRUE = password has been changed)
-- The old schema uses is_password_change_required (TRUE = password change is required)
-- These are logical opposites, so we need to handle the migration carefully

-- Check if we need to add is_password_change
DO $$
BEGIN
    -- Add is_password_change if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'auth_users' AND column_name = 'is_password_change'
    ) THEN
        -- Add the column
        ALTER TABLE auth_users ADD COLUMN is_password_change BOOLEAN NOT NULL DEFAULT FALSE;
        
        -- If is_password_change_required exists, copy inverted values
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'auth_users' AND column_name = 'is_password_change_required'
        ) THEN
            UPDATE auth_users SET is_password_change = NOT is_password_change_required;
        END IF;
    END IF;
END $$;

-- Ensure indexes exist
CREATE INDEX IF NOT EXISTS ix_auth_users_employee_id ON auth_users(employee_id);
CREATE INDEX IF NOT EXISTS ix_auth_users_username ON auth_users(username);
CREATE INDEX IF NOT EXISTS ix_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS ix_auth_users_status ON auth_users(status);

-- Verify the schema
SELECT 'Migration completed successfully' as status;

-- Show updated schema
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'auth_users'
ORDER BY ordinal_position;

COMMIT;
