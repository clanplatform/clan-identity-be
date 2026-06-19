# Auth Database SQL Files

SQL scripts for creating and managing clan_identity database schema.

## Database: clan_identity

The clan_identity database is part of the auth-service microservice and stores authentication-related data.

## Tables

### 1. auth_users
User authentication table (cached from clan_platform).

**Purpose:** 
- Stores user credentials and authentication data
- NOT used for primary authentication (clan_platform.usersetup_basic is the source)
- Used for caching and potential future features

**Key Columns:**
- `id`: Primary key (UUID)
- `admin_user_id`: Reference to clan_platform user
- `email`, `username`: Login identifiers
- `password_hash`: Bcrypt hashed password
- `two_factor_enabled`: 2FA flag
- `status`: Account status (active, inactive, suspended, locked)

### 2. login_attempts
Login attempt tracking and security monitoring.

**Purpose:**
- Track all login attempts (successful and failed)
- Rate limiting and brute force protection
- Security monitoring and audit
- Suspicious activity detection

**Key Columns:**
- `id`: Primary key (UUID)
- `user_id`: Reference to clan_platform user
- `email_or_username`: Login identifier used
- `is_successful`: Attempt result
- `ip_address`: Client IP
- `risk_score`: Calculated risk score (0-100)
- `is_suspicious`: Suspicious activity flag

### 3. sessions
Active session management and tracking.

**Purpose:**
- Track active user sessions
- Device and location tracking
- Session security and trust management
- Multi-device session handling

**Key Columns:**
- `id`: Primary key (UUID)
- `user_id`: Reference to clan_platform user
- `access_token_hash`: Hashed JWT access token
- `refresh_token_hash`: Hashed refresh token
- `is_active`, `is_revoked`: Session status
- `device_fingerprint`: Unique device identifier
- `expires_at`: Session expiration

## File Execution Order

Execute SQL files in this exact order:

1. **00_init_auth_database.sql** - Database initialization
   - Creates extensions (uuid-ossp, pgcrypto)
   - Sets up schemas
   - Configures database settings

2. **01_create_auth_users_table.sql** - Auth users table
   - Creates auth_users table
   - Creates indexes
   - Creates triggers

3. **02_create_login_attempts_table.sql** - Login tracking
   - Creates login_attempts table
   - Creates indexes for performance
   - Cleanup functions

4. **03_create_sessions_table.sql** - Session management
   - Creates sessions table
   - Session management functions
   - Auto-revocation triggers

5. **99_complete_setup.sql** - Complete setup (alternative)
   - Executes all files above
   - Verification queries
   - Summary report

## Usage

### Method 1: Using psql

```bash
# Connect to PostgreSQL
psql -U clan_user -d clan_identity

# Execute files in order
\i 00_init_auth_database.sql
\i 01_create_auth_users_table.sql
\i 02_create_login_attempts_table.sql
\i 03_create_sessions_table.sql

# Or execute all at once
\i 99_complete_setup.sql
```

### Method 2: Using Python Script

```bash
cd ../script-files
python create_auth_tables.py
```

### Method 3: Direct psql Command

```bash
psql -U clan_user -d clan_identity -f 00_init_auth_database.sql
psql -U clan_user -d clan_identity -f 01_create_auth_users_table.sql
psql -U clan_user -d clan_identity -f 02_create_login_attempts_table.sql
psql -U clan_user -d clan_identity -f 03_create_sessions_table.sql
```

### Method 4: Docker

```bash
# Copy SQL files to container
docker cp . clan-identity-postgres:/tmp/sql-files/

# Execute in container
docker exec -it clan-identity-postgres psql -U clan_user -d clan_identity -f /tmp/sql-files/00_init_auth_database.sql
```

## Important Notes

### Foreign Key Constraints

⚠️ **No Foreign Key Constraints to clan_platform**

The `user_id` columns in `login_attempts` and `sessions` tables reference `clan_platform.usersetup_basic.id` but **DO NOT** use foreign key constraints.

**Reason:** Cross-service database constraints are avoided in microservices architecture for service independence.

**Implications:**
- Application must handle referential integrity
- Orphaned records are possible if users are deleted from clan_platform
- Periodic cleanup jobs recommended

### Performance Considerations

#### Indexes
- All tables have optimized indexes for common queries
- Composite indexes for complex filter operations
- Partial indexes for conditional lookups

#### Cleanup
- `login_attempts`: Auto-cleanup after 90 days
- `sessions`: Auto-cleanup revoked sessions after 30 days
- Schedule cleanup jobs with pg_cron (optional)

### Security

- Passwords stored as bcrypt hashes
- Tokens stored as SHA-256 hashes
- Audit triggers available (commented out)
- Supports IP geolocation tracking
- Risk scoring capabilities

## Maintenance Functions

### Auto-revoke Expired Sessions
```sql
SELECT auto_revoke_expired_sessions();
```

### Cleanup Old Login Attempts
```sql
SELECT cleanup_old_login_attempts();
```

### Cleanup Old Sessions
```sql
SELECT cleanup_old_sessions();
```

### Revoke User Sessions
```sql
SELECT revoke_user_sessions('user-uuid-here', 'security');
```

## Monitoring Queries

### Active Sessions Count
```sql
SELECT COUNT(*) FROM sessions WHERE is_active = TRUE AND is_revoked = FALSE;
```

### Failed Login Attempts (Last Hour)
```sql
SELECT COUNT(*) FROM login_attempts 
WHERE is_successful = FALSE 
AND created_at > NOW() - INTERVAL '1 hour';
```

### Suspicious Login Attempts
```sql
SELECT * FROM login_attempts 
WHERE is_suspicious = TRUE 
ORDER BY created_at DESC 
LIMIT 10;
```

### User Active Sessions
```sql
SELECT * FROM sessions 
WHERE user_id = 'user-uuid' 
AND is_active = TRUE;
```

## Verification

After running scripts, verify with:

```sql
-- List all tables
\dt

-- Check table structure
\d auth_users
\d login_attempts
\d sessions

-- List indexes
\di

-- Table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public';
```

## Rollback

To drop all tables:

```sql
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS login_attempts CASCADE;
DROP TABLE IF EXISTS auth_users CASCADE;
```

Or use the drop script:
```bash
cd ../script-files
python drop_auth_tables.py
```

## Related Documentation

- Models: `../user-service/models/`
- Scripts: `../script-files/`
- Docker: `../../docker-compose.yml`
