"""
Login Schemas for authentication
Request and response schemas for login-related endpoints
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    # NOTE: tenant is resolved server-side by email (auth_users directory) and is
    # carried onward only via the JWT — the client never sends tenant_id.


class UserLoginInfo(BaseModel):
    """User information returned after login"""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., description="Username")
    firstname: Optional[str] = Field(None, description="First name")
    lastname: Optional[str] = Field(None, description="Last name")
    employee_id: Optional[str] = Field(None, description="Employee ID")
    status: str = Field(..., description="User status")
    roles: List[UUID] = Field(default=[], description="Assigned role IDs")
    admin_user_id: Optional[UUID] = Field(None, description="Reference to admin service user")
    tenant_id: Optional[UUID] = Field(None, description="Tenant UUID from clients table")

    class Config:
        from_attributes = True


class PasswordChangeRequiredResponse(BaseModel):
    """Response when password change is required (first login) - 403 Forbidden"""
    message: str = Field(..., description="Message indicating password change is needed")
    error_code: str = Field(default="FIRST_LOGIN_PASSWORD_CHANGE_REQUIRED", description="Error code")
    error_type: str = Field(default="validation_error", description="Error type")
    show_popup: bool = Field(default=True, description="Whether to show popup message")
    require_password_change: bool = Field(default=True, description="Password change is required")
    email: EmailStr = Field(..., description="User email for password change flow")
    is_password_change: bool = Field(default=False, description="Current password change status")


class LoginResponse(BaseModel):
    """Login response schema with tokens and user info"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    is_password_change: bool = Field(..., description="Password change status from database")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    session_id: UUID = Field(..., description="Session ID")
    user: UserLoginInfo = Field(..., description="User info")
    redirect_to: Optional[str] = Field(
        None,
        description="Tenant's application URL (from tenants.allowed_origins) — frontend should redirect here after login",
    )


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    email: EmailStr = Field(..., description="User email address")
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")


class ChangePasswordResponse(BaseModel):
    """Change password response schema"""
    message: str = Field(..., description="Success message")
    email: EmailStr = Field(..., description="User email address")
    show_popup: bool = Field(default=True, description="Whether to show popup message")
    logout_in_seconds: int = Field(default=2, description="Logout timer in seconds")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema - Request OTP for password reset"""
    email: EmailStr = Field(..., description="User email address")
    purpose: str = Field(default="forgot_password", description="Purpose of OTP request")


class ForgotPasswordResponse(BaseModel):
    """Forgot password response schema"""
    message: str = Field(..., description="Success message")
    email: EmailStr = Field(..., description="Email where OTP was sent")
    expires_in_minutes: int = Field(..., description="OTP expiration time in minutes")


class OTPVerifyRequest(BaseModel):
    """OTP verification request schema"""
    email: EmailStr = Field(..., description="User email address")
    otp_code: str = Field(..., min_length=4, max_length=10, description="OTP verification code")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class LogoutRequest(BaseModel):
    """Logout request schema"""
    refresh_token: Optional[str] = Field(None, description="Refresh token to invalidate")
    all_sessions: bool = Field(False, description="Logout from all sessions")


class LogoutResponse(BaseModel):
    """Logout response schema"""
    message: str = Field(..., description="Logout message")
    sessions_revoked: int = Field(default=1, description="Number of sessions revoked")


class SessionInfo(BaseModel):
    """Session information schema"""
    id: UUID = Field(..., description="Session ID")
    device_type: Optional[str] = Field(None, description="Device type")
    device_name: Optional[str] = Field(None, description="Device name")
    ip_address: Optional[str] = Field(None, description="IP address")
    browser: Optional[str] = Field(None, description="Browser")
    country: Optional[str] = Field(None, description="Country")
    is_current: bool = Field(False, description="Is this the current session")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    created_at: datetime = Field(..., description="Session creation timestamp")

    class Config:
        from_attributes = True


# Update forward references
LoginResponse.model_rebuild()

