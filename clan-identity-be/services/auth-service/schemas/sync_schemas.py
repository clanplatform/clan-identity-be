"""
Sync Schemas - Data Transfer Objects for User Synchronization
Schemas for syncing users between admin_service and auth_service
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class UserSyncRequest(BaseModel):
    """
    Schema for syncing a single user from admin_service to auth_service
    Contains all fields from usersetup_basic table
    """
    # Primary ID
    id: UUID = Field(..., description="User ID from admin_service.usersetup_basic (primary key)")
    
    # Reference ID from admin_service (kept for compatibility)
    user_setup_id: UUID = Field(..., description="User ID from admin_service.usersetup_basic")
    
    # Personal Information
    firstname: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    employee_id: str = Field(..., min_length=1, max_length=50)
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=20)
    
    # Authentication
    password_hash: str = Field(..., description="Hashed password from admin_service")
    password_changed: Optional[datetime] = None
    is_password_change: bool = Field(default=False, description="Whether password has been changed from default")
    can_change_password: bool = Field(
        default=True,
        description="True → forced password change on first login; False → log in directly",
    )
    
    # Employment Status
    status: str = Field(default="active", max_length=50)

    # Role assignment — single role (user_role.id), mirrors usersetup_basic.role_id
    role_id: Optional[UUID] = None

    # Branch / location — entities.entity_id, mirrors usersetup_basic.entity_id.
    # A user can belong to multiple entities; the first is the default/primary.
    entity_id: Optional[List[UUID]] = None

    # Tenant identifier (from clients.tenant_id in admin_service)
    tenant_id: Optional[UUID] = Field(None, description="Tenant UUID from clients table")

    # User group + invite flag + per-user allowed origins (mirror usersetup_basic)
    user_group_id: Optional[UUID] = None
    send_invite_email: bool = Field(default=False)
    allowed_origins: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_setup_id": "123e4567-e89b-12d3-a456-426614174000",
                "firstname": "John",
                "lastname": "Doe",
                "employee_id": "EMP001",
                "username": "john.doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
                "password_hash": "$2b$12$...",
                "is_password_change": False,
                "status": "active"
            }
        }


class UserSyncResponse(BaseModel):
    """Response schema for user sync operation"""
    message: str
    user_id: UUID = Field(..., description="Auth service user ID (auth_users.id)")
    user_setup_id: UUID = Field(..., description="Admin service user ID (usersetup_basic.id)")
    email: EmailStr
    synced_at: datetime
    operation: str = Field(..., description="Operation performed: 'created' or 'updated'")


class BulkUserSyncRequest(BaseModel):
    """Schema for bulk user synchronization"""
    users: List[UserSyncRequest] = Field(..., description="List of users to sync")

    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "user_setup_id": "123e4567-e89b-12d3-a456-426614174000",
                        "firstname": "John",
                        "lastname": "Doe",
                        "employee_id": "EMP001",
                        "username": "john.doe",
                        "email": "john.doe@example.com",
                        "password_hash": "$2b$12$...",
                        "status": "active"
                    }
                ]
            }
        }


class UserSyncResult(BaseModel):
    """Result for individual user sync in bulk operation"""
    user_setup_id: UUID
    email: EmailStr
    success: bool
    operation: Optional[str] = None  # 'created' or 'updated'
    error: Optional[str] = None


class BulkUserSyncResponse(BaseModel):
    """Response schema for bulk user sync operation"""
    message: str
    total_users: int
    successful: int
    failed: int
    results: List[UserSyncResult]
    synced_at: datetime


class UserDeleteSyncRequest(BaseModel):
    """Schema for deleting user from auth_service"""
    user_setup_id: UUID = Field(..., description="User ID from admin_service")
    email: EmailStr = Field(..., description="Email for validation")

    class Config:
        json_schema_extra = {
            "example": {
                "user_setup_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com"
            }
        }


class UserDeleteSyncResponse(BaseModel):
    """Response schema for user deletion sync"""
    message: str
    user_setup_id: UUID
    email: EmailStr
    deleted_at: datetime


class SyncStatusResponse(BaseModel):
    """Response schema for sync status check"""
    is_synced: bool = Field(..., description="Whether user is synced to auth_service")
    user_id: Optional[UUID] = Field(None, description="Auth service user ID if synced")
    user_setup_id: Optional[UUID] = Field(None, description="Admin service user ID")
    email: Optional[EmailStr] = Field(None, description="User email if synced")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp (updated_at)")
    status: Optional[str] = Field(None, description="User status if synced")

    class Config:
        json_schema_extra = {
            "example": {
                "is_synced": True,
                "user_id": "987fcdeb-51a2-43f7-8e9d-0123456789ab",
                "user_setup_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "last_synced_at": "2024-01-15T10:30:00Z",
                "status": "active"
            }
        }
