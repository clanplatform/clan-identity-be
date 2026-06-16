# Identity Domain Database Setup Guide

This guide covers database initialization for all services in the identity domain.

## Overview

The identity domain consists of multiple microservices, each with its own PostgreSQL database:

- **auth_service** - Authentication and login management
- **user_service** - User profile management
- **session_service** - Session tracking
- **rbac_service** - Role-based access control
- **oauth_service** - OAuth/SSO integration

## Quick Start - Auth Service

### 1. Start PostgreSQL and Redis
```bash
docker-compose up -d postgres redis
```

### 2. Initialize Auth Service Database
```bash
cd services/auth-service
python scripts/init_db.py
```

### 3. Verify Setup
```bash
python scripts/verify_db.py
```

### 4. Start Auth Service
```bash
python main.py
```

Visit: http://localhost:8001/docs

## Database Architecture

### Auth Service (Port 8001)
**Database:** `auth_service`

**Tables:**
- `auth_users` - Authenticated user data (mirrors admin_service.usersetup_basic)
- `sessions` - User sessions and JWT tokens
- `login_attempts` - Login tracking for security and rate limiting

**Key Features:**
- Cross-database reference to admin_service (no FK constraints)
- Security monitoring and risk assessment
- Device fingerprinting and trust management
- Comprehensive audit trail

### User Service (Port 8002)
**Database:** `user_service`
- User profiles and preferences
- User settings management

### Session Service (Port 8003)
**Database:** `session_service`
- Centralized session management
- Multi-device session tracking

### RBAC Service (Port 8004)
**Database:** `rbac_service`
- Roles and permissions
- Access control policies

### OAuth Service (Port 8005)
**Database:** `oauth_service`
- OAuth providers configuration
- SSO integration

## Docker Compose Setup

The `docker-compose.yml` automatically creates all databases:

```yaml
POSTGRES_MULTIPLE_DATABASES: auth_service,user_service,session_service,rbac_service,oauth_service
```

### Full Stack Startup

```bash
# Start all services
docker-compose up -d

# Initialize all databases
docker-compose exec auth-service python scripts/init_db.py
docker-compose exec user-service python scripts/init_db.py
docker-compose exec session-service python scripts/init_db.py
docker-compose exec rbac-service python scripts/init_db.py
docker-compose exec oauth-service python scripts/init_db.py

# Check logs
docker-compose logs -f auth-service
```

## Connection Configuration

### Default Ports
- PostgreSQL: `5433` (mapped from container 5432)
- Redis: `6380` (mapped from container 6379)
- Auth Service: `8001`
- User Service: `8002`
- Session Service: `8003`
- RBAC Service: `8004`
- OAuth Service: `8005`

### Environment Variables

Create `.env` file or use `config/environments/.env.local`:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root

# Service-specific databases
POSTGRES_DB=auth_service  # Changes per service

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# Admin Service (External)
ADMIN_POSTGRES_HOST=host.docker.internal
ADMIN_POSTGRES_PORT=5432
ADMIN_POSTGRES_USER=postgres
ADMIN_POSTGRES_PASSWORD=root
ADMIN_DB=admin_service
```

## Service-Specific Scripts

Each service has its own initialization scripts:

```
services/
├── auth-service/
│   └── scripts/
│       ├── init_db.py          # Python initialization
│       ├── init_db.sql         # SQL initialization
│       ├── init_db.ps1         # PowerShell wrapper
│       ├── init_db.sh          # Bash wrapper
│       ├── verify_db.py        # Verification script
│       ├── drop_db.py          # Cleanup script
│       ├── QUICKSTART.md       # Quick reference
│       └── README.md           # Full documentation
├── user-service/
│   └── scripts/...
├── session-service/
│   └── scripts/...
├── rbac-service/
│   └── scripts/...
└── oauth-service/
    └── scripts/...
```

## Admin Service Integration

The auth service connects to an **external admin_service database** for user authentication:

1. User logs in through auth service
2. Auth service queries `admin_service.usersetup_basic` for credentials
3. After first password change, user data is cached in `auth_service.auth_users`
4. Subsequent logins use local cache for performance

**Note:** The admin_service database may be:
- In a different repository
- On a different host
- Accessed via `host.docker.internal` from Docker

## Database Management

### Backup

```bash
# Backup single database
pg_dump -h localhost -p 5433 -U postgres -d auth_service > auth_backup.sql

# Backup all databases
for db in auth_service user_service session_service rbac_service oauth_service; do
    pg_dump -h localhost -p 5433 -U postgres -d $db > ${db}_backup_$(date +%Y%m%d).sql
done
```

### Restore

```bash
# Restore database
psql -h localhost -p 5433 -U postgres -d auth_service < auth_backup.sql
```

### Reset Database

```bash
cd services/auth-service
python scripts/drop_db.py --full
python scripts/init_db.py
```

## Verification Commands

### Check All Databases

```bash
# List databases
psql -h localhost -p 5433 -U postgres -l | grep service

# Check auth_service tables
psql -h localhost -p 5433 -U postgres -d auth_service -c "\dt"

# Count records across all tables
psql -h localhost -p 5433 -U postgres -d auth_service -c "
SELECT 
    'auth_users' as table, COUNT(*) FROM auth_users 
UNION 
SELECT 'sessions', COUNT(*) FROM sessions 
UNION 
SELECT 'login_attempts', COUNT(*) FROM login_attempts;
"
```

### Check Docker Services

```bash
# Check container status
docker-compose ps

# Check postgres logs
docker-compose logs postgres

# Check auth-service logs
docker-compose logs auth-service

# Execute commands in container
docker-compose exec postgres psql -U postgres -l
```

## Troubleshooting

### Cannot Connect to PostgreSQL

```bash
# Check if container is running
docker-compose ps postgres

# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Admin Database Not Accessible

This is expected if the admin service is in a different environment. The auth service will:
- Log a warning about admin database connection
- Continue to function for users cached in auth_users
- Require admin database only for first-time logins

### Tables Not Created

```bash
# Check if init script ran
docker-compose logs auth-service | grep "init_db"

# Run manually
docker-compose exec auth-service python scripts/init_db.py

# Check from PostgreSQL
docker-compose exec postgres psql -U postgres -d auth_service -c "\dt"
```

### Port Conflicts

If ports 5433 or 6380 are in use:

```yaml
# Edit docker-compose.yml
services:
  postgres:
    ports:
      - "5434:5432"  # Change external port
  redis:
    ports:
      - "6381:6379"  # Change external port
```

## Development Workflow

1. **Start Infrastructure**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Initialize Databases**
   ```bash
   cd services/auth-service
   python scripts/init_db.py
   ```

3. **Run Service Locally** (outside Docker for development)
   ```bash
   # Update .env to use localhost:5433
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5433
   
   python main.py
   ```

4. **Or Run in Docker**
   ```bash
   docker-compose up auth-service
   ```

## Production Considerations

1. **Security**
   - ✓ Use strong passwords
   - ✓ Enable SSL/TLS for database connections
   - ✓ Use secrets management (not .env files)
   - ✓ Implement network segmentation
   - ✓ Enable audit logging

2. **Performance**
   - ✓ Configure connection pooling
   - ✓ Set appropriate pool sizes
   - ✓ Monitor query performance
   - ✓ Create appropriate indexes
   - ✓ Regular VACUUM and ANALYZE

3. **Reliability**
   - ✓ Set up database replication
   - ✓ Configure automatic backups
   - ✓ Test disaster recovery procedures
   - ✓ Monitor disk space
   - ✓ Set up alerting

4. **Migrations**
   - ✓ Use Alembic for schema changes
   - ✓ Test migrations in staging
   - ✓ Have rollback procedures
   - ✓ Version control all migrations
   - ✓ Document changes

## Useful Commands

```bash
# Connect to PostgreSQL container
docker-compose exec postgres psql -U postgres

# Connect to specific database
docker-compose exec postgres psql -U postgres -d auth_service

# List all databases
docker-compose exec postgres psql -U postgres -c "\l"

# Show database size
docker-compose exec postgres psql -U postgres -c "
SELECT 
    datname, 
    pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
WHERE datname LIKE '%service';
"

# Check active connections
docker-compose exec postgres psql -U postgres -c "
SELECT 
    datname, 
    count(*) as connections
FROM pg_stat_activity
GROUP BY datname;
"
```

## Getting Help

- **Auth Service:** `services/auth-service/scripts/README.md`
- **Quick Start:** `services/auth-service/scripts/QUICKSTART.md`
- **Docker Compose:** `docker-compose.yml`
- **Environment Config:** `config/environments/.env.example`

## Next Steps

1. ✅ Initialize databases (auth-service complete!)
2. ⬜ Initialize other service databases
3. ⬜ Configure admin service connection
4. ⬜ Set up Redis caching
5. ⬜ Configure Kafka event streaming
6. ⬜ Deploy to staging environment
7. ⬜ Set up monitoring and alerting

---

**Created:** 2024
**Updated:** Regular maintenance required
**Contact:** Development Team
