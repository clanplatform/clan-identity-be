"""
Auth User Model for auth_service database
Mirrors the usersetup_basic table structure from admin_service
Used for local authentication after first password change.
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func

try:
    from database.database import Base
except ImportError:
    from app.db.database import Base


class AuthUser(Base):
    """
    Auth User table - Mirrors usersetup_basic structure
    Used for local authentication after first password change
    """
    __tablename__ = "auth_users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to admin_service user (for linking)
    user_setup_id = Column(UUID(as_uuid=True), nullable=True, unique=True, index=True)
    
    # Personal Information
    firstname = Column(String(100), nullable=False)
    lastname = Column(String(100), nullable=False)
    employee_id = Column(String(50), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone_number = Column(String(20), nullable=True)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    password_changed = Column(DateTime(timezone=True), nullable=True)
    is_password_change = Column(Boolean, default=False, nullable=False)
    # True → first-login password-change flow applies; False → user logs
    # straight in and is redirected to the tenant's application.
    can_change_password = Column(Boolean, default=True, server_default='true', nullable=False)
    
    # Employment Status
    status = Column(String(50), nullable=False, default='active', index=True)

    # Tenant identifier (from clients.tenant_id in admin_service)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Role assignment — single role (user_role.id), mirrors usersetup_basic.role_id
    role_id = Column(UUID(as_uuid=True), nullable=True)

    # Branch / location — entities.entity_id, mirrors usersetup_basic.entity_id.
    # A user can belong to multiple entities; the first is the default/primary.
    entity_id = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # Department / Division Access — mirrors usersetup_basic.department_id /
    # .division_id, used to resolve a role's access_scope of "department" or
    # "division". Backend-derived in admin-service from job_code_id below,
    # not accepted/returned on either service's schema.
    department_id = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    division_id = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # Job code (job_codes.id in admin-service — no local FK, cross-database),
    # mirrors usersetup_basic.job_code_id.
    job_code_id = Column(UUID(as_uuid=True), nullable=True)

    # User group (bare reference), invite flag and per-user allowed origins
    # (mirrors usersetup_basic)
    user_group_id = Column(UUID(as_uuid=True), nullable=True)
    send_invite_email = Column(Boolean, nullable=False, server_default='false', default=False)
    allowed_origins = Column(ARRAY(Text), nullable=True)

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
    
    @property
    def is_password_change_required(self) -> bool:
        """Check if password change is required (inverse of is_password_change)"""
        return not self.is_password_change

