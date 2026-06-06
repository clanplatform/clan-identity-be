# Quick Start Guide - Auth Database Setup

## Prerequisites

- Docker and Docker Compose running
- PostgreSQL container up
- Python 3.12+ with asyncpg installed

## Option 1: Using Python Scripts (Recommended)

### Step 1: Install Dependencies

```bash
pip install asyncpg python-dotenv
```

### Step 2: Set Environment Variables

Create or update `.env` in project root:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=clan_user
POSTGRES_PASSWORD=clan_password
```

### Step 3: Run Creation Script

```bash
cd services/script-files
python create_auth_tables.py
```

**Output:**
```
================================================================================
AUTH DATABASE TABLE CREATION SCRIPT
================================================================================
Database: auth_db
Host: localhost:5432
User: clan_user
================================================================================

✓ Database auth_db created successfully
✓ Connected to auth_db successfully

================================================================================
Executing: 00_init_auth_database.sql
================================================================================
✓ Successfully executed 00_init_auth_database.sql

[... continues for all tables ...]

✓ All tables created successfully!
```

### Step 4: Verify Tables

```bash
python verify_auth_tables.py
```

## Option 2: Using Docker Compose

### Step 1: Start Services

```bash
docker-compose up -d postgres
```

### Step 2: Wait for PostgreSQL

```bash
docker-compose logs -f postgres
# Wait for "database system is ready to accept connections"
```

### Step 3: Execute SQL Files

```bash
# Copy SQL files to container
docker cp services/sql-files/ clan-identity-postgres:/tmp/

# Execute in PostgreSQL
docker exec -it clan-identity-postgres bash

# Inside container:
psql -U clan_user -d auth_db -f /tmp/sql-files/00_init_auth_database.sql
psql -U clan_user -d auth_db -f /tmp/sql-files/01_create_auth_users_table.sql
psql -U clan_user -d auth_db -f /tmp/sql-files/02_create_login_attempts_table.sql
psql -U clan_user -d auth_db -f /tmp/sql-files/03_create_sessions_table.sql
```

## Option 3: Using psql Directly

### Step 1: Connect to Database

```bash
psql -U clan_user -h localhost -p 5432 -d auth_db
```

### Step 2: Execute Files

```sql
\i services/sql-files/00_init_auth_database.sql
\i services/sql-files/01_create_auth_users_table.sql
\i services/sql-files/02_create_login_attempts_table.sql
\i services/sql-files/03_create_sessions_table.sql
```

## Verification

### Check Tables Exist

```sql
\dt
```

Expected output:
```
          List of relations
 Schema |      Name       | Type  |   Owner
--------+-----------------+-------+-----------
 public | auth_users      | table | clan_user
 public | login_attempts  | table | clan_user
 public | sessions        | table | clan_user
```

### Check Table Structure

```sql
\d auth_users
\d login_attempts
\d sessions
```

### Check Indexes

```sql
\di
```

### Test Queries

```sql
-- Count records (should be 0)
SELECT 
    'auth_users' as table_name, COUNT(*) FROM auth_users
UNION ALL
SELECT 'login_attempts', COUNT(*) FROM login_attempts
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions;
```

## Common Issues

### Issue: "database auth_db does not exist"

**Solution:**
```sql
-- Connect to postgres database first
psql -U clan_user -d postgres

-- Create the database
CREATE DATABASE auth_db;

-- Exit and reconnect to auth_db
\c auth_db
```

### Issue: "relation already exists"

**Solution:** Tables already created. To recreate:

```bash
# Drop all tables
python drop_auth_tables.py

# Recreate
python create_auth_tables.py
```

### Issue: Connection refused

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# Start if needed
docker-compose up -d postgres

# Check logs
docker-compose logs postgres
```

### Issue: Permission denied

**Solution:**
```sql
-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE auth_db TO clan_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO clan_user;
```

## Next Steps

After successful setup:

1. **Start Auth Service**
   ```bash
   docker-compose up -d auth-service
   ```

2. **Test API**
   ```bash
   curl http://localhost:8001/health
   ```

3. **Access API Docs**
   Open: http://localhost:8001/docs

4. **Monitor Logs**
   ```bash
   docker-compose logs -f auth-service
   ```

## Cleanup (if needed)

### Drop All Tables

```bash
cd services/script-files
python drop_auth_tables.py
```

### Drop Database

```sql
DROP DATABASE IF EXISTS auth_db;
```

### Remove Docker Volumes

```bash
docker-compose down -v
```

## File Locations

- **SQL Files:** `services/sql-files/`
- **Python Scripts:** `services/script-files/`
- **Documentation:** `services/sql-files/AUTH_DATABASE_SCHEMA.md`
- **Models:** `services/user-service/models/`

## Support

- Check README.md in sql-files/ for detailed documentation
- Check AUTH_DATABASE_SCHEMA.md for schema details
- Check script-files/README.md for script usage
