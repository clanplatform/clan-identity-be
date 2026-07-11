"""
Login Attempt Model for auth_service database
Tracks login attempts for security and rate limiting
Note: user_id references admin_service.usersetup_basic (no FK constraint)
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

try:
    from database.database import Base
except ImportError:
    from app.db.database import Base


class LoginAttempt(Base):
    """
    Login Attempt table for tracking all login attempts
    Used for security monitoring, rate limiting, and audit
    Note: user_id references users in admin_service.usersetup_basic
    """
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference (UUID from admin_service.usersetup_basic - no FK constraint)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Tenant / session context
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # NULL = master user
    session_id = Column(UUID(as_uuid=True), nullable=True)  # set on successful login

    # Attempt details
    email_or_username = Column(String(255), nullable=False, index=True)
    attempt_type = Column(String(50), nullable=False, default="password")  # password, otp, 2fa, sso

    # Result
    is_successful = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String(100), nullable=True)  # invalid_credentials, account_locked, 2fa_required, etc.

    # Network (server-side: request IP + IP-intelligence lookup)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    ip_type = Column(String(10), nullable=True)  # ipv4 | ipv6
    isp = Column(String(150), nullable=True)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    is_vpn = Column(Boolean, default=False, nullable=False)
    is_proxy = Column(Boolean, default=False, nullable=False)
    is_tor = Column(Boolean, default=False, nullable=False)

    # Device (server-side: parsed from User-Agent header)
    user_agent = Column(Text, nullable=True)  # raw header, kept for audit
    device_type = Column(String(20), nullable=True)  # desktop | mobile | tablet | bot
    device_name = Column(String(100), nullable=True)  # e.g. 'Windows PC', 'iPhone'
    browser = Column(String(50), nullable=True)
    browser_version = Column(String(20), nullable=True)
    os = Column(String(50), nullable=True)
    os_version = Column(String(20), nullable=True)

    # Device fingerprint (for detecting suspicious activity)
    device_fingerprint = Column(String(255), nullable=True)

    # Risk assessment
    risk_score = Column(SmallInteger, nullable=True)  # 0-100 risk score
    is_suspicious = Column(Boolean, default=False, nullable=False)
    suspicious_reason = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<LoginAttempt(id={self.id}, email={self.email_or_username}, success={self.is_successful})>"

