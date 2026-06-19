"""
Auth User Model for clan_identity database
Mirrors the usersetup_basic table structure from clan_platform
Used for local authentication after first password change.
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Date
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
    
    # Reference to clan_platform user (for linking)
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
    
    # Employment Status
    status = Column(String(50), nullable=False, default='active', index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    tem_employee = Column(Boolean, default=False, nullable=False)
    
    # Organizational Structure (stored as UUIDs, no FK constraints)
    department = Column(UUID(as_uuid=True), nullable=True)
    division = Column(UUID(as_uuid=True), nullable=True)
    job_code = Column(UUID(as_uuid=True), nullable=True)
    
    # Role Management
    manage_roles = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # Default Settings
    default_dept = Column(UUID(as_uuid=True), nullable=True)
    reporting_to = Column(UUID(as_uuid=True), nullable=True)
    
    # Entity Access
    entities = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    default_entity = Column(UUID(as_uuid=True), nullable=True)
    
    # View Preferences
    view = Column(String(50), nullable=True)
    dashboard_view = Column(String(50), nullable=True)
    
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

