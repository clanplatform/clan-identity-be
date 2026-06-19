# Auth Service Database Status

## ✅ Database Successfully Created

**Date:** 2026-06-16 12:25:33  
**Database:** clan_identity  
**Host:** localhost (Docker: clan-identity-postgres)  
**Port:** 5433 (Docker internal: 5432)  
**PostgreSQL Version:** 18.0

---

## 📊 Tables Created

| Table | Description | Columns | Indexes | Status |
|-------|-------------|---------|---------|--------|
| **auth_users** | Authenticated user data | 27 | 8 | ✅ Ready |
| **sessions** | User session management | 24 | 5 | ✅ Ready |
| **login_attempts** | Login security tracking | 15 | 7 | ✅ Ready |

**Total:** 3 tables, 66 columns, 20 indexes

---

## 🔍 Table Details

### auth_users
Stores authenticated user data (mirrors clan_platform.usersetup_basic)

**Key Features:**
- UUID primary key
- Unique constraints on: email, username, employee_id, user_setup_id
- Password hash storage
- Employment status tracking
- Organizational structure (department, division, job_code)
- Role and entity management
- Automatic timestamps (created_at, updated_at)

**Indexes:**
- Primary key on `id`
- Unique indexes on `email`, `username`, `employee_id`, `user_setup_id`
- Composite index on `employee_id, status`
- Partial index on `status` (for active users only)

### sessions
Manages user sessions and JWT tokens

**Key Features:**
- Session and refresh token hashing
- Device tracking (type, name, fingerprint)
- Location tracking (IP, country, city)
- Browser and OS detection
- Session revocation support
- Device trust management
- Activity tracking

**Indexes:**
- Primary key on `id`
- Unique indexes on `access_token_hash`, `refresh_token_hash`
- Index on `user_id`
- Composite indexes for active session queries
- Cleanup index for expired sessions

### login_attempts
Tracks all login attempts for security monitoring

**Key Features:**
- Attempt result tracking (success/failure)
- Risk assessment scoring
- Suspicious activity flagging
- Client information (IP, user agent, device fingerprint)
- Location tracking (country, city)
- Multiple attempt types (password, otp, 2fa, sso)

**Indexes:**
- Primary key on `id`
- Indexes on `user_id`, `email_or_username`, `ip_address`
- Time-based indexes for rate limiting
- Composite indexes for security queries
- Partial index on suspicious attempts

---

## 📈 Current Statistics

```sql
-- Record counts (as of initialization)
auth_users:       0 rows
sessions:         0 rows
login_attempts:   0 rows
```

---

## 🔗 Connection Information

### From Host Machine
```bash
Host: localhost
Port: 5433
Database: clan_identity
User: postgres
Password: root

# Connection string
postgresql://postgres:root@localhost:5433/clan_identity
```

### From Docker Containers
```bash
Host: postgres
Port: 5432
Database: clan_identity
User: postgres
Password: root

# Connection string
postgresql://postgres:root@postgres:5432/clan_identity
```

### Using psql
```bash
# From host
psql -h localhost -p 5433 -U postgres -d clan_identity

# From Docker
docker-compose exec postgres psql -U postgres -d clan_identity
```

---

## ✅ Verification Results

| Check | Status | Notes |
|-------|--------|-------|
| Database Connection | ✓ PASS | PostgreSQL 18.0 running |
| Tables Created | ✓ PASS | All 3 tables exist |
| Indexes Created | ✓ PASS | All 20 indexes created |
| CRUD Operations | ✓ PASS | Read/Write working |
| Admin DB Connection | ⚠️ Expected | Admin service in different environment |

---

## 🚀 Next Steps

### 1. Start the Auth Service
```bash
cd services/auth-service
python main.py
```

Or with Docker:
```bash
docker-compose up auth-service
```

### 2. Access API Documentation
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### 3. Test Endpoints
```bash
# Health check
curl http://localhost:8001/health

# API health
curl http://localhost:8001/api/v1/health
```

### 4. Test Database Connection
```bash
python scripts/test_admin_db_connection.ps1
```

---

## 📝 Useful Commands

### Query Tables
```sql
-- List all tables
\dt

-- Describe table structure
\d auth_users
\d sessions
\d login_attempts

-- List all indexes
\di

-- Count records
SELECT 'auth_users' as table, COUNT(*) FROM auth_users
UNION SELECT 'sessions', COUNT(*) FROM sessions
UNION SELECT 'login_attempts', COUNT(*) FROM login_attempts;

-- Check table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_relation_size(tablename::regclass)) as size
FROM pg_tables
WHERE schemaname = 'public';
```

### Maintenance
```sql
-- Vacuum and analyze
VACUUM ANALYZE auth_users;
VACUUM ANALYZE sessions;
VACUUM ANALYZE login_attempts;

-- Reindex if needed
REINDEX TABLE auth_users;
```

---

## 🛠️ Management Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| init_db.py | Initialize database | `python scripts/init_db.py` |
| verify_db.py | Verify setup | `python scripts/verify_db.py` |
| drop_db.py | Drop database | `python scripts/drop_db.py` |
| init_db.sql | SQL initialization | `psql -f scripts/init_db.sql` |

---

## 📚 Documentation

- Quick Start: `scripts/QUICKSTART.md`
- Full Documentation: `scripts/README.md`
- Migration Guide: `scripts/migrations/README.md`
- Overall Setup: `../../DATABASE_SETUP.md`

---

## ⚠️ Important Notes

1. **Admin Service Integration**
   - The clan_platform database is expected to be in a different environment
   - First-time logins query clan_platform.usersetup_basic
   - After password change, user data is cached in auth_users

2. **Security**
   - Change default passwords before production
   - Use environment variables for credentials
   - Enable SSL/TLS for database connections
   - Implement proper backup strategy

3. **Performance**
   - Connection pooling is configured (pool_size=10, max_overflow=20)
   - Indexes optimized for common queries
   - Regular VACUUM ANALYZE recommended

---

**Status:** ✅ Ready for Development  
**Last Updated:** 2026-06-16  
**Created By:** Database Initialization Script v1.0
