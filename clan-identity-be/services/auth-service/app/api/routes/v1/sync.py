"""
Sync API Routes - User Synchronization Endpoints
Handles HTTP requests for syncing users between admin_service and auth_service
Called by admin_service when users are created, updated, or deleted
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from uuid import UUID

# Database dependencies
try:
    from database.database import get_db
except ImportError:
    from database.connection import get_db

# Schemas
from schemas.sync_schemas import (
    UserSyncRequest,
    UserSyncResponse,
    BulkUserSyncRequest,
    BulkUserSyncResponse,
    UserDeleteSyncRequest,
    UserDeleteSyncResponse,
    SyncStatusResponse
)

# Service layer
from services.sync_service import SyncService

router = APIRouter()


@router.post(
    "/user",
    response_model=UserSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync User from Admin Service",
    description="""
    Sync a single user from admin_service.usersetup_basic to auth_service.auth_users.
    
    **Use Cases:**
    - When a new user is created in admin_service
    - When user details are updated in admin_service
    - When password is changed in admin_service
    
    **Behavior:**
    - If user exists (by user_setup_id), updates all fields
    - If user doesn't exist, creates new user
    - Returns operation type (created/updated) in response
    
    **Authentication:**
    This endpoint should be called only by admin_service (internal service-to-service communication).
    In production, secure this with service authentication (API key, mTLS, etc.)
    """,
    tags=["Sync"]
)
def sync_user(
    sync_data: UserSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync single user from admin_service to auth_service
    
    **Flow:**
    1. Check if user exists by user_setup_id
    2. If exists, update all fields
    3. If not exists, create new user
    4. Return sync result with operation type
    """
    try:
        result = SyncService.sync_user(db=db, sync_data=sync_data)
        
        return UserSyncResponse(
            message=f"User {result['operation']} successfully",
            user_id=result["user_id"],
            user_setup_id=result["user_setup_id"],
            email=result["email"],
            synced_at=result["synced_at"],
            operation=result["operation"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/users/bulk",
    response_model=BulkUserSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk Sync Users from Admin Service",
    description="""
    Sync multiple users in a single request.
    
    **Use Cases:**
    - Initial migration of existing users
    - Batch synchronization of multiple users
    - Periodic sync jobs
    
    **Behavior:**
    - Processes each user individually
    - Returns detailed results for each user (success/failure)
    - Does not fail entire batch if some users fail
    - Returns counts of successful and failed syncs
    
    **Authentication:**
    This endpoint should be called only by admin_service (internal service-to-service communication).
    """,
    tags=["Sync"]
)
def sync_users_bulk(
    bulk_data: BulkUserSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk sync multiple users from admin_service to auth_service
    
    **Flow:**
    1. Process each user in the list
    2. Collect results (success/failure) for each
    3. Return aggregate statistics and individual results
    """
    try:
        result = SyncService.sync_users_bulk(db=db, users_data=bulk_data.users)
        
        return BulkUserSyncResponse(
            message=f"Bulk sync completed: {result['successful']} succeeded, {result['failed']} failed",
            total_users=result["total_users"],
            successful=result["successful"],
            failed=result["failed"],
            results=result["results"],
            synced_at=result["synced_at"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk sync failed: {str(e)}"
        )


@router.delete(
    "/user",
    response_model=UserDeleteSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete User Sync",
    description="""
    Delete user from auth_service when deleted from admin_service.
    
    **Use Cases:**
    - When user is deleted/removed from admin_service
    - When user account is deactivated permanently
    
    **Behavior:**
    - Finds user by user_setup_id
    - Validates email matches for safety
    - Permanently deletes user from auth_users table
    - Also deletes associated sessions (cascade)
    
    **Authentication:**
    This endpoint should be called only by admin_service (internal service-to-service communication).
    
    **Warning:**
    This is a permanent deletion. Consider soft-delete (status='inactive') for audit purposes.
    """,
    tags=["Sync"]
)
def delete_user_sync(
    delete_data: UserDeleteSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Delete user from auth_service when deleted from admin_service
    
    **Flow:**
    1. Find user by user_setup_id
    2. Validate email matches
    3. Delete user from auth_users table
    4. Return deletion confirmation
    """
    try:
        result = SyncService.delete_user(
            db=db,
            user_setup_id=delete_data.user_setup_id,
            email=delete_data.email
        )
        
        return UserDeleteSyncResponse(
            message="User deleted successfully from auth_service",
            user_setup_id=result["user_setup_id"],
            email=result["email"],
            deleted_at=result["deleted_at"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/status/{user_setup_id}",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check User Sync Status",
    description="""
    Check if a user from admin_service is synced to auth_service.
    
    **Use Cases:**
    - Verify if user needs to be synced
    - Check last sync timestamp
    - Debugging sync issues
    
    **Returns:**
    - Whether user is synced (boolean)
    - Auth service user ID if synced
    - Email if synced
    - Last sync timestamp
    """,
    tags=["Sync"]
)
def check_sync_status(
    user_setup_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Check if user is synced from admin_service to auth_service
    
    **Flow:**
    1. Query auth_users by user_setup_id
    2. Return sync status and details
    """
    try:
        result = SyncService.check_sync_status(db=db, user_setup_id=user_setup_id)
        
        return SyncStatusResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/user", response_model=UserSyncResponse, status_code=status.HTTP_200_OK)
def sync_user(sync_data: UserSyncRequest, db: Session = Depends(get_db)):
    """Sync single user from admin_service to auth_service"""
    try:
        result = SyncService.sync_user(db=db, sync_data=sync_data)
        return UserSyncResponse(
            message=f"User {result['operation']} successfully",
            user_id=result["user_id"],
            user_setup_id=result["user_setup_id"],
            email=result["email"],
            synced_at=result["synced_at"],
            operation=result["operation"]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/bulk", response_model=BulkUserSyncResponse)
def sync_users_bulk(bulk_data: BulkUserSyncRequest, db: Session = Depends(get_db)):
    """Bulk sync multiple users"""
    try:
        result = SyncService.sync_users_bulk(db=db, users_data=bulk_data.users)
        return BulkUserSyncResponse(
            message=f"Bulk sync completed: {result['successful']} succeeded, {result['failed']} failed",
            total_users=result["total_users"],
            successful=result["successful"],
            failed=result["failed"],
            results=result["results"],
            synced_at=result["synced_at"]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/user", response_model=UserDeleteSyncResponse)
def delete_user_sync(delete_data: UserDeleteSyncRequest, db: Session = Depends(get_db)):
    """Delete user from auth_service"""
    try:
        result = SyncService.delete_user(db=db, user_setup_id=delete_data.user_setup_id, email=delete_data.email)
        return UserDeleteSyncResponse(
            message="User deleted successfully",
            user_setup_id=result["user_setup_id"],
            email=result["email"],
            deleted_at=result["deleted_at"]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/status/{user_setup_id}", response_model=SyncStatusResponse)
def check_sync_status(user_setup_id: UUID, db: Session = Depends(get_db)):
    """Check if user is synced"""
    try:
        result = SyncService.check_sync_status(db=db, user_setup_id=user_setup_id)
        return SyncStatusResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
