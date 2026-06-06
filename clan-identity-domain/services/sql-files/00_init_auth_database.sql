-- ============================================================================
-- Database Initialization Script for auth_db (auth_service)
-- ============================================================================
-- This script initializes the auth_db database with extensions,
-- schemas, and basic configuration
-- ============================================================================

-- Connect to auth_db database
\c auth_db;

-- ============================================================================
-- Enable required PostgreSQL extensions
-- ============================================================================

-- UUID generation functions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Generate random UUIDs (preferred method)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Advanced text search capabilities (if needed)
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Scheduled job support (optional - for automated cleanup)
-- Requires separate installation: https://github.com/citusdata/pg_cron
-- CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- ============================================================================
-- Create schemas if needed (optional)
-- ============================================================================

-- Default schema is 'public'
-- Uncomment if you want separate schemas
-- CREATE SCHEMA IF NOT EXISTS auth;
-- CREATE SCHEMA IF NOT EXISTS audit;

-- ============================================================================
-- Set default privileges
-- ============================================================================

-- Grant usage on extensions
GRANT USAGE ON SCHEMA public TO PUBLIC;

-- ============================================================================
-- Database settings
-- ============================================================================

-- Set timezone to UTC
ALTER DATABASE auth_db SET timezone TO 'UTC';

-- Set default text search configuration (if needed)
-- ALTER DATABASE auth_db SET default_text_search_config TO 'pg_catalog.english';

-- ============================================================================
-- Audit schema (optional - for comprehensive audit logging)
-- ============================================================================

/*
-- Uncomment to create audit schema and table

CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    user_id UUID,
    old_data JSONB,
    new_data JSONB,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_table_name ON audit.audit_log(table_name);
CREATE INDEX idx_audit_log_user_id ON audit.audit_log(user_id);
CREATE INDEX idx_audit_log_changed_at ON audit.audit_log(changed_at);

-- Generic audit trigger function
CREATE OR REPLACE FUNCTION audit.log_audit()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit.audit_log (table_name, operation, old_data)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.audit_log (table_name, operation, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit.audit_log (table_name, operation, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
*/

-- ============================================================================
-- Create roles and users (adjust for your environment)
-- ============================================================================

-- Create read-only role
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'auth_readonly') THEN
        CREATE ROLE auth_readonly;
    END IF;
END
$$;

-- Grant select permissions to readonly role (run after tables are created)
-- GRANT USAGE ON SCHEMA public TO auth_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO auth_readonly;

-- ============================================================================
-- Information
-- ============================================================================

SELECT 'auth_db database initialized successfully!' AS status;
SELECT version() AS postgresql_version;
SELECT current_database() AS current_database;
SELECT current_timestamp AS initialized_at;
