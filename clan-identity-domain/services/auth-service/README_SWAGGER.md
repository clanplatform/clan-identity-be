# User Service - Swagger API Documentation

## 🎯 Overview

The User Service provides authentication and user management APIs with complete Swagger/OpenAPI documentation.

## 🚀 Quick Start

### 1. Start the Service

```bash
cd services/user-service
python main.py
```

The service will start on: **http://localhost:8002**

### 2. Access Swagger UI

Open your browser and navigate to:

**Swagger UI:** http://localhost:8002/api/v1/docs

**ReDoc:** http://localhost:8002/api/v1/redoc

**OpenAPI JSON:** http://localhost:8002/api/v1/openapi.json

---

## 📚 API Documentation

### Authentication Endpoints

#### 1. **POST /api/v1/login/**
User login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "your_password",
  "remember_me": false,
  "device_fingerprint": "optional_device_id"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "is_password_change": true,
  "expires_in": 3600,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "johndoe",
    "firstname": "John",
    "lastname": "Doe",
    "employee_id": "EMP001",
    "status": "active",
    "roles": []
  }
}
```

**Password Change Required Response:**
```json
{
  "is_password_change": false,
  "message": "First Time Login Detected - Please change your password",
  "email": "user@example.com",
  "show_popup": true,
  "error_code": "FIRST_LOGIN_PASSWORD_CHANGE_REQUIRED",
  "error_type": "validation_error"
}
```

---

#### 2. **POST /api/v1/login/change-password**
Change user password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "current_password": "old_password",
  "new_password": "new_secure_password",
  "confirm_password": "new_secure_password"
}
```

**Success Response (200):**
```json
{
  "message": "The password is successfully changed. You will logout in 2 sec",
  "email": "user@example.com",
  "show_popup": true,
  "logout_in_seconds": 2
}
```

---

#### 3. **POST /api/v1/login/after-change-password-login**
Login after password change.

**Request Body:** Same as login endpoint

**Response:** Same as login endpoint (with tokens)

---

#### 4. **POST /api/v1/login/logout**
Logout user and invalidate session.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body (Optional):**
```json
{
  "refresh_token": "optional_refresh_token",
  "all_sessions": false
}
```

**Success Response (200):**
```json
{
  "message": "Logged out successfully",
  "sessions_revoked": 1
}
```

---

#### 5. **POST /api/v1/login/refresh**
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

#### 6. **GET /api/v1/login/me**
Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "employee_id": "EMP001",
  "status": "active"
}
```

---

## 🔐 Authentication Flow

### First Time Login (Password Change Required)

```
1. User POST /api/v1/login/
   ↓
2. Response: is_password_change = false
   {
     "message": "First Time Login - Please change password",
     "is_password_change": false,
     ...
   }
   ↓
3. User POST /api/v1/login/change-password
   {
     "email": "...",
     "current_password": "...",
     "new_password": "..."
   }
   ↓
4. Response: Success with logout timer
   {
     "message": "Password changed successfully",
     "logout_in_seconds": 2
   }
   ↓
5. Wait 2 seconds, then POST /api/v1/login/after-change-password-login
   ↓
6. Response: Full login with tokens
   {
     "access_token": "...",
     "refresh_token": "...",
     "is_password_change": true,
     ...
   }
```

### Regular Login Flow

```
1. User POST /api/v1/login/
   ↓
2. Response: Tokens and user info
   {
     "access_token": "...",
     "refresh_token": "...",
     "session_id": "...",
     "user": {...}
   }
   ↓
3. Use access_token for authenticated requests
   Authorization: Bearer <access_token>
   ↓
4. When access_token expires, POST /api/v1/login/refresh
   {
     "refresh_token": "..."
   }
   ↓
5. Receive new access_token
```

---

## 🏗️ Architecture

### Clean Separation of Concerns

```
┌─────────────────────────────────────────┐
│         HTTP Request (Client)           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│   Routes Layer (CRUD API)               │
│   app/api/routes/v1/login.py           │
│                                          │
│   • Extract request data                │
│   • Inject dependencies                 │
│   • Delegate to service                 │
│   • Return HTTP response                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│   Service Layer (Business Logic)        │
│   services/login_service.py            │
│                                          │
│   • Authenticate user                   │
│   • Validate business rules             │
│   • Generate tokens                     │
│   • Create sessions                     │
│   • Execute database queries            │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│   Database Layer                        │
│   • user_service DB (sessions, logs)    │
│   • admin_service DB (user data)        │
└─────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
user-service/
├── app/
│   └── api/
│       └── routes/
│           └── v1/
│               └── login.py          # CRUD API Routes (HTTP layer)
├── services/
│   └── login_service.py              # Business Logic
├── schemas/
│   └── login_schemas.py              # Pydantic models
├── models/
│   ├── session.py                    # Session model
│   └── login_attempt.py              # Login attempt model
├── core/
│   ├── config.py                     # Configuration
│   └── security.py                   # JWT, hashing utilities
├── database/
│   └── connection.py                 # Database connections
├── main.py                           # FastAPI application
└── README_SWAGGER.md                 # This file
```

---

## 🧪 Testing with Swagger UI

### Step 1: Open Swagger UI
Navigate to: http://localhost:8002/api/v1/docs

### Step 2: Test Login
1. Expand **POST /api/v1/login/**
2. Click **"Try it out"**
3. Enter request body:
```json
{
  "email": "test@example.com",
  "password": "password123"
}
```
4. Click **"Execute"**
5. View response

### Step 3: Authorize (for protected endpoints)
1. Copy the `access_token` from login response
2. Click **"Authorize"** button at top right
3. Enter: `Bearer <your_access_token>`
4. Click **"Authorize"**
5. Now you can test protected endpoints like `/me`

### Step 4: Test Protected Endpoint
1. Expand **GET /api/v1/login/me**
2. Click **"Try it out"**
3. Click **"Execute"**
4. View your user information

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the user-service directory:

```env
# Service Configuration
PROJECT_NAME=User Auth Service
ENVIRONMENT=development
DEBUG=true

# Database - user_service
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root
POSTGRES_DB=user_service
ADMIN_DB=admin_service

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8001
```

---

## 📊 Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid credentials) |
| 403 | Forbidden (account inactive/locked) |
| 404 | Not Found (user not found) |
| 500 | Internal Server Error |

---

## 🎨 Swagger Tags

All endpoints are organized with tags:

- **Authentication**: Login, logout, password change, refresh token
- **User Info**: Get current user information

---

## 📝 Code Examples

### Python (requests)

```python
import requests

# Login
response = requests.post(
    "http://localhost:8002/api/v1/login/",
    json={
        "email": "user@example.com",
        "password": "password123"
    }
)
data = response.json()
access_token = data["access_token"]

# Get current user
response = requests.get(
    "http://localhost:8002/api/v1/login/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
user = response.json()
print(user)
```

### JavaScript (fetch)

```javascript
// Login
const loginResponse = await fetch('http://localhost:8002/api/v1/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});
const { access_token } = await loginResponse.json();

// Get current user
const userResponse = await fetch('http://localhost:8002/api/v1/login/me', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const user = await userResponse.json();
console.log(user);
```

### cURL

```bash
# Login
curl -X POST "http://localhost:8002/api/v1/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Get current user
curl -X GET "http://localhost:8002/api/v1/login/me" \
  -H "Authorization: Bearer <your_access_token>"
```

---

## ✅ Features

- ✅ Complete Swagger/OpenAPI documentation
- ✅ JWT-based authentication
- ✅ Access and refresh tokens
- ✅ Session management
- ✅ Login attempt tracking
- ✅ Password change flow
- ✅ First login password requirement
- ✅ Clean architecture (routes + services)
- ✅ Type validation with Pydantic
- ✅ CORS support
- ✅ Database connection pooling

---

## 🆘 Troubleshooting

### Cannot access Swagger UI
- Ensure service is running: `python main.py`
- Check the port is not in use: `netstat -an | findstr 8002`
- Verify URL: http://localhost:8002/api/v1/docs

### Authentication errors
- Check JWT_SECRET_KEY in .env file
- Verify token hasn't expired
- Ensure correct Authorization header format: `Bearer <token>`

### Database connection errors
- Verify PostgreSQL is running
- Check database credentials in .env
- Ensure both user_service and admin_service databases exist

---

## 📚 Additional Documentation

- [API_ARCHITECTURE.md](./API_ARCHITECTURE.md) - Detailed architecture explanation
- [SEPARATION_OF_CONCERNS.md](./SEPARATION_OF_CONCERNS.md) - Code organization guide

---

**Service:** User Service  
**Version:** 1.0.0  
**Last Updated:** 2026-06-06  
**Port:** 8002  
**Swagger UI:** http://localhost:8002/api/v1/docs
