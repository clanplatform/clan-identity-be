"""
Sync Schemas - Data Transfer Objects for User Synchronization
Schemas for syncing users between clan_platform and clan_identity
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date


class UserSyncRequest(BaseModel):
    """
    Schema for syncing a single user from clan_platform to clan_identity
    Contains all fields from usersetup_basic table
    """
    # Primary ID
    id: UUID = Field(..., description="User ID from clan_platform.usersetup_basic (primary key)")
    
    # Reference ID from clan_platform (kept for compatibility)
    user_setup_id: UUID = Field(..., description="User ID from clan_platform.usersetup_basic")
    
    # Personal Information
    firstname: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    employee_id: str = Field(..., min_length=1, max_length=50)
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=20)
    
    # Authentication
    password_hash: str = Field(..., description="Hashed password from clan_platform")
    password_changed: Optional[datetime] = None
    is_password_change: bool = Field(default=False, description="Whether password has been changed from default")
    
    # Employment Status
    status: str = Field(default="active", max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tem_employee: bool = Field(default=False)
    
    # Organizational Structure (UUIDs)
    department: Optional[UUID] = None
    division: Optional[UUID] = None
    job_code: Optional[UUID] = None
    
    # Role Management
    manage_roles: Optional[List[UUID]] = Field(default=None)
    
    # Default Settings
    default_dept: Optional[UUID] = None
    reporting_to: Optional[UUID] = None
    
    # Entity Access
    entities: Optional[List[UUID]] = Field(default=None)
    default_entity: Optional[UUID] = None
    
    # View Preferences
    view: Optional[str] = Field(None, max_length=50)
    dashboard_view: Optional[str] = Field(None, max_length=50)

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
                "status": "active",
                "tem_employee": False
            }
        }


class UserSyncResponse(BaseModel):
    """Response schema for user sync operation"""
    message: str
    user_id: UUID = Field(..., description="clan_identity user ID (auth_users.id)")
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
    """Schema for deleting user from clan_identity"""
    user_setup_id: UUID = Field(..., description="User ID from clan_platform")
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
    is_synced: bool = Field(..., description="Whether user is synced to clan_identity")
    user_id: Optional[UUID] = Field(None, description="clan_identity user ID if synced")
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
