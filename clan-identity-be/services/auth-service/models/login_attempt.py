"""
Login Attempt Model for clan_identity database
Tracks login attempts for security and rate limiting
Note: user_id references clan_platform.usersetup_basic (no FK constraint)
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
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
    Note: user_id references users in clan_platform.usersetup_basic
    """
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference (UUID from clan_platform.usersetup_basic - no FK constraint)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Attempt details
    email_or_username = Column(String(255), nullable=False, index=True)
    attempt_type = Column(String(50), nullable=False, default="password")  # password, otp, 2fa, sso
    
    # Result
    is_successful = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String(100), nullable=True)  # invalid_credentials, account_locked, 2fa_required, etc.
    
    # Client information
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Device fingerprint (for detecting suspicious activity)
    device_fingerprint = Column(String(255), nullable=True)
    
    # Location (based on IP)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Risk assessment
    risk_score = Column(String(10), nullable=True)  # 0-100 risk score
    is_suspicious = Column(Boolean, default=False, nullable=False)
    suspicious_reason = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<LoginAttempt(id={self.id}, email={self.email_or_username}, success={self.is_successful})>"

