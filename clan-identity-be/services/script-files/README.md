# Auth Database Scripts

Python scripts for managing the clan_identity database tables.

## Prerequisites

```bash
pip install asyncpg python-dotenv
```

## Available Scripts

### 1. create_auth_tables.py
Creates all clan_identity tables by executing SQL files in order.

**Usage:**
```bash
python create_auth_tables.py
```

**What it does:**
- Creates the clan_identity database if it doesn't exist
- Executes all SQL files in sequence:
  - 00_init_auth_database.sql (extensions and initialization)
  - 01_create_auth_users_table.sql
  - 02_create_login_attempts_table.sql
  - 03_create_sessions_table.sql
- Creates all indexes and triggers
- Shows summary of execution

### 2. verify_auth_tables.py
Verifies that all tables exist and shows their structure.

**Usage:**
```bash
python verify_auth_tables.py
```

**What it shows:**
- List of all tables
- Column details for each table
- Indexes for each table
- Row counts
- Table sizes

### 3. drop_auth_tables.py
⚠️ **WARNING: Destructive operation!**

Drops all clan_identity tables and their data.

**Usage:**
```bash
python drop_auth_tables.py
```

**Safety:**
- Requires typing 'YES' to confirm
- Drops tables in correct order (reverse foreign key dependencies)

## Environment Variables

Scripts read from `.env` file or environment:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=clan_user
POSTGRES_PASSWORD=clan_password
```

## Quick Start

```bash
# 1. Create tables
python create_auth_tables.py

# 2. Verify tables were created
python verify_auth_tables.py

# 3. (Optional) Drop all tables
python drop_auth_tables.py
```

## Docker Usage

If running in Docker:

```bash
# Copy script into container
docker cp create_auth_tables.py clan-auth-service:/app/

# Execute inside container
docker exec -it clan-auth-service python create_auth_tables.py
```

Or use docker-compose exec:

```bash
docker-compose exec auth-service python /app/scripts/create_auth_tables.py
```

## Troubleshooting

### Connection Error
```
Error: could not connect to server
```
**Solution:** Check PostgreSQL is running and credentials are correct

### Database Already Exists
```
Database clan_identity already exists
```
**Solution:** This is normal, script will continue with table creation

### Permission Denied
```
Error: permission denied to create database
```
**Solution:** Ensure the database user has CREATE DATABASE privileges

## Related Files

- SQL files: `../sql-files/`
- Models: `../user-service/models/`
