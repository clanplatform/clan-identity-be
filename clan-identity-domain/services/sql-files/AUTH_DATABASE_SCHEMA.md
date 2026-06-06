# Auth Database Schema Documentation

## Overview

**Database Name:** `auth_db`  
**Service:** auth-service  
**Purpose:** Authentication, session management, and security tracking  
**PostgreSQL Version:** 16+

## Architecture Notes

### Cross-Service References

⚠️ **Important:** This database references user data from `admin_service.usersetup_basic` but **does NOT use foreign key constraints**.

**Reason:** Microservices architecture best practice - services should be independently deployable and not have direct database dependencies on other services.

**Implications:**
- Application layer must handle referential integrity
- Orphaned records possible if admin_service users are deleted
- Periodic cleanup/sync jobs recommended
- Use event-driven architecture for data consistency

## Tables

### 1. auth_users

**Status:** ⚠️ NOT USED FOR PRIMARY AUTHENTICATION  
**Purpose:** User credential cache (for future use)

**Note:** Users are authenticated against `admin_service.usersetup_basic`. This table exists for potential caching and future features.

#### Schema

```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY,
    admin_user_id UUID UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    employee_id VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'active',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    password_changed TIMESTAMPTZ,
    is_password_change_required BOOLEAN DEFAULT TRUE,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMPTZ,
    last_login TIMESTAMPTZ,
    last_login_ip VARCHAR(45),
    failed_login_attempts VARCHAR(10) DEFAULT '0',
    locked_until TIMESTAMPTZ,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    two_factor_backup_codes TEXT,
    current_token TEXT,
    roles UUID[],
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| admin_user_id | UUID | Reference to admin_service user (no FK) |
| email | VARCHAR(255) | User email (unique) |
| username | VARCHAR(100) | Username (unique) |
| password_hash | VARCHAR(255) | Bcrypt hashed password |
| status | VARCHAR(50) | active, inactive, suspended, locked |
| two_factor_enabled | BOOLEAN | Whether 2FA is enabled |
| roles | UUID[] | Array of role IDs from admin_service |

#### Indexes

- `idx_auth_users_admin_user_id` on admin_user_id
- `idx_auth_users_email` on email
- `idx_auth_users_username` on username
- `idx_auth_users_status` on status
- `idx_auth_users_is_active` on is_active
- `idx_auth_users_active_status` on (is_active, status)

#### Constraints

- `status` CHECK: Must be one of 'active', 'inactive', 'suspended', 'locked'
- `email` UNIQUE
- `username` UNIQUE
- `employee_id` UNIQUE

---

### 2. login_attempts

**Purpose:** Track all login attempts for security monitoring, rate limiting, and audit

#### Schema

```sql
CREATE TABLE login_attempts (
    id UUID PRIMARY KEY,
    user_id UUID,
    email_or_username VARCHAR(255) NOT NULL,
    attempt_type VARCHAR(50) DEFAULT 'password',
    is_successful BOOLEAN DEFAULT FALSE,
    failure_reason VARCHAR(100),
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    country VARCHAR(100),
    city VARCHAR(100),
    risk_score VARCHAR(10),
    is_suspicious BOOLEAN DEFAULT FALSE,
    suspicious_reason VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Reference to admin_service user (no FK) |
| email_or_username | VARCHAR(255) | Login identifier used |
| attempt_type | VARCHAR(50) | password, otp, 2fa, sso, biometric |
| is_successful | BOOLEAN | Whether attempt succeeded |
| failure_reason | VARCHAR(100) | invalid_credentials, account_locked, etc. |
| ip_address | VARCHAR(45) | Client IP (IPv4/IPv6) |
| device_fingerprint | VARCHAR(255) | Unique device identifier |
| risk_score | VARCHAR(10) | Risk score 0-100 |
| is_suspicious | BOOLEAN | Suspicious activity flag |

#### Indexes

- `idx_login_attempts_user_id` on user_id
- `idx_login_attempts_email_username` on email_or_username
- `idx_login_attempts_ip_address` on ip_address
- `idx_login_attempts_created_at` on created_at
- `idx_login_attempts_failed_recent` on (email_or_username, is_successful, created_at) WHERE is_successful = FALSE
- `idx_login_attempts_suspicious` on (is_suspicious, created_at) WHERE is_suspicious = TRUE
- `idx_login_attempts_ip_recent` on (ip_address, created_at, is_successful)

#### Use Cases

1. **Rate Limiting:** Count failed attempts per email/IP in time window
2. **Brute Force Detection:** Track suspicious patterns
3. **Security Audit:** Compliance and forensics
4. **User Analytics:** Login patterns and behavior

#### Maintenance

- Auto-cleanup after 90 days (via `cleanup_old_login_attempts()`)
- Consider partitioning for high-volume systems
- Monitor for suspicious activity patterns

---

### 3. sessions

**Purpose:** Active session management, device tracking, and security

#### Schema

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    access_token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_reason VARCHAR(100),
    device_id VARCHAR(255),
    device_type VARCHAR(50),
    device_name VARCHAR(255),
    device_fingerprint VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    browser VARCHAR(100),
    os VARCHAR(100),
    country VARCHAR(100),
    city VARCHAR(100),
    is_trusted BOOLEAN DEFAULT FALSE,
    trusted_at TIMESTAMPTZ,
    last_activity TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_activity_ip VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
```

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Reference to admin_service user (no FK) |
| access_token_hash | VARCHAR(255) | SHA-256 hash of JWT access token |
| refresh_token_hash | VARCHAR(255) | SHA-256 hash of refresh token |
| is_active | BOOLEAN | Session currently active |
| is_revoked | BOOLEAN | Session has been revoked |
| device_type | VARCHAR(50) | web, mobile, tablet, desktop, api |
| device_fingerprint | VARCHAR(255) | Unique device identifier |
| is_trusted | BOOLEAN | Trusted device flag |
| expires_at | TIMESTAMPTZ | Session expiration time |
| last_activity | TIMESTAMPTZ | Last activity timestamp |

#### Indexes

- `idx_sessions_user_id` on user_id
- `idx_sessions_access_token_hash` on access_token_hash
- `idx_sessions_refresh_token_hash` on refresh_token_hash WHERE NOT NULL
- `idx_sessions_user_active` on (user_id, is_active, expires_at) WHERE active AND not revoked
- `idx_sessions_expires_at` on expires_at
- `idx_sessions_device_fingerprint` on device_fingerprint
- `idx_sessions_trusted` on (user_id, is_trusted, device_fingerprint) WHERE trusted

#### Functions

**auto_revoke_expired_sessions()**
- Automatically marks expired sessions as revoked
- Run every 15 minutes via pg_cron

**cleanup_old_sessions()**
- Deletes revoked sessions older than 30 days
- Run daily via pg_cron

**revoke_user_sessions(user_id, reason)**
- Revokes all active sessions for a user
- Use for logout, security incidents, password changes

#### Use Cases

1. **Multi-Device Sessions:** Track all user sessions across devices
2. **Session Security:** Detect suspicious devices/locations
3. **Trusted Devices:** Remember user devices
4. **Session Management:** List and revoke active sessions
5. **Idle Timeout:** Auto-revoke inactive sessions

---

## Database Functions

### Cleanup Functions

```sql
-- Delete login attempts older than 90 days
SELECT cleanup_old_login_attempts();

-- Delete revoked sessions older than 30 days
SELECT cleanup_old_sessions();

-- Auto-revoke expired sessions
SELECT auto_revoke_expired_sessions();
```

### Session Management

```sql
-- Revoke all sessions for a user
SELECT revoke_user_sessions('user-uuid', 'security');

-- Revoke reasons: manual, expired, security, logout, password_change
```

## Triggers

### auth_users Table

- `trigger_auth_users_updated_at`: Updates `updated_at` on row modification

### sessions Table

- `trigger_sessions_last_activity`: Updates `last_activity` timestamp

## Performance Considerations

### Indexes Strategy

1. **Lookup Indexes:** Primary keys, unique constraints
2. **Filter Indexes:** Status, active flags
3. **Composite Indexes:** Multi-column queries (user_id + is_active)
4. **Partial Indexes:** Conditional lookups (WHERE is_active = TRUE)
5. **Time-based Indexes:** created_at, expires_at for cleanup

### Query Optimization

**Get Active Sessions for User:**
```sql
SELECT * FROM sessions 
WHERE user_id = ? 
  AND is_active = TRUE 
  AND is_revoked = FALSE
  AND expires_at > NOW()
ORDER BY last_activity DESC;
-- Uses: idx_sessions_user_active
```

**Rate Limiting - Failed Login Attempts:**
```sql
SELECT COUNT(*) FROM login_attempts
WHERE email_or_username = ?
  AND is_successful = FALSE
  AND created_at > NOW() - INTERVAL '15 minutes';
-- Uses: idx_login_attempts_failed_recent
```

**Find Suspicious Activity:**
```sql
SELECT * FROM login_attempts
WHERE is_suspicious = TRUE
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
-- Uses: idx_login_attempts_suspicious
```

### Partitioning (High Volume)

For systems with millions of login attempts:

```sql
-- Partition login_attempts by month
CREATE TABLE login_attempts_partitioned (
    LIKE login_attempts INCLUDING ALL
) PARTITION BY RANGE (created_at);

CREATE TABLE login_attempts_2024_06 
PARTITION OF login_attempts_partitioned
FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
```

## Security Best Practices

### Password Storage
- ✅ Use bcrypt with cost factor 12+
- ✅ Store hashes only, never plaintext
- ✅ Enforce password complexity rules in application

### Token Storage
- ✅ Store SHA-256 hashes of tokens, not raw tokens
- ✅ Use short expiration times (access token: 30min)
- ✅ Rotate refresh tokens on use

### Rate Limiting
- ✅ Max 5 failed attempts per email in 15 minutes
- ✅ Max 20 failed attempts per IP in 15 minutes
- ✅ Implement progressive delays

### Session Security
- ✅ Revoke all sessions on password change
- ✅ Detect and flag suspicious logins (new device, location)
- ✅ Implement idle timeout (30 minutes)
- ✅ Max sessions per user (e.g., 10 devices)

### IP Geolocation
- ✅ Track login locations
- ✅ Alert on suspicious location changes
- ✅ Consider VPN/proxy detection

## Monitoring Queries

### Active Sessions
```sql
SELECT 
    COUNT(*) as total_sessions,
    COUNT(DISTINCT user_id) as unique_users
FROM sessions
WHERE is_active = TRUE AND is_revoked = FALSE;
```

### Failed Login Rate
```sql
SELECT 
    COUNT(*) FILTER (WHERE is_successful = FALSE) * 100.0 / COUNT(*) as failure_rate
FROM login_attempts
WHERE created_at > NOW() - INTERVAL '1 hour';
```

### Suspicious Activity
```sql
SELECT 
    COUNT(*) as suspicious_attempts,
    COUNT(DISTINCT email_or_username) as affected_users
FROM login_attempts
WHERE is_suspicious = TRUE
  AND created_at > NOW() - INTERVAL '24 hours';
```

### Top Failed IPs
```sql
SELECT 
    ip_address,
    COUNT(*) as failed_attempts
FROM login_attempts
WHERE is_successful = FALSE
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip_address
ORDER BY failed_attempts DESC
LIMIT 10;
```

## Backup and Recovery

### Backup Strategy

```bash
# Full database backup
pg_dump -U clan_user -d auth_db -F c -f auth_db_backup.dump

# Schema only
pg_dump -U clan_user -d auth_db --schema-only -f auth_db_schema.sql

# Data only
pg_dump -U clan_user -d auth_db --data-only -f auth_db_data.sql
```

### Restore

```bash
# Restore from dump
pg_restore -U clan_user -d auth_db auth_db_backup.dump

# Restore from SQL
psql -U clan_user -d auth_db -f auth_db_schema.sql
```

## Migration Path

### From Monolith to Microservices

If migrating from a monolithic database:

1. **Phase 1:** Create auth_db alongside existing database
2. **Phase 2:** Dual-write to both databases
3. **Phase 3:** Migrate historical data
4. **Phase 4:** Switch reads to auth_db
5. **Phase 5:** Remove old authentication tables

### Data Sync

Use event-driven architecture:

```python
# When user created in admin_service
publish_event("user.created", user_data)

# auth_service subscriber
@subscribe("user.created")
def sync_user(user_data):
    # Create auth_user if needed
    pass
```

## Troubleshooting

### Orphaned Records

Check for sessions without users in admin_service:

```sql
-- Requires dblink extension
SELECT s.id, s.user_id, s.created_at
FROM sessions s
WHERE NOT EXISTS (
    SELECT 1 FROM dblink(
        'admin_db_connection',
        'SELECT id FROM usersetup_basic WHERE id = ''' || s.user_id || ''''
    ) AS t(id UUID)
);
```

### Stuck Sessions

Find sessions that should be expired:

```sql
UPDATE sessions
SET is_active = FALSE, is_revoked = TRUE, revoked_reason = 'expired'
WHERE expires_at < NOW()
  AND is_active = TRUE;
```

### Cleanup Old Data

```sql
-- Delete old login attempts
DELETE FROM login_attempts
WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete old revoked sessions
DELETE FROM sessions
WHERE is_revoked = TRUE
  AND revoked_at < NOW() - INTERVAL '30 days';
```

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-06-06 | Initial schema creation |

## Related Documentation

- [SQL Files README](./README.md)
- [Scripts README](../script-files/README.md)
- [SQLAlchemy Models](../user-service/models/)
