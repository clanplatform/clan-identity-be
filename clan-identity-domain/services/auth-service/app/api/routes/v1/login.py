"""
Login API Routes - CRUD Layer
Handles HTTP requests and responses for authentication endpoints
Business logic delegated to LoginService
"""
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from typing import Dict

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
    2. **Password change required**: Returns is_password_change: false with message "change password"
       - User must call `/change-password` endpoint
       - After password change, call `/after-change-password-login` to get tokens
    """,
    tags=["Authentication"]
)
def login(
    request: Request,
    login_data: LoginRequest,
    auth_db: Session = Depends(get_db),
    admin_db: Session = Depends(get_admin_db)
):
    """
    Login endpoint - Authenticate user with email and password
    
    - Authenticates user from admin_service.usersetup_basic table
    - If password change required, returns password change info
    - Otherwise stores session and returns JWT tokens
    """
    # Extract client information from request
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Delegate to service layer
    return LoginService.login(
        auth_db=auth_db,
        admin_db=admin_db,
        login_data=login_data,
        client_ip=client_ip,
        user_agent=user_agent
    )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change password in admin_service.usersetup_basic table.",
    tags=["Authentication"]
)
def change_password(
    password_data: ChangePasswordRequest,
    admin_db: Session = Depends(get_admin_db)
):
    """
    Change user password in admin_service database
    
    **Flow:**
    - Validates current password
    - Ensures new password matches confirmation
    - Updates password in database
    - Returns success message with logout timer
    """
    # Delegate to service layer
    return LoginService.change_password(
        admin_db=admin_db,
        email=password_data.email,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        confirm_password=password_data.confirm_password
    )


@router.post(
    "/after-change-password-login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login After Password Change",
    description="""
    Login endpoint for users who have just changed their password.

    **Flow:**
    1. User attempts login → receives `is_password_change_required: true`
    2. User calls `/change-password` → receives success with `logout_in_seconds: 2`
    3. After 2 seconds, frontend calls this endpoint with new password
    4. User receives access_token, refresh_token, and full user details
    """,
    tags=["Authentication"]
)
def after_change_password_login(
    request: Request,
    login_data: LoginRequest,
    auth_db: Session = Depends(get_db),
    admin_db: Session = Depends(get_admin_db)
):
    """
    Login endpoint for users who have just changed their password.
    Returns full login response with tokens and user details.
    """
    # Extract client information from request
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Delegate to service layer (same login logic)
    return LoginService.login(
        auth_db=auth_db,
        admin_db=admin_db,
        login_data=login_data,
        client_ip=client_ip,
        user_agent=user_agent
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
    auth_db: Session = Depends(get_db)
):
    """
    Logout endpoint - Invalidate user session in user_service database
    
    **Options:**
    - Single session logout (default)
    - All sessions logout (if all_sessions=true)
    """
    # Delegate to service layer
    return LoginService.logout_user(
        auth_db=auth_db,
        user_id=current_user_id,
        refresh_token=logout_data.refresh_token if logout_data else None,
        all_sessions=logout_data.all_sessions if logout_data else False
    )


@router.get(
    "/me",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get current authenticated user information from admin_service",
    tags=["User Info"]
)
def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    admin_db: Session = Depends(get_admin_db)
):
    """
    Get current authenticated user info from admin_service
    
    **Returns:**
    - user_id: User UUID
    - email: User email address
    - username: Username
    - firstname: First name
    - lastname: Last name
    - employee_id: Employee ID
    - status: Account status
    """
    # Delegate to service layer
    return LoginService.get_current_user_info(
        admin_db=admin_db,
        user_id=current_user_id
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

