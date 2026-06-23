"""
Login API Routes - CRUD Layer
Handles HTTP requests and responses for authentication endpoints
Business logic delegated to LoginService
"""
from fastapi import APIRouter, Depends, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Dict

_bearer = HTTPBearer(auto_error=False)

# Database dependencies
try:
    from database.database import get_db, get_admin_db
except ImportError:
    from database.connection import get_db, get_admin_db

# Schemas
from schemas.login_schemas import (
    LoginRequest, LoginResponse,
    ChangePasswordRequest, ChangePasswordResponse,
    ForgotPasswordRequest, ForgotPasswordResponse,
    OTPVerifyRequest, RefreshTokenRequest, RefreshTokenResponse,
    LogoutRequest, LogoutResponse
)

# Service layer
from services.login_service import LoginService

# Security utilities
from core.security import get_current_user_id

router = APIRouter()


@router.post(
    "/",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="""
    Login endpoint - Authenticate user with email and password.

    **Response cases:**
    1. **Successful login**: Returns access_token, refresh_token, session_id, and user details
    2. **Password change required**: Returns 403 with message "change password"
       - User must call `/change-password` endpoint
       - After password change, call `/after-change-password-login` to get tokens
    
    **Automatic Sync:**
    - On every login, syncs latest user data from admin_service.usersetup_basic to auth_users
    - Ensures auth_users table is always up-to-date with admin_service
    """,
    tags=["Authentication"]
)
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    admin_db: Session = Depends(get_admin_db)
):
    """
    Login endpoint - Authenticate user with email and password
    
    - Authenticates user from admin_service.usersetup_basic table (first login)
    - Or from local auth_users table (subsequent logins)
    - Automatically syncs latest user data from admin_service to auth_users on every login
    - If password change required, returns 403
    - Otherwise stores session and returns JWT tokens
    """
    # Extract client information from request
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    origin = request.headers.get("origin", "")

    # Delegate to service layer (includes automatic sync)
    return LoginService.login(
        db=db,
        admin_db=admin_db,
        login_data=login_data,
        client_ip=client_ip,
        user_agent=user_agent,
        origin=origin,
    )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change password in admin_service.usersetup_basic table and create/update auth_users record.",
    tags=["Authentication"]
)
def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin_db: Session = Depends(get_admin_db)
):
    """
    Change user password in both admin_service and auth_service databases
    
    **Flow:**
    - Validates current password
    - Ensures new password matches confirmation
    - Updates password in admin_service database
    - Creates/updates user in auth_users table (auth_service)
    - Returns success message with logout timer
    """
    # Delegate to service layer
    return LoginService.change_password(
        db=db,
        admin_db=admin_db,
        email=password_data.email,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        confirm_password=password_data.confirm_password
    )




@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logout endpoint - Invalidate user session",
    tags=["Authentication"]
)
def logout(
    logout_data: LogoutRequest = None,
    current_user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db)
):
    """
    Logout endpoint - Invalidate user session in auth_service database

    **Options:**
    - Single session logout (default)
    - All sessions logout (if all_sessions=true)
    """
    return LoginService.logout_user(
        db=db,
        user_id=current_user_id,
        access_token=credentials.credentials if credentials else None,
        refresh_token=logout_data.refresh_token if logout_data else None,
        all_sessions=logout_data.all_sessions if logout_data else False
    )




@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Refresh access token using refresh token",
    tags=["Authentication"]
)
def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    **Process:**
    1. Validates the refresh token
    2. Extracts user information from token payload
    3. Generates new access token
    4. Returns new access token with expiration time
    """
    # Delegate to service layer
    result = LoginService.refresh_access_token(
        db=db,
        refresh_token=token_data.refresh_token
    )
    
    return RefreshTokenResponse(**result)

