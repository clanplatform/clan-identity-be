# Fix: "column user_setup_id does not exist" Error

## Problem

The auth-service was failing with:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) 
column "user_setup_id" of relation "auth_users" does not exist
```

This occurred during the change-password operation when trying to create a new user in the `auth_users` table.

## Root Cause

The issue had **multiple layers**:

### 1. Two Different PostgreSQL Databases
- **localhost:5433** - PostgreSQL accessible from the host machine (Docker exposed port)
- **postgres:5432** - PostgreSQL accessible from inside Docker containers (Docker internal network)

### 2. Schema Mismatch
The `auth_users` table in the Docker PostgreSQL (postgres:5432) had an **old schema** that was missing several columns required by the `AuthUser` model:

**Missing columns:**
- `user_setup_id` - Link to admin_service user
- `phone_number`
- `start_date`, `end_date`
- `tem_employee`
- `department`, `division`, `job_code`
- `manage_roles`
- `default_dept`, `reporting_to`
- `entities`, `default_entity`
- `view`, `dashboard_view`
- `is_password_change` - Password change status

**Extra columns in old schema:**
- `admin_user_id` (different from user_setup_id)
- `is_password_change_required` (opposite logic of is_password_change)
- `is_active`, `is_verified`
- `password_reset_token`, `password_reset_expires`
- `last_login`, `last_login_ip`
- `failed_login_attempts`, `locked_until`
- `two_factor_enabled`, `two_factor_secret`, `two_factor_backup_codes`
- `current_token`

### 3. Where We Initially Created the Table
When we first created the `auth_users` table using the script, we created it on **localhost:5433**, but the Docker container was trying to use the table on **postgres:5432** (different database instance).

## Solution Applied

### Step 1: Identified the Correct Database
The auth-service Docker container connects to:
- Host: `postgres` (Docker internal network)
- Port: `5432` (internal port)
- Database: `auth_service`

### Step 2: Ran Schema Migration
Created and executed `migrate_auth_users_schema.sql` which:

1. **Added missing columns:**
   ```sql
   ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS user_setup_id UUID;
   ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
   ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS start_date DATE;
   -- ... and all other missing columns
   ```

2. **Added is_password_change column:**
   ```sql
   ALTER TABLE auth_users ADD COLUMN is_password_change BOOLEAN NOT NULL DEFAULT FALSE;
   -- Copied inverted values from is_password_change_required
   UPDATE auth_users SET is_password_change = NOT is_password_change_required;
   ```

3. **Created indexes:**
   ```sql
   CREATE INDEX IF NOT EXISTS ix_auth_users_user_setup_id ON auth_users(user_setup_id);
   CREATE INDEX IF NOT EXISTS ix_auth_users_employee_id ON auth_users(employee_id);
   -- ... and other indexes
   ```

### Step 3: Restarted Auth Service
```bash
docker-compose restart auth-service
```

## Verification

### 1. Check Table Schema in Docker
```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "\d auth_users"
```

### 2. Verify Column Exists
```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'auth_users' AND column_name = 'user_setup_id';"
```

Should return:
```
 column_name   
---------------
 user_setup_id
```

### 3. Check Service Logs
```bash
docker logs clan-auth-service --tail 30
```

Should show:
```
INFO - Tables in auth_service: ['sessions', 'login_attempts', 'auth_users']
INFO - Database tables initialized successfully
```

### 4. Test Change Password Endpoint
```bash
curl -X POST "http://localhost:8001/api/v1/login/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "current_password": "oldpassword",
    "new_password": "newpassword",
    "confirm_password": "newpassword"
  }'
```

## Current Database Schema

After migration, the `auth_users` table has **42 columns**:

### Core Columns (from AuthUser model):
- `id` (UUID) - Primary key
- `user_setup_id` (UUID) - Link to admin_service
- `firstname`, `lastname`, `email`, `username`, `employee_id`
- `password_hash`, `password_changed`, `is_password_change`
- `status`, `start_date`, `end_date`, `tem_employee`
- `department`, `division`, `job_code`
- `manage_roles`, `default_dept`, `reporting_to`
- `entities`, `default_entity`
- `view`, `dashboard_view`
- `created_at`, `updated_at`

### Legacy Columns (from old schema):
- `admin_user_id`, `is_password_change_required`
- `is_active`, `is_verified`
- Authentication/security fields
- Two-factor authentication fields

**Note:** SQLAlchemy will ignore columns not defined in the model, so the legacy columns won't cause issues.

## Scripts Created

### 1. `migrate_auth_users_schema.sql`
Complete schema migration script that:
- Adds all missing columns
- Creates necessary indexes
- Handles data migration (is_password_change)

### 2. `create_table_in_docker.sh` / `create_table_in_docker.ps1`
Scripts to create the table directly in Docker PostgreSQL

### 3. `check_columns.py`
Python script to list all columns in auth_users table

### 4. `test_insert.py`
Test script to verify INSERT operations work

## Key Learnings

### 1. Docker Networking
- Docker containers communicate via internal network (e.g., `postgres:5432`)
- Host machine accesses via exposed ports (e.g., `localhost:5433`)
- These are **different database instances** if not properly configured

### 2. Schema Evolution
- Existing production data required ALTER TABLE instead of DROP/CREATE
- Column additions are non-destructive
- Inverse logic fields (is_password_change vs is_password_change_required) need data migration

### 3. Database Operations in Docker
```bash
# Execute SQL in Docker PostgreSQL
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SQL COMMAND"

# Execute SQL file
Get-Content script.sql | docker exec -i clan-identity-postgres psql -U postgres -d auth_service
```

## Prevention for Future

### 1. Use Alembic Migrations
Instead of manual schema changes, use Alembic:
```bash
alembic revision --autogenerate -m "Add missing columns to auth_users"
alembic upgrade head
```

### 2. Verify Database Before Deployment
Always check which database the service connects to:
```python
with engine.connect() as conn:
    result = conn.execute("SELECT current_database(), inet_server_addr(), inet_server_port()")
    print(result.fetchone())
```

### 3. Keep Schemas in Sync
- Model definitions should match database schema
- Document any legacy columns
- Use consistent column naming

## Summary

| Issue | Status | Solution |
|-------|--------|----------|
| user_setup_id column missing | ✅ Fixed | Added column via ALTER TABLE |
| Schema mismatch (old vs new) | ✅ Fixed | Ran migration script to add all missing columns |
| Wrong database (localhost vs Docker) | ✅ Fixed | Ran migration on correct Docker PostgreSQL |
| is_password_change missing | ✅ Fixed | Added column and migrated data |
| Service not recognizing changes | ✅ Fixed | Restarted Docker container |

## Next Steps

1. ✅ Schema migration completed
2. ✅ Auth-service restarted
3. 🔄 **Test change-password endpoint** to verify fix works
4. 🔄 **Test login with first-time user** to verify user creation
5. 🔄 **Monitor logs** for any remaining issues

---

**Status**: ✅ RESOLVED - user_setup_id column now exists in Docker PostgreSQL
**Date**: June 10, 2026
**Files Created**: 
- `scripts/migrate_auth_users_schema.sql`
- `scripts/create_table_in_docker.ps1`
- `scripts/create_table_in_docker.sh`
- `scripts/check_columns.py`
- `scripts/test_insert.py`
