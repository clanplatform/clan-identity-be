# Auth Service Database Migrations

This directory contains SQL migration scripts for the auth_service database.

## Migration Files

1. **001_create_auth_users_table.sql** - Creates the auth_users table
   - Stores user authentication information after first password change
   - Mirrors usersetup_basic structure from admin_service
   - Includes indexes for email, username, employee_id, and status

2. **002_create_login_attempts_table.sql** - Creates the login_attempts table
   - Tracks all login attempts for security monitoring
   - Used for rate limiting and audit trails
   - Includes risk assessment fields

3. **003_create_sessions_table.sql** - Creates the sessions table
   - Manages active user sessions
   - Tracks device information and session metadata
   - Supports session revocation and trust management

## Running Migrations

### Option 1: Using the Python migration runner
```bash
python scripts/run_migrations.py
```

### Option 2: Using Docker
```bash
# Run all migrations
python scripts/run_migrations_docker.py

# Or use PowerShell script
.\scripts\run_migrations.ps1
```

### Option 3: Manual execution with psql
```bash
# Connect to database
psql -h localhost -p 5433 -U postgres -d auth_service

# Run migrations in order
\i scripts/migrations/001_create_auth_users_table.sql
\i scripts/migrations/002_create_login_attempts_table.sql
\i scripts/migrations/003_create_sessions_table.sql
```

## Migration Order

Migrations must be run in numerical order:
1. 001 - Creates auth_users table
2. 002 - Creates login_attempts table
3. 003 - Creates sessions table

## Database Schema

### auth_users
- Primary user authentication table
- Stores local credentials after password change
- No foreign key constraints to admin_service

### login_attempts
- Security monitoring and audit trail
- Rate limiting support
- Risk assessment tracking

### sessions
- Active session management
- Device tracking and trust management
- Session revocation support

## Rollback

To rollback migrations, use the rollback scripts:
```bash
python scripts/rollback_migrations.py
```

Or manually drop tables:
```sql
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS login_attempts CASCADE;
DROP TABLE IF EXISTS auth_users CASCADE;
```

## Notes

- All tables use UUID as primary keys
- Timestamps are timezone-aware (TIMESTAMP WITH TIME ZONE)
- No foreign key constraints to admin_service database
- Indexes are created for frequently queried columns
- Updated_at trigger is automatically managed for auth_users
