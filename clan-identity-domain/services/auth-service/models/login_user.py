"""
Auth User Model for auth_service database
NOTE: This model is NOT used for authentication.
Users are authenticated against admin_service.usersetup_basic table.
This table is kept for potential future use (e.g., caching user data).
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func

from app.db.database import Base


class AuthUser(Base):
    """
    Auth User table - NOT USED FOR AUTHENTICATION
    Users are authenticated against admin_service.usersetup_basic
    This table is kept for potential future use.
    """
    __tablename__ = "auth_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to admin_service user (for linking)
    admin_user_id = Column(UUID(as_uuid=True), nullable=True, unique=True, index=True)
    
    # Authentication credentials
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Basic user info (cached from admin service)
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    employee_id = Column(String(50), nullable=True, unique=True)
    
    # Account status
    status = Column(String(50), nullable=False, default='active')  # active, inactive, suspended, locked
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Password management
    password_changed = Column(DateTime(timezone=True), nullable=True)
    is_password_change_required = Column(Boolean, default=True, nullable=False)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Login tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 compatible
    failed_login_attempts = Column(String(10), default='0', nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Two-factor authentication
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    two_factor_backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    
    # Session management
    current_token = Column(Text, nullable=True)  # Current active token
    
    # Roles (cached from admin service for quick access)
    roles = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AuthUser(id={self.id}, email={self.email}, username={self.username}, status={self.status})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.firstname and self.lastname:
            return f"{self.firstname} {self.lastname}"
        return self.username

