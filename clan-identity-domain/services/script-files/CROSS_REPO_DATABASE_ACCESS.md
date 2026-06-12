# Cross-Repository Database Access Configuration

## Overview
This document explains how to configure `clan-identity-domain-be` to access the `admin_service` database from the `clan-platform-domain-be` repository.

## Architecture

```
┌─────────────────────────────────────┐
│  clan-platform-domain-be (Repo 1)  │
│  ┌──────────────────────────────┐  │
│  │   admin-service              │  │
│  │   PostgreSQL:5432            │  │
│  │   Database: admin_service    │  │
│  │   Table: usersetup_basic     │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
              ↑ (cross-repo access)
              │
┌─────────────────────────────────────┐
│  clan-identity-domain-be (Repo 2)  │
│  ┌──────────────────────────────┐  │
│  │   auth-service               │  │
│  │   - Local DB: auth_service   │  │
│  │   - Remote: admin_service    │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Configuration Options

### Option 1: Access via Host Machine (Recommended for Development)

**When to use:** When both repositories are running on the same machine.

#### Step 1: Update `.env.local`

```bash
# Admin Service Database (External Repository: clan-platform-domain-be)
ADMIN_POSTGRES_HOST=host.docker.internal
ADMIN_POSTGRES_PORT=5432
ADMIN_POSTGRES_USER=postgres
ADMIN_POSTGRES_PASSWORD=root
ADMIN_DB=admin_service
```

#### Step 2: Ensure admin-service PostgreSQL is accessible
Check that the admin-service PostgreSQL is exposed on host port 5432:

```bash
cd ../clan-platform-domain-be
docker-compose ps | grep postgres
# Should show: 0.0.0.0:5432->5432/tcp
```

If not exposed, update `clan-platform-domain-be/docker-compose.yml`:
```yaml
services:
  postgres:
    ports:
      - "5432:5432"  # Expose to host
```

#### Step 3: Restart auth-service
```bash
docker-compose restart auth-service
```

### Option 2: Access via Docker Network Bridge

**When to use:** When you want both repositories to share a Docker network.

#### Step 1: Create shared Docker network
```bash
docker network create clan-shared-network
```

#### Step 2: Update `clan-platform-domain-be/docker-compose.yml`
```yaml
services:
  postgres:
    networks:
      - default
      - clan-shared-network

networks:
  clan-shared-network:
    external: true
```

#### Step 3: Update `clan-identity-domain-be/docker-compose.yml`
```yaml
services:
  auth-service:
    networks:
      - clan-identity-network
      - clan-shared-network

networks:
  clan-shared-network:
    external: true
```

#### Step 4: Update `.env.local`
```bash
# Use container name from clan-platform-domain-be
ADMIN_POSTGRES_HOST=admin-service-postgres
ADMIN_POSTGRES_PORT=5432
```

### Option 3: Access via Direct IP Address

**When to use:** When services are on different machines or in production.

#### Step 1: Get admin-service PostgreSQL IP
```bash
# If on same network
docker inspect admin-service-postgres | grep IPAddress

# If on different machine
# Use the actual server IP
```

#### Step 2: Update `.env.local`
```bash
ADMIN_POSTGRES_HOST=192.168.1.100  # Replace with actual IP
ADMIN_POSTGRES_PORT=5432
ADMIN_POSTGRES_USER=postgres
ADMIN_POSTGRES_PASSWORD=root
ADMIN_DB=admin_service
```

#### Step 3: Ensure PostgreSQL allows remote connections
In `clan-platform-domain-be`, update `postgresql.conf`:
```
listen_addresses = '*'
```

And `pg_hba.conf`:
```
host    all             all             0.0.0.0/0               md5
```

## Testing the Connection

### 1. Test from host machine
```bash
# Test connection to admin_service database
docker exec -it clan-auth-service psql -h host.docker.internal -U postgres -d admin_service -c "SELECT COUNT(*) FROM usersetup_basic;"
```

### 2. Check health endpoint
```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "auth_database": "healthy",
  "admin_database": "healthy",
  "kafka": "disabled",
  "service": "Auth Service"
}
```

### 3. Test login endpoint
```bash
curl -X POST http://localhost:8001/api/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "yourpassword"
  }'
```

## Troubleshooting

### Error: "Connection refused"
**Cause:** PostgreSQL is not accessible from Docker container.

**Solution:**
1. Verify admin-service PostgreSQL is running:
   ```bash
   cd ../clan-platform-domain-be
   docker-compose ps | grep postgres
   ```

2. Check if port 5432 is exposed:
   ```bash
   netstat -an | grep 5432
   ```

3. Ensure `extra_hosts` is set in docker-compose.yml:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

### Error: "Database does not exist"
**Cause:** `admin_service` database doesn't exist.

**Solution:**
```bash
cd ../clan-platform-domain-be
docker exec -it admin-service-postgres psql -U postgres -c "CREATE DATABASE admin_service;"
```

### Error: "Relation usersetup_basic does not exist"
**Cause:** The `usersetup_basic` table hasn't been created yet.

**Solution:** The table should exist in the admin-service. Check:
```bash
cd ../clan-platform-domain-be
docker exec -it admin-service-postgres psql -U postgres -d admin_service -c "\dt"
```

### Error: "Authentication failed"
**Cause:** Wrong PostgreSQL credentials.

**Solution:** Check credentials in both repositories match:
```bash
# clan-platform-domain-be
cat .env | grep POSTGRES

# clan-identity-domain-be
cat config/environments/.env.local | grep ADMIN_POSTGRES
```

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ADMIN_POSTGRES_HOST` | Admin service PostgreSQL host | `host.docker.internal` | `192.168.1.100` |
| `ADMIN_POSTGRES_PORT` | Admin service PostgreSQL port | `5432` | `5433` |
| `ADMIN_POSTGRES_USER` | Admin service PostgreSQL user | `postgres` | `admin_user` |
| `ADMIN_POSTGRES_PASSWORD` | Admin service PostgreSQL password | `root` | `secure_pass` |
| `ADMIN_DB` | Admin service database name | `admin_service` | `admin_service` |

## Security Best Practices

### Development
- ✅ Use `host.docker.internal` for local development
- ✅ Keep default credentials simple
- ✅ Don't expose PostgreSQL to public internet

### Production
- 🔒 Use private network or VPN
- 🔒 Use strong passwords and secrets management
- 🔒 Enable SSL/TLS for PostgreSQL connections
- 🔒 Restrict IP access with firewall rules
- 🔒 Use connection pooling (PgBouncer)
- 🔒 Enable PostgreSQL authentication logs

## Production Configuration Example

```yaml
# .env.production
ADMIN_POSTGRES_HOST=admin-db.internal.company.com
ADMIN_POSTGRES_PORT=5432
ADMIN_POSTGRES_USER=${VAULT_ADMIN_DB_USER}
ADMIN_POSTGRES_PASSWORD=${VAULT_ADMIN_DB_PASS}
ADMIN_DB=admin_service
ADMIN_POSTGRES_SSL_MODE=require
```

## Additional Resources

- [PostgreSQL Network Configuration](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Docker Networking](https://docs.docker.com/network/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
