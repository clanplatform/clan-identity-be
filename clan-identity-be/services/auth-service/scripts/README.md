# Auth Service Database Scripts

This directory contains database initialization and management scripts for the auth service.

## Quick Start

### Initialize Database (First Time Setup)

Choose one of the following methods:

#### 1. Using Python (Recommended)
```bash
# From auth-service directory
python scripts/init_db.py

# Or with custom settings via environment variables
POSTGRES_HOST=localhost POSTGRES_PORT=5432 python scripts/init_db.py
```

#### 2. Using PowerShell (Windows)
```powershell
# From auth-service/scripts directory
.\init_db.ps1

# With custom settings
.\init_db.ps1 -Host localhost -Port 5432 -User postgres -Password root -Database clan_identity

# Using SQL script instead of Python
.\init_db.ps1 -UseSQL
```

#### 3. Using Bash (Linux/macOS)
```bash
# Make script executable
chmod +x scripts/init_db.sh

# Run with defaults
./scripts/init_db.sh

# With custom settings
./scripts/init_db.sh -h localhost -p 5432 -u postgres -w root -d clan_identity

# Using SQL script
./scripts/init_db.sh --sql
```

#### 4. Using SQL Directly
```bash
psql -h localhost -p 5432 -U postgres -d postgres -f scripts/init_db.sql
```

#### 5. Using Docker
```bash
# If running from docker-compose
docker-compose exec auth-service python scripts/init_db.py

# Or execute SQL script from postgres container
docker-compose exec postgres psql -U postgres -d postgres -f /app/scripts/init_db.sql
```

## Available Scripts

### `init_db.py`
Python script for database initialization.
- Creates database if it doesn't exist
- Creates all tables (auth_users, sessions, login_attempts)
- Creates indexes for performance
- Verifies database connection
- Provides detailed logging

**Features:**
- Automatic database creation
- Table existence checking
- Index creation with error handling
- Connection verification
- Detailed progress output

### `init_db.sql`
SQL script for database initialization.
- Complete SQL schema definition
- All indexes and triggers
- Database comments for documentation
- Can be run with psql or any PostgreSQL client

### `init_db.ps1`
PowerShell wrapper for Windows.
- Parameter support for configuration
- Connection verification
- Can use either Python or SQL script
- Colored output for better readability

### `init_db.sh`
Bash wrapper for Linux/macOS.
- Parameter support for configuration
- Connection verification
- Can use either Python or SQL script
- Colored output for better readability

### `drop_db.py`
Database cleanup script (USE WITH CAUTION!)
- Drops all tables or entire database
- Requires confirmation before execution
- Supports force mode for automation

**Usage:**
```bash
# Drop only tables (keeps database)
python scripts/drop_db.py

# Drop entire database
python scripts/drop_db.py --full

# Force drop without confirmation (dangerous!)
python scripts/drop_db.py --full --force
```

## Database Schema

The auth service creates three main tables:

### 1. `auth_users`
Stores authenticated user data (mirrors clan_platform.usersetup_basic)

**Key Columns:**
- `id` - Primary key (UUID)
- `user_setup_id` - Reference to admin service user (UUID)
- `email`, `username`, `employee_id` - Unique identifiers
- `password_hash` - Encrypted password
- `is_password_change` - Password change status
- `status` - User account status
- `manage_roles`, `entities` - Authorization data

### 2. `sessions`
Manages user sessions and JWT tokens

**Key Columns:**
- `id` - Primary key (UUID)
- `user_id` - User reference (UUID)
- `session_token`, `refresh_token` - JWT tokens
- `device_type`, `device_name`, `browser` - Device info
- `ip_address`, `country`, `city` - Location tracking
- `is_active`, `is_revoked` - Session status
- `expires_at` - Expiration timestamp

### 3. `login_attempts`
Tracks all login attempts for security monitoring

**Key Columns:**
- `id` - Primary key (UUID)
- `user_id` - User reference (UUID, nullable)
- `email_or_username` - Attempted credentials
- `is_successful`, `failure_reason` - Result tracking
- `ip_address`, `user_agent` - Client information
- `risk_score`, `is_suspicious` - Risk assessment
- `country`, `city` - Location tracking

## Configuration

### Environment Variables

Set these before running initialization scripts:

```bash
# Auth Service Database
POSTGRES_HOST=localhost          # Default: localhost
POSTGRES_PORT=5432              # Default: 5432
POSTGRES_USER=postgres          # Default: postgres
POSTGRES_PASSWORD=root          # Default: root
POSTGRES_DB=clan_identity        # Default: clan_identity

# Admin Service Database (for user authentication)
ADMIN_POSTGRES_HOST=localhost   # Can be different host
ADMIN_POSTGRES_PORT=5432
ADMIN_POSTGRES_USER=postgres
ADMIN_POSTGRES_PASSWORD=root
ADMIN_DB=clan_platform
```

### Using .env File

You can also configure via the `.env` file in `config/environments/`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root
POSTGRES_DB=clan_identity
```

## Verification

After initialization, verify the setup:

```bash
# Check if database exists
psql -h localhost -p 5432 -U postgres -l | grep clan_identity

# Check tables
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\dt"

# Expected output:
#             List of relations
#  Schema |      Name       | Type  |  Owner
# --------+-----------------+-------+----------
#  public | auth_users      | table | postgres
#  public | login_attempts  | table | postgres
#  public | sessions        | table | postgres

# Check table structure
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\d auth_users"
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\d sessions"
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\d login_attempts"

# Check indexes
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\di"
```

## Troubleshooting

### Connection Refused
**Problem:** Cannot connect to PostgreSQL
**Solutions:**
- Ensure PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Check if port is correct (5432 or 5433 for docker)
- Verify credentials in environment variables

### Database Already Exists
**Problem:** Database creation fails because it exists
**Solution:**
- The script will skip database creation and continue
- To start fresh, use `drop_db.py --full` first

### Permission Denied
**Problem:** User doesn't have permission to create database
**Solution:**
- Grant CREATE privilege: `ALTER USER postgres CREATEDB;`
- Or run as superuser

### Tables Already Exist
**Problem:** Tables already exist in database
**Solution:**
- The script uses `CREATE TABLE IF NOT EXISTS`
- To recreate tables, use `drop_db.py` first

### Import Errors (Python)
**Problem:** Cannot import models or database module
**Solution:**
- Ensure you're in the auth-service directory
- Check Python path: `sys.path.insert(0, str(project_root))`
- Verify all dependencies are installed: `pip install -r requirements.txt`

### psql Command Not Found
**Problem:** `psql` or `pg_isready` not in PATH
**Solution:**
- Install PostgreSQL client tools
- Add PostgreSQL bin directory to PATH
- Or use Python script which doesn't require psql

## Migration Strategy

For future schema changes, use one of these approaches:

### 1. Alembic (Recommended for Production)
```bash
# Install alembic
pip install alembic

# Initialize alembic (one time)
alembic init alembic

# Configure alembic.ini with database URL
# Edit env.py to import your models

# Create migration
alembic revision --autogenerate -m "Add column to auth_users"

# Review the generated migration file

# Apply migration
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### 2. Manual SQL Scripts
Create versioned SQL files in `scripts/migrations/`:
```
001_initial_schema.sql
002_add_oauth_columns.sql
003_add_mfa_support.sql
```

Track applied migrations in a table:
```sql
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

### 3. Python Migration Scripts
Create Python scripts similar to `init_db.py` for each migration.

## Production Considerations

### Before Making Changes

1. **Always Backup First**
   ```bash
   # Full database backup
   pg_dump -h host -U user -d clan_identity > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Schema only
   pg_dump -h host -U user -d clan_identity --schema-only > schema_backup.sql
   
   # Data only
   pg_dump -h host -U user -d clan_identity --data-only > data_backup.sql
   ```

2. **Test in Staging First**
   - Never test migrations directly in production
   - Use identical database structure in staging
   - Test rollback procedures

3. **Use Transactions**
   - Wrap DDL statements in transactions when possible
   - Have rollback scripts ready

### Performance Monitoring

```sql
-- Check table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Find slow queries (if pg_stat_statements enabled)
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Maintenance Tasks

```sql
-- Vacuum and analyze tables
VACUUM ANALYZE auth_users;
VACUUM ANALYZE sessions;
VACUUM ANALYZE login_attempts;

-- Reindex tables (if needed)
REINDEX TABLE auth_users;
REINDEX TABLE sessions;
REINDEX TABLE login_attempts;

-- Check for bloat
SELECT
    tablename,
    pg_size_pretty(pg_relation_size(tablename::regclass)) as size,
    n_dead_tup,
    n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > 0;
```

## Next Steps

After successful database initialization:

1. **Start the Auth Service**
   ```bash
   python main.py
   ```

2. **Check Service Health**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/api/v1/health
   ```

3. **View API Documentation**
   - Swagger UI: http://localhost:8001/docs
   - ReDoc: http://localhost:8001/redoc

4. **Test Database Connection**
   ```bash
   python scripts/test_admin_db_connection.py
   ```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review PostgreSQL logs
3. Check application logs
4. Verify all environment variables are set correctly
5. Ensure all dependencies are installed

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
