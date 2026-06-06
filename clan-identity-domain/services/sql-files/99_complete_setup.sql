-- ============================================================================
-- Complete Setup Script - Execute all table creation scripts in order
-- Database: auth_db (auth_service)
-- ============================================================================

\echo '============================================================================'
\echo 'Starting auth_db database setup...'
\echo '============================================================================'

-- Initialize database with extensions
\echo 'Step 1: Initializing database and extensions...'
\i 00_init_auth_database.sql

\echo ''
\echo 'Step 2: Creating auth_users table...'
\i 01_create_auth_users_table.sql

\echo ''
\echo 'Step 3: Creating login_attempts table...'
\i 02_create_login_attempts_table.sql

\echo ''
\echo 'Step 4: Creating sessions table...'
\i 03_create_sessions_table.sql

-- ============================================================================
-- Verify table creation
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'Verifying table creation...'
\echo '============================================================================'

SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename IN ('auth_users', 'login_attempts', 'sessions')
ORDER BY tablename;

-- ============================================================================
-- Display table sizes
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'Table statistics:'
\echo '============================================================================'

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename IN ('auth_users', 'login_attempts', 'sessions')
ORDER BY tablename;

-- ============================================================================
-- List all indexes
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'Created indexes:'
\echo '============================================================================'

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
AND tablename IN ('auth_users', 'login_attempts', 'sessions')
ORDER BY tablename, indexname;

-- ============================================================================
-- List all triggers
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'Created triggers:'
\echo '============================================================================'

SELECT 
    trigger_schema,
    trigger_name,
    event_manipulation,
    event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
AND event_object_table IN ('auth_users', 'login_attempts', 'sessions')
ORDER BY event_object_table, trigger_name;

-- ============================================================================
-- Completion message
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'auth_db setup completed successfully!'
\echo '============================================================================'
\echo 'Tables created: auth_users, login_attempts, sessions'
\echo 'All indexes and triggers have been created.'
\echo 'Database is ready for use.'
\echo '============================================================================'
