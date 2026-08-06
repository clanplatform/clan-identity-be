"""
Sync Service - Business Logic for User Synchronization
Handles syncing users between admin_service.usersetup_basic and auth_service.auth_users
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from uuid import UUID
import logging

# Import models
try:
    from models.login_user import AuthUser
except ImportError:
    from app.models.login_user import AuthUser

# Import schemas
try:
    from schemas.sync_schemas import UserSyncRequest
except ImportError:
    from app.schemas.sync_schemas import UserSyncRequest

logger = logging.getLogger(__name__)


class SyncService:
    """
    Service class for handling user synchronization between admin_service and auth_service
    """

    @staticmethod
    def sync_user(db: Session, sync_data: UserSyncRequest) -> Dict[str, Any]:
        """
        Sync a single user from admin_service to auth_service
        
        **Logic:**
        - If user exists (by user_setup_id), update all fields
        - If user doesn't exist, create new user
        - Returns operation type (created/updated)
        
        Args:
            db: Database session for auth_service
            sync_data: User data from admin_service
            
        Returns:
            Dictionary with sync result
        """
        try:
            # Check if user already exists by id or user_setup_id
            existing_user = db.query(AuthUser).filter(
                (AuthUser.id == sync_data.id) | (AuthUser.user_setup_id == sync_data.user_setup_id)
            ).first()

            if existing_user:
                # Update existing user
                operation = "updated"
                user = SyncService._update_auth_user(db, existing_user, sync_data)
                logger.info(f"Updated auth_user for email: {sync_data.email} (id: {sync_data.id})")
            else:
                # Create new user
                operation = "created"
                user = SyncService._create_auth_user(db, sync_data)
                logger.info(f"Created auth_user for email: {sync_data.email} (id: {sync_data.id})")

            return {
                "user_id": user.id,
                "user_setup_id": user.user_setup_id,
                "email": user.email,
                "synced_at": datetime.now(timezone.utc),
                "operation": operation
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync user {sync_data.email}: {e}")
            logger.exception("Full exception:")
            raise Exception(f"Failed to sync user: {str(e)}")

    @staticmethod
    def sync_users_bulk(db: Session, users_data: List[UserSyncRequest]) -> Dict[str, Any]:
        """
        Sync multiple users in bulk
        
        Args:
            db: Database session
            users_data: List of user data to sync
            
        Returns:
            Dictionary with bulk sync statistics and individual results
        """
        results = []
        successful = 0
        failed = 0

        for user_data in users_data:
            try:
                result = SyncService.sync_user(db, user_data)
                results.append({
                    "user_setup_id": user_data.user_setup_id,
                    "email": user_data.email,
                    "success": True,
                    "operation": result["operation"],
                    "error": None
                })
                successful += 1
            except Exception as e:
                results.append({
                    "user_setup_id": user_data.user_setup_id,
                    "email": user_data.email,
                    "success": False,
                    "operation": None,
                    "error": str(e)
                })
                failed += 1
                logger.error(f"Failed to sync user {user_data.email}: {e}")

        return {
            "total_users": len(users_data),
            "successful": successful,
            "failed": failed,
            "results": results,
            "synced_at": datetime.now(timezone.utc)
        }

    @staticmethod
    def delete_user(db: Session, user_setup_id: UUID, email: str) -> Dict[str, Any]:
        """
        Delete user from auth_service when deleted from admin_service
        
        Args:
            db: Database session
            user_setup_id: User ID from admin_service
            email: Email for validation
            
        Returns:
            Dictionary with deletion confirmation
        """
        try:
            # Find user by user_setup_id
            user = db.query(AuthUser).filter(
                AuthUser.user_setup_id == user_setup_id
            ).first()

            if not user:
                raise Exception(f"User not found with user_setup_id: {user_setup_id}")

            # Validate email matches for safety
            if user.email != email:
                raise Exception(f"Email mismatch: expected {user.email}, got {email}")

            # Delete user (sessions will cascade if FK configured)
            db.delete(user)
            db.commit()
            
            logger.info(f"Deleted auth_user: {email} (user_setup_id: {user_setup_id})")

            return {
                "user_setup_id": user_setup_id,
                "email": email,
                "deleted_at": datetime.now(timezone.utc)
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete user {email}: {e}")
            raise Exception(f"Failed to delete user: {str(e)}")

    @staticmethod
    def check_sync_status(db: Session, user_setup_id: UUID) -> Dict[str, Any]:
        """
        Check if user is synced to auth_service
        
        Args:
            db: Database session
            user_setup_id: User ID from admin_service
            
        Returns:
            Dictionary with sync status
        """
        try:
            user = db.query(AuthUser).filter(
                AuthUser.user_setup_id == user_setup_id
            ).first()

            if user:
                return {
                    "is_synced": True,
                    "user_id": user.id,
                    "user_setup_id": user.user_setup_id,
                    "email": user.email,
                    "last_synced_at": user.updated_at,
                    "status": user.status
                }
            else:
                return {
                    "is_synced": False,
                    "user_id": None,
                    "user_setup_id": user_setup_id,
                    "email": None,
                    "last_synced_at": None,
                    "status": None
                }

        except Exception as e:
            logger.error(f"Failed to check sync status for {user_setup_id}: {e}")
            raise Exception(f"Failed to check sync status: {str(e)}")

    @staticmethod
    def _create_auth_user(db: Session, sync_data: UserSyncRequest) -> AuthUser:
        """
        Create a new user in auth_users table from sync data
        
        Args:
            db: Database session
            sync_data: User data from admin_service
            
        Returns:
            Created AuthUser object
        """
        auth_user = AuthUser(
            id=sync_data.id,
            user_setup_id=sync_data.user_setup_id,
            # Personal Information
            firstname=sync_data.firstname,
            lastname=sync_data.lastname,
            employee_id=sync_data.employee_id,
            username=sync_data.username,
            email=sync_data.email,
            phone_number=sync_data.phone_number,
            # Authentication
            password_hash=sync_data.password_hash,
            password_changed=sync_data.password_changed,
            is_password_change=sync_data.is_password_change,
            can_change_password=getattr(sync_data, "can_change_password", True),
            # Employment Status
            status=sync_data.status,
            # Role assignment
            role_id=getattr(sync_data, "role_id", None),
            # Branch / location
            entity_id=getattr(sync_data, "entity_id", None),
            # Tenant
            tenant_id=getattr(sync_data, "tenant_id", None),
            # User group + invite flag + allowed origins
            user_group_id=getattr(sync_data, "user_group_id", None),
            send_invite_email=getattr(sync_data, "send_invite_email", False),
            allowed_origins=getattr(sync_data, "allowed_origins", None),
        )

        db.add(auth_user)
        db.commit()
        db.refresh(auth_user)
        
        return auth_user

    @staticmethod
    def _update_auth_user(db: Session, user: AuthUser, sync_data: UserSyncRequest) -> AuthUser:
        """
        Update existing user in auth_users table from sync data
        
        Args:
            db: Database session
            user: Existing AuthUser object
            sync_data: Updated user data from admin_service
            
        Returns:
            Updated AuthUser object
        """
        # Update ID if different (to sync primary keys)
        if user.id != sync_data.id:
            user.id = sync_data.id
        
        # Personal Information
        user.firstname = sync_data.firstname
        user.lastname = sync_data.lastname
        user.employee_id = sync_data.employee_id
        user.username = sync_data.username
        user.email = sync_data.email
        user.phone_number = sync_data.phone_number
        
        # Authentication
        user.password_hash = sync_data.password_hash
        user.password_changed = sync_data.password_changed
        user.is_password_change = sync_data.is_password_change
        user.can_change_password = getattr(sync_data, "can_change_password", True)

        # Employment Status
        user.status = sync_data.status

        # Role assignment
        user.role_id = getattr(sync_data, "role_id", None)

        # Branch / location
        user.entity_id = getattr(sync_data, "entity_id", None)

        # Tenant
        if getattr(sync_data, "tenant_id", None) is not None:
            user.tenant_id = sync_data.tenant_id

        # User group + invite flag + allowed origins
        user.user_group_id = getattr(sync_data, "user_group_id", None)
        user.send_invite_email = getattr(sync_data, "send_invite_email", False)
        user.allowed_origins = getattr(sync_data, "allowed_origins", None)

        # Update timestamp
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        
        return user

    @staticmethod
    def sync_user_from_admin_data(
        db: Session,
        admin_user_data: Dict[str, Any]
    ) -> Optional[AuthUser]:
        """
        Sync user from admin_service data dictionary (used during login)
        Converts admin data to UserSyncRequest and syncs
        
        Args:
            db: Database session for auth_service
            admin_user_data: User data from admin_service.usersetup_basic
            
        Returns:
            Synced AuthUser object or None if sync fails
        """
        try:
            # Create UserSyncRequest from admin data
            sync_data = UserSyncRequest(
                id=admin_user_data["id"],
                user_setup_id=admin_user_data["id"],  # Use same ID for both
                firstname=admin_user_data["firstname"],
                lastname=admin_user_data["lastname"],
                employee_id=admin_user_data["employee_id"],
                username=admin_user_data["username"],
                email=admin_user_data["email"],
                phone_number=admin_user_data.get("phone_number"),
                password_hash=admin_user_data["password_hash"],
                password_changed=admin_user_data.get("password_changed"),
                is_password_change=admin_user_data.get("is_password_change", False),
                can_change_password=admin_user_data.get("can_change_password", True),
                status=admin_user_data.get("status", "active"),
                role_id=admin_user_data.get("role_id"),
                entity_id=admin_user_data.get("entity_id"),
                tenant_id=admin_user_data.get("tenant_id"),
                user_group_id=admin_user_data.get("user_group_id"),
                send_invite_email=admin_user_data.get("send_invite_email", False),
                allowed_origins=admin_user_data.get("allowed_origins"),
            )

            # Sync the user
            result = SyncService.sync_user(db, sync_data)
            
            # Retrieve and return the synced user
            synced_user = db.query(AuthUser).filter(
                AuthUser.id == result["user_id"]
            ).first()
            
            return synced_user
            
        except Exception as e:
            logger.error(f"Failed to sync user from admin data: {e}")
            logger.exception("Full exception:")
            return None
