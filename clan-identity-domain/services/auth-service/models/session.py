"""
Session Model for auth_service database
Stores user session information for login tracking
Note: user_id references admin_service.usersetup_basic (no FK constraint)
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

try:
    from database.database import Base
except ImportError:
    from app.db.database import Base


class Session(Base):
    """
    Session table for storing user login sessions
    Tracks active sessions, devices, and session metadata
    Note: user_id references users in admin_service.usersetup_basic
    """
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference (UUID from admin_service.usersetup_basic - no FK constraint)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Token information
    access_token_hash = Column(String(255), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=True, index=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_reason = Column(String(100), nullable=True)  # manual, expired, security, logout
    
    # Device information
    device_id = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)  # web, mobile, tablet, desktop
    device_name = Column(String(255), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    
    # Client information
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    
    # Location (optional, based on IP)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Trust status
    is_trusted = Column(Boolean, default=False, nullable=False)
    trusted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Activity tracking
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_ip = Column(String(45), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
    
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        from datetime import datetime, timezone
        
        if not self.is_active or self.is_revoked:
            return False
        if self.expires_at < datetime.now(timezone.utc):
            return False
        return True

