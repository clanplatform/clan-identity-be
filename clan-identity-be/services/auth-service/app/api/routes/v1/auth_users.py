"""
Auth Users Sync Endpoint - Compatible with Admin Service
This endpoint matches the URL that admin-service calls: /api/v1/auth/users/sync
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

try:
    from database.database import get_db
except ImportError:
    from database.connection import get_db

from schemas.sync_schemas import UserSyncRequest, UserSyncResponse
from services.sync_service import SyncService

router = APIRouter()


@router.post(
    "/sync",
    response_model=UserSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync User from Admin Service",
    description="""
    This endpoint is called by admin-service when a user is created or updated.
    
    **URL**: /api/v1/auth/users/sync
    
    **Behavior:**
    - If user exists (by user_setup_id), updates all fields
    - If user doesn't exist, creates new user
    - Returns operation type (created/updated) in response
    
    **Called by admin-service when:**
    - New user is created
    - User details are updated
    - Password is changed
    """,
    tags=["Auth", "Sync"]
)
def sync_user_from_admin(
    sync_data: UserSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync single user from admin_service to auth_service
    Called automatically by admin-service
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
