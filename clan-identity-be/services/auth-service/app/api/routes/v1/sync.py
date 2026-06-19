"""
Sync API Routes - User Synchronization Endpoints
Handles HTTP requests for syncing users between clan_platform and clan_identity
Called by clan_platform when users are created, updated, or deleted
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

# Audit
from core.audit_client import fire_audit_log

router = APIRouter()


@router.post(
    "/user",
    response_model=UserSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync User from Admin Service",
    description="""
    Sync a single user from clan_platform.usersetup_basic to clan_identity.auth_users.

    **Use Cases:**
    - When a new user is created in clan_platform
    - When user details are updated in clan_platform
    - When password is changed in clan_platform

    **Behavior:**
    - If user exists (by user_setup_id), updates all fields
    - If user doesn't exist, creates new user
    - Returns operation type (created/updated) in response

    **Authentication:**
    This endpoint should be called only by clan_platform (internal service-to-service communication).
    In production, secure this with service authentication (API key, mTLS, etc.)
    """,
    tags=["Sync"]
)
def sync_user(
    sync_data: UserSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync single user from clan_platform to clan_identity

    **Flow:**
    1. Check if user exists by user_setup_id
    2. If exists, update all fields
    3. If not exists, create new user
    4. Return sync result with operation type
    """
    try:
        result = SyncService.sync_user(db=db, sync_data=sync_data)

        response = UserSyncResponse(
            message=f"User {result['operation']} successfully",
            user_id=result["user_id"],
            user_setup_id=result["user_setup_id"],
            email=result["email"],
            synced_at=result["synced_at"],
            operation=result["operation"]
        )

        action = "CREATE" if result["operation"] == "created" else "UPDATE"
        fire_audit_log(
            action=action,
            object_type="AUTH_USER",
            object_id=str(result["user_setup_id"]),
            user_id=str(result["user_id"]),
            risk_score="LOW" if action == "CREATE" else "MEDIUM",
        )

        return response

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
    This endpoint should be called only by clan_platform (internal service-to-service communication).
    """,
    tags=["Sync"]
)
def sync_users_bulk(
    bulk_data: BulkUserSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk sync multiple users from clan_platform to clan_identity

    **Flow:**
    1. Process each user in the list
    2. Collect results (success/failure) for each
    3. Return aggregate statistics and individual results
    """
    try:
        result = SyncService.sync_users_bulk(db=db, users_data=bulk_data.users)

        response = BulkUserSyncResponse(
            message=f"Bulk sync completed: {result['successful']} succeeded, {result['failed']} failed",
            total_users=result["total_users"],
            successful=result["successful"],
            failed=result["failed"],
            results=result["results"],
            synced_at=result["synced_at"]
        )

        fire_audit_log(
            action="BULK_SYNC",
            object_type="AUTH_USER",
            new_values={
                "total_users": result["total_users"],
                "successful": result["successful"],
                "failed": result["failed"],
            },
            risk_score="MEDIUM",
        )

        return response

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
    Delete user from clan_identity when deleted from clan_platform.

    **Use Cases:**
    - When user is deleted/removed from clan_platform
    - When user account is deactivated permanently

    **Behavior:**
    - Finds user by user_setup_id
    - Validates email matches for safety
    - Permanently deletes user from auth_users table
    - Also deletes associated sessions (cascade)

    **Authentication:**
    This endpoint should be called only by clan_platform (internal service-to-service communication).

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
    Delete user from clan_identity when deleted from clan_platform

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

        response = UserDeleteSyncResponse(
            message="User deleted successfully from clan_identity",
            user_setup_id=result["user_setup_id"],
            email=result["email"],
            deleted_at=result["deleted_at"]
        )

        fire_audit_log(
            action="DELETE",
            object_type="AUTH_USER",
            object_id=str(result["user_setup_id"]),
            old_values={"email": result["email"]},
            risk_score="HIGH",
        )

        return response

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
    Check if a user from clan_platform is synced to clan_identity.

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
    Check if user is synced from clan_platform to clan_identity

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
