"""Event schemas for auth service

Pydantic models for Kafka events published by auth service
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class BaseEvent(BaseModel):
    """Base event schema with common fields"""
    event_id: str = Field(default_factory=lambda: str(UUID))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = "auth-service"
    version: str = "1.0"
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "123e4567-e89b-12d3-a456-426614174000",
                "event_type": "user.login",
                "timestamp": "2024-01-01T12:00:00Z",
                "service": "auth-service",
                "version": "1.0"
            }
        }
    }


class UserLoginEvent(BaseEvent):
    """Event published when a user logs in"""
    event_type: str = "user.login"
    user_id: UUID
    email: str
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_method: str = "password"  # password, otp, sso, etc.
    success: bool = True


class UserLogoutEvent(BaseEvent):
    """Event published when a user logs out"""
    event_type: str = "user.logout"
    user_id: UUID
    email: str
    session_id: Optional[str] = None
    logout_reason: str = "user_initiated"  # user_initiated, session_expired, forced


class UserPasswordChangedEvent(BaseEvent):
    """Event published when a user changes their password"""
    event_type: str = "user.password_changed"
    user_id: UUID
    email: str
    changed_by: str = "user"  # user, admin, system
    is_first_login: bool = False


class TokenRefreshedEvent(BaseEvent):
    """Event published when a token is refreshed"""
    event_type: str = "token.refreshed"
    user_id: UUID
    email: str
    old_token_id: Optional[str] = None
    new_token_id: Optional[str] = None


class TokenRevokedEvent(BaseEvent):
    """Event published when a token is revoked"""
    event_type: str = "token.revoked"
    user_id: UUID
    email: str
    token_id: Optional[str] = None
    revoked_by: str = "user"  # user, admin, system
    reason: str = "user_logout"


class SessionCreatedEvent(BaseEvent):
    """Event published when a session is created"""
    event_type: str = "session.created"
    user_id: UUID
    email: str
    session_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime


class SessionExpiredEvent(BaseEvent):
    """Event published when a session expires"""
    event_type: str = "session.expired"
    user_id: UUID
    email: str
    session_id: str
    expired_at: datetime


class SessionRevokedEvent(BaseEvent):
    """Event published when a session is revoked"""
    event_type: str = "session.revoked"
    user_id: UUID
    email: str
    session_id: str
    revoked_by: str = "user"  # user, admin, system
    reason: str = "user_logout"


class LoginFailedEvent(BaseEvent):
    """Event published when a login attempt fails"""
    event_type: str = "login.failed"
    email: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    failure_reason: str  # invalid_credentials, account_locked, etc.
    attempt_count: int = 1


class OTPGeneratedEvent(BaseEvent):
    """Event published when an OTP is generated"""
    event_type: str = "otp.generated"
    user_id: Optional[UUID] = None
    email: str
    otp_type: str = "login"  # login, password_reset, verification
    expires_at: datetime


class OTPVerifiedEvent(BaseEvent):
    """Event published when an OTP is verified"""
    event_type: str = "otp.verified"
    user_id: Optional[UUID] = None
    email: str
    otp_type: str = "login"
    verified_at: datetime


class OTPExpiredEvent(BaseEvent):
    """Event published when an OTP expires"""
    event_type: str = "otp.expired"
    user_id: Optional[UUID] = None
    email: str
    otp_type: str = "login"
    expired_at: datetime


class UserDataSyncEvent(BaseEvent):
    """Event published to sync user data to admin-service"""
    event_type: str = "user.data_sync"
    user_id: UUID
    email: str
    username: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    employee_id: Optional[str] = None
    phone_number: Optional[str] = None
    status: str = "active"
    department: Optional[str] = None
    division: Optional[str] = None
    job_code: Optional[str] = None
    manage_roles: Optional[list] = None
    default_dept: Optional[str] = None
    reporting_to: Optional[str] = None
    entities: Optional[list] = None
    default_entity: Optional[str] = None
    tenant_id: Optional[UUID] = None
    sync_source: str = "auth-service"  # Source service triggering sync
    sync_action: str  # login, password_change, profile_update, etc.
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None

