"""
Login Service - Business Logic Layer
Handles user authentication logic
AUTHENTICATION FLOW:
1. First login: Authenticates against admin_service.usersetup_basic table
2. After password change: Creates user in auth_users table
3. Subsequent logins: Authenticates from auth_users table
Stores sessions in user_service database
Publishes sync events to admin-service for user activity tracking
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging
import asyncio

# Import models (will need to be created or imported correctly)
try:
    from models.session import Session as UserSession
    from models.login_attempt import LoginAttempt
    from models.login_user import AuthUser
except ImportError:
    # Fallback imports from app
    from app.models.session import Session as UserSession
    from app.models.login_attempt import LoginAttempt
    from app.models.login_user import AuthUser

# Import schemas
try:
    from schemas.login_schemas import (
        LoginRequest, LoginResponse, UserLoginInfo,
        ChangePasswordRequest, ChangePasswordResponse
    )
except ImportError:
    # Fallback import from app
    from app.schemas.login import (
        LoginRequest, LoginResponse, UserLoginInfo,
        ChangePasswordRequest, ChangePasswordResponse
    )

# Import core utilities
from core.security import (
    verify_password, create_access_token, create_refresh_token,
    get_password_hash, hash_token, verify_token
)
from core.config import settings

# Import event publishers
try:
    from events.producers.auth_events import (
        publish_user_login_event,
        publish_user_password_changed_event,
        publish_user_data_sync_event,
        publish_session_created_event
    )
except ImportError:
    # Fallback import
    try:
        from app.events.producers.auth_events import (
            publish_user_login_event,
            publish_user_password_changed_event,
            publish_user_data_sync_event,
            publish_session_created_event
        )
    except ImportError:
        # If event publishers not available, create no-op functions
        logger.warning("Event publishers not available - events will not be published")
        async def publish_user_login_event(*args, **kwargs): return False
        async def publish_user_password_changed_event(*args, **kwargs): return False
        async def publish_user_data_sync_event(*args, **kwargs): return False
        async def publish_session_created_event(*args, **kwargs): return False

logger = logging.getLogger(__name__)


class LoginService:
    """
    Service class for handling user authentication business logic
    AUTHENTICATION FLOW:
    1. First time: Authenticates against admin_service.usersetup_basic table
    2. After password change: Creates user record in auth_users table
    3. Subsequent logins: Authenticates from auth_users table (faster, local)
    Stores sessions and login attempts in user_service database
    """

    @staticmethod
    def get_user_from_auth_db(db: Session, email: str) -> Optional[AuthUser]:
        """
        Get user from auth_users table by email
        Returns AuthUser ORM object or None
        """
        try:
            user = db.query(AuthUser).filter(AuthUser.email == email).first()
            return user
        except Exception as e:
            logger.error(f"Error querying auth_users table: {e}")
            logger.exception("Full exception:")
            # Rollback to clear any failed transaction state
            try:
                db.rollback()
            except:
                pass
            return None

    @staticmethod
    def create_auth_user_from_admin_data(
        db: Session,
        admin_user_data: Dict[str, Any],
        password_hash: str
    ) -> AuthUser:
        """
        Create a new user in auth_users table from admin service data
        Called after successful password change on first login
        Copies all fields from usersetup_basic to auth_users
        """
        try:
            logger.info(f"Creating auth_user for email: {admin_user_data['email']}")
            
            auth_user = AuthUser(
                user_setup_id=admin_user_data["id"],
                # Personal Information
                firstname=admin_user_data["firstname"],
                lastname=admin_user_data["lastname"],
                employee_id=admin_user_data["employee_id"],
                username=admin_user_data["username"],
                email=admin_user_data["email"],
                phone_number=admin_user_data.get("phone_number"),
                # Authentication
                password_hash=password_hash,
                password_changed=datetime.now(timezone.utc),
                is_password_change=True,  # Password has been changed
                # Employment Status
                status=admin_user_data.get("status", "active"),
                start_date=admin_user_data.get("start_date"),
                end_date=admin_user_data.get("end_date"),
                tem_employee=admin_user_data.get("tem_employee", False),
                # Organizational Structure
                department=admin_user_data.get("department"),
                division=admin_user_data.get("division"),
                job_code=admin_user_data.get("job_code"),
                # Role Management
                manage_roles=admin_user_data.get("manage_roles"),
                # Default Settings
                default_dept=admin_user_data.get("default_dept"),
                reporting_to=admin_user_data.get("reporting_to"),
                # Entity Access
                entities=admin_user_data.get("entities"),
                default_entity=admin_user_data.get("default_entity"),
                # View Preferences
                view=admin_user_data.get("view"),
                dashboard_view=admin_user_data.get("dashboard_view"),
            )
            
            db.add(auth_user)
            db.commit()
            db.refresh(auth_user)
            logger.info(f"Created auth_user for {admin_user_data['email']} with ID: {auth_user.id}")
            return auth_user
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create auth_user: {e}")
            logger.exception("Full exception:")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user account: {str(e)}"
            )

    @staticmethod
    def update_auth_user_password(
        db: Session,
        user: AuthUser,
        new_password_hash: str
    ) -> AuthUser:
        """
        Update password for existing auth_users record
        """
        try:
            user.password_hash = new_password_hash
            user.password_changed = datetime.now(timezone.utc)
            user.is_password_change = True  # Password has been changed
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            logger.info(f"Updated password for auth_user {user.email}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update auth_user password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )

    @staticmethod
    def get_user_from_admin_db(admin_db: Session, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user from admin_service.usersetup_basic table by email
        Returns user data as dictionary
        """
        try:
            query = text("""
                SELECT
                    ub.id,
                    ub.user_setup_id,
                    ub.firstname,
                    ub.lastname,
                    ub.employee_id,
                    ub.username,
                    ub.email,
                    ub.phone_number,
                    ub.password_hash,
                    ub.password_changed,
                    ub.is_password_change,
                    NOT ub.is_password_change as is_password_change_required,
                    ub.status,
                    ub.department,
                    ub.division,
                    ub.job_code,
                    ub.manage_roles,
                    ub.default_dept,
                    ub.reporting_to,
                    ub.entities,
                    ub.default_entity,
                    ub.created_at,
                    ub.updated_at
                FROM usersetup_basic ub
                WHERE ub.email = :email
            """)

            result = admin_db.execute(query, {"email": email}).fetchone()

            if result:
                return {
                    "id": result.id,
                    "user_setup_id": result.user_setup_id,
                    "firstname": result.firstname,
                    "lastname": result.lastname,
                    "employee_id": result.employee_id,
                    "username": result.username,
                    "email": result.email,
                    "phone_number": result.phone_number,
                    "password_hash": result.password_hash,
                    "password_changed": result.password_changed,
                    "is_password_change": result.is_password_change,
                    "is_password_change_required": result.is_password_change_required,
                    "status": result.status,
                    "department": result.department,
                    "division": result.division,
                    "job_code": result.job_code,
                    "manage_roles": result.manage_roles,
                    "default_dept": result.default_dept,
                    "reporting_to": result.reporting_to,
                    "entities": result.entities,
                    "default_entity": result.default_entity,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at,
                }
            return None
        except Exception as e:
            logger.error(f"Error querying admin_service.usersetup_basic table: {e}")
            logger.exception("Full exception:")
            # Rollback to clear any failed transaction state
            try:
                admin_db.rollback()
            except:
                pass
            return None

    @staticmethod
    def authenticate_user(db: Session, admin_db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user by email and password
        Priority: auth_users table → admin_service.usersetup_basic (fallback for first login)
        """
        # First, try to authenticate from auth_users table (local, faster)
        auth_user = LoginService.get_user_from_auth_db(db, email)
        
        if auth_user:
            # User exists in auth_users - authenticate locally
            if not verify_password(password, auth_user.password_hash):
                logger.warning(f"Invalid password for auth_user: {email}")
                return None
            
            # Convert AuthUser ORM object to dictionary for consistency
            return {
                "id": auth_user.id,
                "admin_user_id": auth_user.user_setup_id,
                "user_setup_id": auth_user.user_setup_id,  # Alias for compatibility
                "firstname": auth_user.firstname,
                "lastname": auth_user.lastname,
                "employee_id": auth_user.employee_id,
                "username": auth_user.username,
                "email": auth_user.email,
                "phone_number": auth_user.phone_number,
                "password_hash": auth_user.password_hash,
                "password_changed": auth_user.password_changed,
                "is_password_change": auth_user.is_password_change,
                "is_password_change_required": not auth_user.is_password_change,
                "status": auth_user.status,
                "start_date": auth_user.start_date,
                "end_date": auth_user.end_date,
                "tem_employee": auth_user.tem_employee,
                "department": auth_user.department,
                "division": auth_user.division,
                "job_code": auth_user.job_code,
                "manage_roles": auth_user.manage_roles or [],
                "default_dept": auth_user.default_dept,
                "reporting_to": auth_user.reporting_to,
                "entities": auth_user.entities,
                "default_entity": auth_user.default_entity,
                "view": auth_user.view,
                "dashboard_view": auth_user.dashboard_view,
                "created_at": auth_user.created_at,
                "updated_at": auth_user.updated_at,
                "source": "auth_db"  # Mark source for tracking
            }
        
        # Fallback: Try admin_service.usersetup_basic (first-time login)
        user = LoginService.get_user_from_admin_db(admin_db, email)

        if not user:
            logger.warning(f"User not found: {email}")
            return None

        if not verify_password(password, user["password_hash"]):
            logger.warning(f"Invalid password for user: {email}")
            return None

        user["source"] = "admin_db"  # Mark source for tracking
        return user

    @staticmethod
    def login(
        db: Session,
        admin_db: Session,
        login_data: LoginRequest,
        client_ip: str = None,
        user_agent: str = None
    ) -> LoginResponse:
        """
        Login user and generate tokens
        - Authenticates from auth_users table (if exists) or admin_service.usersetup_basic (first login)
        - Stores session in auth_service database
        - Returns 403 if password change is required
        """
        # Authenticate user (checks auth_users first, then admin_service)
        user = LoginService.authenticate_user(db, admin_db, login_data.email, login_data.password)

        if not user:
            # Log failed attempt in auth_service database
            LoginService._log_login_attempt(
                db, None, login_data.email, client_ip, user_agent, False, "invalid_credentials"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if user["status"] != "active":
            LoginService._log_login_attempt(
                db, user["id"], login_data.email, client_ip, user_agent, False, "account_inactive"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User account is {user['status']}. Please contact administrator.",
            )

        # Check if password change is required (first login)
        if user["is_password_change_required"]:
            # Log the attempt as successful but requiring password change
            LoginService._log_login_attempt(
                db, user["id"], login_data.email, client_ip, user_agent, True, "password_change_required"
            )

            # Raise HTTPException with password change required info
            # is_password_change value from database (false = needs to change password)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "is_password_change": user["is_password_change"],
                    "message": "First Time Login Detected - Please change your password",
                    "email": user["email"],
                    "show_popup": True,
                    "error_code": "FIRST_LOGIN_PASSWORD_CHANGE_REQUIRED",
                    "error_type": "validation_error",
                }
            )

        # Generate tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_data = {
            "user_id": str(user["id"]),
            "email": user["email"],
            "username": user["username"],
            "user_setup_id": str(user["user_setup_id"]) if user["user_setup_id"] else None,
        }

        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data, expires_delta=refresh_token_expires)

        # Create session in auth_service database
        session = LoginService._create_session(
            db, user["id"], access_token, refresh_token,
            client_ip, user_agent, login_data.device_fingerprint,
            refresh_token_expires
        )

        # Log successful attempt in auth_service database
        LoginService._log_login_attempt(
            db, user["id"], login_data.email, client_ip, user_agent, True, None
        )

        # Publish user login event (async, non-blocking)
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            def run_async_task(coro):
                """Helper to run async task in background"""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(coro)
                    loop.close()
                except Exception as e:
                    logger.warning(f"Background task error: {e}")
            
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(
                run_async_task,
                publish_user_login_event(
                    user_id=user["id"],
                    email=user["email"],
                    username=user.get("username"),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    login_method="password"
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish user_login event: {e}")

        # Publish session created event (async, non-blocking)
        try:
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(
                run_async_task,
                publish_session_created_event(
                    user_id=user["id"],
                    email=user["email"],
                    session_id=str(session.id),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    expires_at=session.expires_at
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish session_created event: {e}")

        # Publish user data sync event to admin-service (async, non-blocking)
        try:
            # Convert UUID fields to strings for event schema
            def uuid_to_str(value):
                """Convert UUID to string, or return None if None"""
                return str(value) if value is not None else None
            
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(
                run_async_task,
                publish_user_data_sync_event(
                    user_id=user["id"],
                    email=user["email"],
                    sync_action="login",
                    username=user.get("username"),
                    firstname=user.get("firstname"),
                    lastname=user.get("lastname"),
                    employee_id=user.get("employee_id"),
                    phone_number=user.get("phone_number"),
                    status=user.get("status", "active"),
                    department=uuid_to_str(user.get("department")),
                    division=uuid_to_str(user.get("division")),
                    job_code=uuid_to_str(user.get("job_code")),
                    manage_roles=user.get("manage_roles"),
                    default_dept=uuid_to_str(user.get("default_dept")),
                    reporting_to=uuid_to_str(user.get("reporting_to")),
                    entities=user.get("entities"),
                    default_entity=uuid_to_str(user.get("default_entity")),
                    last_login_at=datetime.now(timezone.utc),
                    last_login_ip=client_ip
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish user_data_sync event: {e}")

        # Prepare user info
        user_info = UserLoginInfo(
            id=user["id"],
            email=user["email"],
            username=user["username"],
            firstname=user["firstname"],
            lastname=user["lastname"],
            employee_id=user["employee_id"],
            status=user["status"],
            roles=user["manage_roles"] or [],
            admin_user_id=user["user_setup_id"]
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            is_password_change=user["is_password_change"],
            expires_in=int(access_token_expires.total_seconds()),
            session_id=session.id,
            user=user_info,
        )

    @staticmethod
    def change_password(
        db: Session,
        admin_db: Session,
        email: str,
        current_password: str,
        new_password: str,
        confirm_password: str
    ) -> ChangePasswordResponse:
        """
        Change user password
        Updates password in admin_service.usersetup_basic AND creates/updates auth_users record
        """
        # Validate passwords match
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "New password and confirmation do not match",
                    "error_code": "PASSWORD_MISMATCH",
                    "error_type": "validation_error",
                    "show_popup": True
                }
            )

        # Get user from admin_service
        admin_user = LoginService.get_user_from_admin_db(admin_db, email)
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "error_code": "USER_NOT_FOUND",
                    "error_type": "not_found_error",
                    "show_popup": True
                }
            )

        # Verify current password
        if not verify_password(current_password, admin_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Current password is incorrect",
                    "error_code": "INVALID_PASSWORD",
                    "error_type": "validation_error",
                    "show_popup": True
                }
            )

        # Generate new password hash
        new_hash = get_password_hash(new_password)
        
        # Update password in admin_service.usersetup_basic
        update_query = text("""
            UPDATE usersetup_basic
            SET password_hash = :password_hash,
                password_changed = :password_changed,
                is_password_change = true,
                updated_at = :updated_at
            WHERE email = :email
        """)

        admin_db.execute(update_query, {
            "password_hash": new_hash,
            "password_changed": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "email": email
        })
        admin_db.commit()

        # Sync to auth_users is handled by admin-service automatically
        # When data is posted to usersetup_basic, admin-service syncs to auth_users
        # via direct database connection (admin-service-postgres → clan-identity-postgres)
        logger.info(f"Password updated in admin_service for {email}")

        # Publish password changed event (async, non-blocking)
        try:
            from concurrent.futures import ThreadPoolExecutor
            
            def run_async_task(coro):
                """Helper to run async task in background"""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(coro)
                    loop.close()
                except Exception as e:
                    logger.warning(f"Background task error: {e}")
            
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(
                run_async_task,
                publish_user_password_changed_event(
                    user_id=admin_user["id"],
                    email=email,
                    changed_by="user",
                    is_first_login=admin_user.get("is_password_change_required", False)
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish user_password_changed event: {e}")

        # Publish user data sync event to admin-service (async, non-blocking)
        try:
            # Convert UUID fields to strings for event schema
            def uuid_to_str(value):
                """Convert UUID to string, or return None if None"""
                return str(value) if value is not None else None
            
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(
                run_async_task,
                publish_user_data_sync_event(
                    user_id=admin_user["id"],
                    email=email,
                    sync_action="password_change",
                    username=admin_user.get("username"),
                    firstname=admin_user.get("firstname"),
                    lastname=admin_user.get("lastname"),
                    employee_id=admin_user.get("employee_id"),
                    phone_number=admin_user.get("phone_number"),
                    status=admin_user.get("status", "active"),
                    department=uuid_to_str(admin_user.get("department")),
                    division=uuid_to_str(admin_user.get("division")),
                    job_code=uuid_to_str(admin_user.get("job_code")),
                    manage_roles=admin_user.get("manage_roles"),
                    default_dept=uuid_to_str(admin_user.get("default_dept")),
                    reporting_to=uuid_to_str(admin_user.get("reporting_to")),
                    entities=admin_user.get("entities"),
                    default_entity=uuid_to_str(admin_user.get("default_entity"))
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish user_data_sync event: {e}")

        return ChangePasswordResponse(
            message="The password is successfully changed. You will logout in 2 sec",
            email=email,
            show_popup=True,
            logout_in_seconds=2
        )

    @staticmethod
    def get_current_user_info(admin_db: Session, user_id: str) -> Dict[str, str]:
        """
        Get current authenticated user info from admin_service
        """
        query = text("""
            SELECT id, email, username, firstname, lastname, employee_id, status
            FROM usersetup_basic
            WHERE id = :user_id
        """)

        result = admin_db.execute(query, {"user_id": user_id}).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "user_id": str(result.id),
            "email": result.email,
            "username": result.username,
            "firstname": result.firstname or "",
            "lastname": result.lastname or "",
            "employee_id": result.employee_id or "",
            "status": result.status
        }

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        """
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        token_data_dict = {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "username": payload.get("username")
        }

        access_token = create_access_token(
            data=token_data_dict,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    @staticmethod
    def logout_user(db: Session, user_id: str, refresh_token: Optional[str] = None, all_sessions: bool = False) -> Dict[str, Any]:
        """
        Logout user - Invalidate user session(s) in auth_service database
        """
        # TODO: Implement actual session invalidation logic
        # This should:
        # 1. Find session(s) by user_id and optionally refresh_token
        # 2. Mark them as invalid/expired
        # 3. Return number of sessions revoked
        
        sessions_revoked = 1  # Placeholder
        
        return {
            "message": "Logged out successfully",
            "sessions_revoked": sessions_revoked
        }

    @staticmethod
    def _create_session(
        db: Session,
        user_id,
        access_token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        device_fingerprint: str,
        expires_delta: timedelta
    ) -> UserSession:
        """Create a new user session"""
        try:
            session = UserSession(
                user_id=user_id,
                access_token_hash=hash_token(access_token),
                refresh_token_hash=hash_token(refresh_token),
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                expires_at=datetime.now(timezone.utc) + expires_delta
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create session: {e}")
            logger.exception("Full exception:")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user session: {str(e)}"
            )

    @staticmethod
    def _log_login_attempt(
        db: Session,
        user_id,
        email: str,
        ip_address: str,
        user_agent: str,
        is_successful: bool,
        failure_reason: str
    ):
        """Log a login attempt"""
        try:
            attempt = LoginAttempt(
                user_id=user_id,
                email_or_username=email,
                ip_address=ip_address or "unknown",
                user_agent=user_agent,
                is_successful=is_successful,
                failure_reason=failure_reason
            )
            db.add(attempt)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log login attempt: {e}")
            # Don't raise - login attempt logging is not critical
