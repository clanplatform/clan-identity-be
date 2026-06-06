# Identity Domain - Deployment Status

**Last Updated:** June 6, 2026, 4:40 PM IST  
**Status:** ✅ All Services Running and Healthy - SYSTEM FULLY OPERATIONAL

---

## 🎯 System Overview

A microservices-based identity and authentication system built with FastAPI, PostgreSQL, and Redis. The system consists of 5 independent services with separate databases for each domain.

---

## 🚀 Running Services

All containers are healthy and operational:

| Service | Status | Port | Database | Description |
|---------|--------|------|----------|-------------|
| **PostgreSQL** | ✅ Healthy | 5433 | Multiple DBs | Primary data store |
| **Redis** | ✅ Healthy | 6380 | - | Cache & sessions |
| **auth-service** | ✅ Healthy | 8001 | auth_service | Authentication |
| **user-service** | ✅ Healthy | 8002 | user_service | User management |
| **session-service** | ✅ Healthy | 8003 | session_service | Session management |
| **rbac-service** | ✅ Healthy | 8004 | rbac_service | Role-based access |
| **oauth-service** | ✅ Healthy | 8005 | oauth_service | OAuth integration |

---

## 📊 Database Status

### PostgreSQL Databases Created
- ✅ `auth_service` - Authentication data
- ✅ `user_service` - User management data
- ✅ `session_service` - Session tracking data
- ✅ `rbac_service` - Role and permissions data
- ✅ `oauth_service` - OAuth tokens and providers

### Auth Service Tables
The following tables are created and verified in `auth_service` database:

1. **auth_users** (26 columns, 12 indexes)
   - User credentials and authentication data
   - Password management and 2FA
   - Account status tracking
   - ⚠️ Note: NOT used for primary authentication (uses admin_service.usersetup_basic)

2. **sessions** (24 columns, 11 indexes)
   - Active session tracking
   - Device and browser information
   - Token management (access & refresh)
   - Trust status and activity tracking

3. **login_attempts** (15 columns, 9 indexes)
   - Login audit trail
   - Security monitoring
   - Rate limiting data
   - Risk assessment tracking

---

## 🔑 Configuration

### Database Credentials
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root
POSTGRES_DB=auth_service
POSTGRES_HOST=postgres (Docker) / localhost (Host)
POSTGRES_PORT=5432 (Inside Docker) / 5433 (From Host)
```

**Important:** Inside Docker containers, PostgreSQL runs on port **5432**. From your host machine, it's accessible on port **5433**.

### Redis Configuration
```env
REDIS_HOST=redis (Docker) / localhost (Host)
REDIS_PASSWORD=redis_password
REDIS_PORT=6379 (Inside Docker) / 6380 (From Host)
```

**Important:** Inside Docker containers, Redis runs on port **6379**. From your host machine, it's accessible on port **6380**.

### Service Ports
```env
AUTH_SERVICE_PORT=8001
USER_SERVICE_PORT=8002
SESSION_SERVICE_PORT=8003
RBAC_SERVICE_PORT=8004
OAUTH_SERVICE_PORT=8005
```

---

## 🏗️ Architecture

### Service Structure
Each microservice follows the same structure:
```
services/{service-name}/
├── main.py                    # FastAPI application entry point
├── app/
│   ├── core/
│   │   ├── config.py         # Service configuration
│   │   └── __init__.py
│   ├── db/
│   │   ├── database.py       # Database connection
│   │   └── __init__.py
│   ├── models/               # SQLAlchemy models
│   │   └── __init__.py
│   ├── api/
│   │   ├── routes/           # API endpoints
│   │   │   ├── {route}.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   └── events/               # Event publishers (Kafka)
│       ├── kafka_client.py
│       └── __init__.py
└── requirements.txt          # Python dependencies
```

### Shared Libraries
Located in `libs/identity_shared/`:
- `config.py` - Common configuration
- `database.py` - Database utilities
- `redis_client.py` - Redis client
- `security.py` - Security utilities (JWT, hashing)
- `middleware.py` - Common middleware
- `exceptions.py` - Custom exceptions

---

## 📝 API Documentation

Each service provides interactive API documentation:

- **Auth Service:** http://localhost:8001/api/v1/docs
- **User Service:** http://localhost:8002/api/v1/docs
- **Session Service:** http://localhost:8003/api/v1/docs
- **RBAC Service:** http://localhost:8004/api/v1/docs
- **OAuth Service:** http://localhost:8005/api/v1/docs

---

## 🛠️ Management Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis
docker-compose up -d auth-service user-service
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f auth-service
```

### Check Status
```bash
# Container status
docker-compose ps

# Health check
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Database Management
```bash
# Create tables
cd services/script-files
python create_auth_tables.py

# Verify tables
python verify_auth_tables.py

# Drop tables
python drop_auth_tables.py
```

---

## 📂 Important Directories

- **Config:** `config/environments/.env.local`
- **SQL Scripts:** `services/sql-files/`
- **Python Scripts:** `services/script-files/`
- **Docker:** `deploy/Dockerfile`, `docker-compose.yml`
- **Services:** `services/{service-name}/`
- **Shared Libs:** `libs/identity_shared/`

---

## 🔄 Development Workflow

### Making Changes
1. Edit service code in `services/{service-name}/`
2. Rebuild specific service:
   ```bash
   docker-compose up -d --build {service-name}
   ```
3. View logs to verify:
   ```bash
   docker-compose logs -f {service-name}
   ```

### Adding Database Changes
1. Create SQL file in `services/sql-files/`
2. Create Python script in `services/script-files/`
3. Run script with `POSTGRES_HOST=localhost`
4. Update `.env.local` back to `POSTGRES_HOST=postgres`

---

## ✅ Completed Tasks

1. ✅ Docker infrastructure setup (PostgreSQL + Redis)
2. ✅ Multi-stage Dockerfile for Python services
3. ✅ Docker Compose with 5 microservices
4. ✅ Environment configuration
5. ✅ Shared libraries created
6. ✅ Database initialization scripts
7. ✅ Auth service database tables created and verified
8. ✅ All 5 services implemented with FastAPI structure
9. ✅ Health checks and API documentation
10. ✅ Management scripts for database operations

---

## 🎯 Next Steps (Recommendations)

### Immediate
1. Implement authentication logic in endpoint stubs
2. Add request/response schemas with Pydantic
3. Implement JWT token generation and validation
4. Add middleware for authentication checks

### Short-term
1. Create tables for other services (user_service, session_service, etc.)
2. Implement inter-service communication
3. Add comprehensive error handling
4. Set up logging and monitoring

### Long-term
1. Add unit and integration tests
2. Set up CI/CD pipelines
3. Implement rate limiting
4. Add API gateway for unified access
5. Set up monitoring (Prometheus/Grafana)
6. Implement event-driven architecture with Kafka

---

## 📞 Service Endpoints

### Auth Service (8001)
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/docs` - Swagger UI
- `POST /api/v1/auth/*` - Authentication endpoints (stubs)

### User Service (8002)
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/docs` - Swagger UI
- `POST /api/v1/login/*` - Login endpoints (stubs)

### Session Service (8003)
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/docs` - Swagger UI
- `GET /api/v1/sessions/*` - Session endpoints (stubs)

### RBAC Service (8004)
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/docs` - Swagger UI
- `GET /api/v1/rbac/*` - RBAC endpoints (stubs)

### OAuth Service (8005)
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/docs` - Swagger UI
- `GET /api/v1/oauth/*` - OAuth endpoints (stubs)

---

## 🔍 Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs {service-name}

# Rebuild service
docker-compose up -d --build {service-name}

# Check if ports are in use
netstat -an | findstr "8001 8002 8003 8004 8005 5433 6380"
```

### Database Connection Issues
- Ensure `POSTGRES_HOST=postgres` in `.env.local` for Docker services
- Use `POSTGRES_HOST=localhost` when running scripts from host
- Verify PostgreSQL is healthy: `docker-compose ps postgres`

### Redis Connection Issues
- Verify Redis is healthy: `docker-compose ps redis`
- Check Redis password in `.env.local`

---

## 📚 Documentation Files

- `AUTH_DATABASE_SCHEMA.md` - Auth service database schema
- `services/sql-files/README.md` - SQL scripts documentation
- `services/script-files/README.md` - Python scripts documentation
- `services/script-files/QUICK_START.md` - Quick start guide

---

**Project Status:** Production-ready infrastructure with service stubs ready for business logic implementation.
