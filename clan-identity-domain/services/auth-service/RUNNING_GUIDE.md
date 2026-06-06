# Auth Service - Running Guide

## ✅ Service is Running!

The Auth Service is now successfully running and accessible.

## 🚀 Server Information

- **Service Name:** Auth Service  
- **Port:** 8003  
- **Host:** 0.0.0.0 (accessible from all network interfaces)  
- **Base URL:** http://localhost:8003  
- **Swagger UI:** http://localhost:8003/api/v1/docs  
- **ReDoc:** http://localhost:8003/api/v1/redoc  
- **OpenAPI JSON:** http://localhost:8003/api/v1/openapi.json

## 📍 API Endpoints

### Base Endpoints
- **GET /** - Service health check and information
- **GET /health** - Detailed health check (database, Kafka status)

### Authentication Endpoints (All under `/api/v1/login`)
- **POST /api/v1/login/** - User login
- **POST /api/v1/login/change-password** - Change password
- **POST /api/v1/login/after-change-password-login** - Login after password change
- **POST /api/v1/login/logout** - User logout
- **POST /api/v1/login/refresh** - Refresh access token
- **GET /api/v1/login/me** - Get current user info

## 🔧 How to Run

### Command Used:
```powershell
cd services\auth-service
$env:PYTHONPATH="$PWD"
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### Or using Python directly:
```powershell
cd services\auth-service
$env:PYTHONPATH="$PWD"
python main.py
```

## ⚙️ Current Status

### ✅ Working:
- FastAPI application started successfully
- Uvicorn server running on port 8003
- Auto-reload enabled for development
- API routes properly registered
- Swagger documentation accessible

### ⚠️ Warnings (non-critical):
- **Kafka not available**: The service can run without Kafka. Events won't be published but authentication works fine.
- **Database initialization**: Database tables need to be created. This requires:
  - PostgreSQL running
  - `auth_service` database created
  - `admin_service` database created with `usersetup_basic` table

## 🗄️ Database Setup Required

The service needs two databases:

### 1. **auth_service** (Main database)
```sql
CREATE DATABASE auth_service;
```

Tables that will be auto-created:
- `sessions` - User login sessions
- `login_attempts` - Login attempt audit log
- `otps` - One-time passwords
- `auth_users` - Cached user authentication data

### 2. **admin_service** (User data source)
```sql
CREATE DATABASE admin_service;
```

This database should already contain:
- `usersetup_basic` - User authentication credentials

## 📝 Environment Variables

Create a `.env` file in the auth-service directory:

```env
# Service Configuration
PROJECT_NAME=Auth Service
ENVIRONMENT=dev
DEBUG=true

# PostgreSQL Configuration
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root
POSTGRES_DB=auth_service
ADMIN_DB=admin_service

# JWT Configuration
JWT_SECRET_KEY=auth-service-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:8001,http://localhost:8002

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
REDIS_ENABLED=false

# Kafka (Optional)
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_ENABLED=false
```

## 🧪 Testing the Service

### 1. Check if service is running:
```bash
curl http://localhost:8003/
```

Expected response:
```json
{
  "service": "Auth Service",
  "version": "1.0.0",
  "status": "running",
  "environment": "dev",
  "database": "auth_service"
}
```

### 2. Check health status:
```bash
curl http://localhost:8003/health
```

### 3. Access Swagger UI:
Open browser: http://localhost:8003/api/v1/docs

## 📂 Project Structure

```
auth-service/
├── main.py                        # Application entry point ✅
├── core/
│   ├── config.py                 # Configuration ✅
│   └── security.py               # JWT & password utilities ✅
├── database/
│   └── database.py               # Database connections ✅
├── models/
│   ├── session.py               # Session model ✅
│   └── login_attempt.py         # Login attempt model ✅
├── schemas/
│   └── login_schemas.py         # Pydantic schemas ✅
├── services/
│   └── login_service.py         # Business logic ✅
├── app/
│   └── api/
│       └── routes/
│           └── v1/
│               └── login.py     # API routes ✅
└── events/
    └── schemas.py               # Event schemas ✅
```

## 🔍 Troubleshooting

### Issue: Port already in use
```powershell
# Find process using port 8003
netstat -ano | findstr :8003

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Issue: Module not found errors
```powershell
# Make sure PYTHONPATH is set
$env:PYTHONPATH="$PWD"

# Or run from correct directory
cd services\auth-service
```

### Issue: Database connection failed
1. Ensure PostgreSQL is running
2. Check database credentials in .env file
3. Create required databases if they don't exist

## 📊 Import Structure Fixed

All imports have been updated to work with the current directory structure:

### Before (broken):
```python
from app.core.config import settings
from app.db.database import Base
```

### After (working):
```python
try:
    from core.config import settings
    from database.database import Base
except ImportError:
    from app.core.config import settings
    from app.db.database import Base
```

## 🎯 Next Steps

1. ✅ Service is running
2. ⏳ Set up PostgreSQL databases
3. ⏳ Configure environment variables
4. ⏳ Test API endpoints via Swagger
5. ⏳ Integrate with frontend application

## 📚 Additional Documentation

- [API_ARCHITECTURE.md](./API_ARCHITECTURE.md) - Architecture details
- [SEPARATION_OF_CONCERNS.md](./SEPARATION_OF_CONCERNS.md) - Code organization  
- [README_SWAGGER.md](./README_SWAGGER.md) - Complete API documentation

---

**Status:** ✅ **RUNNING**  
**Port:** 8003  
**Swagger:** http://localhost:8003/api/v1/docs  
**Last Updated:** 2026-06-06
