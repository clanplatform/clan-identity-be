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
            # Employment Status
            status=sync_data.status,
            start_date=sync_data.start_date,
            end_date=sync_data.end_date,
            tem_employee=sync_data.tem_employee,
            # Organizational Structure
            department=sync_data.department,
            division=sync_data.division,
            job_code=sync_data.job_code,
            # Role Management
            manage_roles=sync_data.manage_roles,
            # Default Settings
            default_dept=sync_data.default_dept,
            reporting_to=sync_data.reporting_to,
            # Entity Access
            entities=sync_data.entities,
            default_entity=sync_data.default_entity,
            # View Preferences
            view=sync_data.view,
            dashboard_view=sync_data.dashboard_view,
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
        
        # Employment Status
        user.status = sync_data.status
        user.start_date = sync_data.start_date
        user.end_date = sync_data.end_date
        user.tem_employee = sync_data.tem_employee
        
        # Organizational Structure
        user.department = sync_data.department
        user.division = sync_data.division
        user.job_code = sync_data.job_code
        
        # Role Management
        user.manage_roles = sync_data.manage_roles
        
        # Default Settings
        user.default_dept = sync_data.default_dept
        user.reporting_to = sync_data.reporting_to
        
        # Entity Access
        user.entities = sync_data.entities
        user.default_entity = sync_data.default_entity
        
        # View Preferences
        user.view = sync_data.view
        user.dashboard_view = sync_data.dashboard_view
        
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
                status=admin_user_data.get("status", "active"),
                start_date=admin_user_data.get("start_date"),
                end_date=admin_user_data.get("end_date"),
                tem_employee=admin_user_data.get("tem_employee", False),
                department=admin_user_data.get("department"),
                division=admin_user_data.get("division"),
                job_code=admin_user_data.get("job_code"),
                manage_roles=admin_user_data.get("manage_roles"),
                default_dept=admin_user_data.get("default_dept"),
                reporting_to=admin_user_data.get("reporting_to"),
                entities=admin_user_data.get("entities"),
                default_entity=admin_user_data.get("default_entity"),
                view=admin_user_data.get("view"),
                dashboard_view=admin_user_data.get("dashboard_view"),
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
