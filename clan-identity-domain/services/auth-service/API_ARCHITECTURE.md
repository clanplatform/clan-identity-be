# User Service API Architecture

## Separation of Concerns

This document explains the clean separation between CRUD API routes and business logic in the User Service.

## Architecture Layers

### 1. Routes Layer (CRUD API)
**Location:** `app/api/routes/v1/login.py`

**Responsibility:** HTTP Request/Response Handling
- Accept HTTP requests
- Extract data from request (headers, body, client info)
- Inject dependencies (database sessions, current user)
- Delegate to service layer
- Return HTTP responses with proper status codes
- Define OpenAPI/Swagger documentation

**Does NOT contain:**
- Business logic
- Database queries
- Password validation
- Token generation
- Complex data transformation

**Example:**
```python
@router.post("/", response_model=LoginResponse, tags=["Authentication"])
def login(
    request: Request,
    login_data: LoginRequest,
    auth_db: Session = Depends(get_db),
    admin_db: Session = Depends(get_admin_db)
):
    """Login endpoint - Authenticate user with email and password"""
    # Extract request context
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Delegate to service
    return LoginService.login(
        auth_db=auth_db,
        admin_db=admin_db,
        login_data=login_data,
        client_ip=client_ip,
        user_agent=user_agent
    )
```

### 2. Service Layer (Business Logic)
**Location:** `services/login_service.py`

**Responsibility:** Business Logic & Data Operations
- User authentication logic
- Password verification and hashing
- Token generation (access & refresh)
- Session management
- Login attempt tracking
- Password change validation
- Database queries
- Error handling with business rules

**Does NOT contain:**
- HTTP-specific logic (status codes, headers)
- Request/Response models
- FastAPI dependencies
- Routing information

**Example:**
```python
class LoginService:
    @staticmethod
    def login(auth_db: Session, admin_db: Session, login_data: LoginRequest,
              client_ip: str = None, user_agent: str = None) -> LoginResponse:
        """Login user and generate tokens"""
        # 1. Authenticate user
        user = LoginService.authenticate_user(admin_db, login_data.email, login_data.password)
        
        # 2. Check account status
        if user["status"] != "active":
            raise HTTPException(...)
        
        # 3. Check password change requirement
        if user["is_password_change_required"]:
            return {...}  # Password change response
        
        # 4. Generate tokens
        access_token = create_access_token(...)
        refresh_token = create_refresh_token(...)
        
        # 5. Create session
        session = LoginService._create_session(...)
        
        # 6. Log attempt
        LoginService._log_login_attempt(...)
        
        # 7. Return response
        return LoginResponse(...)
```

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description | Service Method |
|----------|--------|-------------|----------------|
| `/api/v1/login/` | POST | User login | `LoginService.login()` |
| `/api/v1/login/change-password` | POST | Change password | `LoginService.change_password()` |
| `/api/v1/login/after-change-password-login` | POST | Login after password change | `LoginService.login()` |
| `/api/v1/login/logout` | POST | User logout | `LoginService.logout_user()` |
| `/api/v1/login/refresh` | POST | Refresh access token | `LoginService.refresh_access_token()` |
| `/api/v1/login/me` | GET | Get current user info | `LoginService.get_current_user_info()` |

## Data Flow

```
Client Request
    ↓
FastAPI Route Handler (app/api/routes/v1/login.py)
    ↓ [Extract request data, inject dependencies]
Service Layer (services/login_service.py)
    ↓ [Business logic, validation]
Database Layer (admin_service / user_service)
    ↓ [Execute queries]
Service Layer
    ↓ [Process results, generate tokens]
Route Handler
    ↓ [Return HTTP response]
Client Response
```

## Benefits of This Architecture

### 1. **Testability**
- Service logic can be tested independently without HTTP layer
- Mock database sessions easily
- Unit test business rules without FastAPI

### 2. **Reusability**
- Service methods can be called from:
  - API routes
  - Background tasks
  - CLI commands
  - Other services

### 3. **Maintainability**
- Clear separation of concerns
- Easy to locate bugs (HTTP vs business logic)
- Changes to business logic don't affect API structure

### 4. **Scalability**
- Service layer can be extracted to microservices
- Routes remain thin and focused
- Easy to add new endpoints using existing services

## Running the Service

### Start the server:
```bash
cd services/user-service
python main.py
```

### Access Swagger Documentation:
```
http://localhost:8002/api/v1/docs
```

### Access ReDoc:
```
http://localhost:8002/api/v1/redoc
```

## Dependencies

### Routes Layer Dependencies:
- `fastapi`: API framework
- `pydantic`: Request/response validation
- `sqlalchemy`: Database session management (via Depends)

### Service Layer Dependencies:
- `sqlalchemy`: Database operations
- `core.security`: Password hashing, token generation
- `core.config`: Configuration settings
- `models`: Database models
- `schemas`: Data validation schemas

## File Structure

```
user-service/
├── app/
│   └── api/
│       └── routes/
│           └── v1/
│               └── login.py          # CRUD API Routes (HTTP Layer)
├── services/
│   └── login_service.py              # Business Logic Layer
├── schemas/
│   └── login_schemas.py              # Pydantic Models
├── models/
│   ├── session.py                    # Session Model
│   └── login_attempt.py              # Login Attempt Model
├── core/
│   ├── config.py                     # Configuration
│   └── security.py                   # Security Utilities
├── database/
│   └── connection.py                 # Database Connection
└── main.py                           # Application Entry Point
```

## Best Practices

### Routes (CRUD Layer):
1. ✅ Keep route handlers thin
2. ✅ Only handle HTTP concerns
3. ✅ Inject dependencies via `Depends()`
4. ✅ Add comprehensive API documentation
5. ✅ Define response models
6. ❌ Don't write SQL queries
7. ❌ Don't implement business logic
8. ❌ Don't directly manipulate data

### Services (Business Logic Layer):
1. ✅ Implement all business rules
2. ✅ Handle data validation
3. ✅ Execute database operations
4. ✅ Raise appropriate exceptions
5. ✅ Log important events
6. ❌ Don't import FastAPI-specific decorators
7. ❌ Don't return HTTP status codes directly
8. ❌ Don't handle request/response objects

## Example: Adding a New Endpoint

### Step 1: Add Schema (schemas/login_schemas.py)
```python
class ForgotPasswordRequest(BaseModel):
    email: EmailStr
```

### Step 2: Add Service Method (services/login_service.py)
```python
@staticmethod
def initiate_password_reset(admin_db: Session, email: str):
    user = LoginService.get_user_from_admin_db(admin_db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Generate reset token, send email, etc.
    return {"message": "Reset email sent"}
```

### Step 3: Add Route (app/api/routes/v1/login.py)
```python
@router.post("/forgot-password", tags=["Authentication"])
def forgot_password(
    request_data: ForgotPasswordRequest,
    admin_db: Session = Depends(get_admin_db)
):
    return LoginService.initiate_password_reset(admin_db, request_data.email)
```

---

**Last Updated:** 2026-06-06
**Author:** Development Team
**Version:** 1.0.0
