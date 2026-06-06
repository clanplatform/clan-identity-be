# Docker Run Guide

## Quick Start with Docker

### Prerequisites
- Docker Desktop installed and running
- Docker Compose available

### Configuration

The environment configuration is located at:
```
config/environments/.env.local
```

**Important:** All services use Docker hostnames (`postgres`, `redis`) for inter-container communication.

### Step 1: Start Infrastructure

Start PostgreSQL and Redis first:

```bash
docker-compose up -d postgres redis
```

Wait for services to be healthy (check with `docker-compose ps`):

```bash
docker-compose ps
```

Expected output:
```
NAME                        STATUS              PORTS
clan-identity-postgres      Up (healthy)        0.0.0.0:5432->5432/tcp
clan-identity-redis         Up (healthy)        0.0.0.0:6379->6379/tcp
```

### Step 2: Create Database Tables

#### Option A: From Host Machine

Update POSTGRES_HOST in `.env.local` temporarily:
```bash
# Change POSTGRES_HOST=postgres to:
POSTGRES_HOST=localhost
```

Run the script:
```bash
cd services/script-files
python create_auth_tables.py
```

Then change it back:
```bash
# Change back to:
POSTGRES_HOST=postgres
```

#### Option B: Inside Container

```bash
# Copy scripts to container
docker cp services/script-files clan-identity-postgres:/tmp/

# Execute SQL files directly
docker exec -it clan-identity-postgres psql -U clan_user -d auth_db -f /tmp/script-files/../sql-files/00_init_auth_database.sql
docker exec -it clan-identity-postgres psql -U clan_user -d auth_db -f /tmp/script-files/../sql-files/01_create_auth_users_table.sql
docker exec -it clan-identity-postgres psql -U clan_user -d auth_db -f /tmp/script-files/../sql-files/02_create_login_attempts_table.sql
docker exec -it clan-identity-postgres psql -U clan_user -d auth_db -f /tmp/script-files/../sql-files/03_create_sessions_table.sql
```

#### Option C: Using psql from host

```bash
psql -h localhost -p 5432 -U clan_user -d auth_db -f services/sql-files/00_init_auth_database.sql
psql -h localhost -p 5432 -U clan_user -d auth_db -f services/sql-files/01_create_auth_users_table.sql
psql -h localhost -p 5432 -U clan_user -d auth_db -f services/sql-files/02_create_login_attempts_table.sql
psql -h localhost -p 5432 -U clan_user -d auth_db -f services/sql-files/03_create_sessions_table.sql
```

### Step 3: Start All Services

```bash
docker-compose up -d
```

Or start services individually:

```bash
docker-compose up -d auth-service
docker-compose up -d user-service
docker-compose up -d session-service
docker-compose up -d rbac-service
docker-compose up -d oauth-service
```

### Step 4: Verify Services

Check all containers are running:

```bash
docker-compose ps
```

Expected output:
```
NAME                        STATUS              PORTS
clan-auth-service           Up                  0.0.0.0:8001->8000/tcp
clan-user-service           Up                  0.0.0.0:8002->8000/tcp
clan-session-service        Up                  0.0.0.0:8003->8000/tcp
clan-rbac-service           Up                  0.0.0.0:8004->8000/tcp
clan-oauth-service          Up                  0.0.0.0:8005->8000/tcp
clan-identity-postgres      Up (healthy)        0.0.0.0:5432->5432/tcp
clan-identity-redis         Up (healthy)        0.0.0.0:6379->6379/tcp
```

### Step 5: Test Services

Check service health:

```bash
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # User Service
curl http://localhost:8003/health  # Session Service
curl http://localhost:8004/health  # RBAC Service
curl http://localhost:8005/health  # OAuth Service
```

Access API documentation:
- Auth Service: http://localhost:8001/docs
- User Service: http://localhost:8002/docs
- Session Service: http://localhost:8003/docs
- RBAC Service: http://localhost:8004/docs
- OAuth Service: http://localhost:8005/docs

## Useful Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f auth-service
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Access Database

```bash
# PostgreSQL shell
docker-compose exec postgres psql -U clan_user -d auth_db

# List databases
docker-compose exec postgres psql -U clan_user -c "\l"

# List tables in auth_db
docker-compose exec postgres psql -U clan_user -d auth_db -c "\dt"
```

### Access Redis

```bash
# Redis CLI
docker-compose exec redis redis-cli -a redis_password

# Check keys
docker-compose exec redis redis-cli -a redis_password KEYS '*'

# Check info
docker-compose exec redis redis-cli -a redis_password INFO
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart auth-service
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop and remove volumes (DESTRUCTIVE!)
docker-compose down -v
```

### Rebuild Services

```bash
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build auth-service

# Rebuild and start
docker-compose up -d --build
```

### Execute Commands in Container

```bash
# Open bash in service container
docker-compose exec auth-service /bin/bash

# Run Python script in container
docker-compose exec auth-service python -c "print('Hello')"

# Check Python packages
docker-compose exec auth-service pip list
```

## Troubleshooting

### Issue: Services fail to start

**Check logs:**
```bash
docker-compose logs auth-service
```

**Common causes:**
- Database not ready → Wait for postgres health check
- Port already in use → Change ports in .env.local
- Build failed → Check Dockerfile and requirements

### Issue: Cannot connect to database

**Verify PostgreSQL is running:**
```bash
docker-compose ps postgres
```

**Test connection:**
```bash
docker-compose exec postgres psql -U clan_user -d auth_db -c "SELECT 1"
```

**Check credentials match .env.local:**
```bash
docker-compose exec postgres env | grep POSTGRES
```

### Issue: Services can't connect to each other

**Check network:**
```bash
docker network ls | grep clan-identity
docker network inspect clan-identity-network
```

**Verify all services are on the same network:**
```bash
docker-compose ps
```

### Issue: Changes not reflecting

**Rebuild containers:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Database data lost

**Check volumes:**
```bash
docker volume ls | grep clan-identity
```

**Backup database:**
```bash
docker-compose exec postgres pg_dump -U clan_user auth_db > backup.sql
```

**Restore database:**
```bash
docker-compose exec -T postgres psql -U clan_user auth_db < backup.sql
```

## Environment Variables

### Docker vs Local Development

**Docker (config/environments/.env.local):**
```bash
POSTGRES_HOST=postgres    # Container name
REDIS_HOST=redis          # Container name
```

**Local development (when running scripts from host):**
```bash
POSTGRES_HOST=localhost   # Localhost for host machine
REDIS_HOST=localhost      # Localhost for host machine
```

### Override Environment Variables

Create `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  auth-service:
    environment:
      DEBUG: "true"
      LOG_LEVEL: "DEBUG"
```

## Production Considerations

1. **Use production environment file:**
   ```yaml
   env_file:
     - ./config/environments/.env.prod
   ```

2. **Remove volume mounts** (code should be in image)

3. **Use external databases** (not Docker containers)

4. **Enable TLS/SSL** for database and Redis

5. **Use secrets management** (not .env files)

6. **Set resource limits:**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 512M
   ```

7. **Enable monitoring** (Prometheus, Grafana)

8. **Set up health checks** properly

9. **Use image registry** (not local builds)

10. **Implement proper logging** (ELK stack, etc.)

## Next Steps

1. Create sample data in database
2. Test authentication flow
3. Set up API gateway (optional)
4. Configure monitoring
5. Set up CI/CD pipeline
