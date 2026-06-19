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

# Audit
from core.audit_client import fire_audit_log

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
    - On every login, syncs latest user data from clan_platform.usersetup_basic to auth_users
    - Ensures auth_users table is always up-to-date with clan_platform
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

    - Authenticates user from clan_platform.usersetup_basic table (first login)
    - Or from local auth_users table (subsequent logins)
    - Automatically syncs latest user data from clan_platform to auth_users on every login
    - If password change required, returns 403
    - Otherwise stores session and returns JWT tokens
    """
    # Extract client information from request
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent", "")

    # Delegate to service layer (includes automatic sync)
    result = LoginService.login(
        db=db,
        admin_db=admin_db,
        login_data=login_data,
        client_ip=client_ip,
        user_agent=user_agent
    )

    fire_audit_log(
        action="LOGIN",
        object_type="AUTH_USER",
        object_id=str(result.user.id),
        user_id=str(result.user.id),
        session_id=str(result.session_id),
        ip_address=client_ip,
        user_agent=user_agent,
        risk_score="LOW",
    )

    return result


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change password in clan_platform.usersetup_basic table and create/update auth_users record.",
    tags=["Authentication"]
)
def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin_db: Session = Depends(get_admin_db)
):
    """
    Change user password in both clan_platform and clan_identity databases

    **Flow:**
    - Validates current password
    - Ensures new password matches confirmation
    - Updates password in clan_platform database
    - Creates/updates user in auth_users table (clan_identity)
    - Returns success message with logout timer
    """
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent", "")

    # Delegate to service layer
    result = LoginService.change_password(
        db=db,
        admin_db=admin_db,
        email=password_data.email,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        confirm_password=password_data.confirm_password
    )

    fire_audit_log(
        action="CHANGE_PASSWORD",
        object_type="AUTH_USER",
        object_id=password_data.email,
        user_id=password_data.email,
        ip_address=client_ip,
        user_agent=user_agent,
        risk_score="MEDIUM",
    )

    return result


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logout endpoint - Invalidate user session",
    tags=["Authentication"]
)
def logout(
    request: Request,
    logout_data: LogoutRequest = None,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Logout endpoint - Invalidate user session in clan_identity database

    **Options:**
    - Single session logout (default)
    - All sessions logout (if all_sessions=true)
    """
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent", "")

    # Delegate to service layer
    result = LoginService.logout_user(
        db=db,
        user_id=current_user_id,
        refresh_token=logout_data.refresh_token if logout_data else None,
        all_sessions=logout_data.all_sessions if logout_data else False
    )

    fire_audit_log(
        action="LOGOUT",
        object_type="AUTH_USER",
        object_id=current_user_id,
        user_id=current_user_id,
        ip_address=client_ip,
        user_agent=user_agent,
        risk_score="LOW",
    )

    return result


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
