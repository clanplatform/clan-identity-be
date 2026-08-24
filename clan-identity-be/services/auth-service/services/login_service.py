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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging
import asyncio
import re

from core.audit_client import fire_audit_log

logger = logging.getLogger(__name__)

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

try:
    from database.redis_client import (
        cache_session, blacklist_token, remove_session, remove_all_user_sessions
    )
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

# Import sync service
try:
    from services.sync_service import SyncService
except ImportError:
    from app.services.sync_service import SyncService

# Import event publishers
try:
    from events.producers.auth_events import (
        publish_user_login_event,
        publish_user_password_changed_event,
        publish_user_data_sync_event,
        publish_session_created_event
    )
except Exception:
    try:
        from app.events.producers.auth_events import (
            publish_user_login_event,
            publish_user_password_changed_event,
            publish_user_data_sync_event,
            publish_session_created_event
        )
    except Exception:
        logger.warning("Event publishers not available - events will not be published")
        async def publish_user_login_event(*args, **kwargs): return False
        async def publish_user_password_changed_event(*args, **kwargs): return False
        async def publish_user_data_sync_event(*args, **kwargs): return False
        async def publish_session_created_event(*args, **kwargs): return False


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
    def _tenant_db_name_from_code(tenant_code: Optional[str]) -> Optional[str]:
        """
        Derive the tenant's dedicated DB name from tenant_code.

        admin-service no longer stores a tenant_db_name column — the name is
        computed as clan_platform_<slug(tenant_code)>, matching
        TenantDatabaseManager.make_db_name / _slugify there
        (slug = re.sub(r'[^a-z0-9_]', '_', code.lower())).
        """
        if not tenant_code or not str(tenant_code).strip():
            return None
        slug = re.sub(r"[^a-z0-9_]", "_", str(tenant_code).strip().lower())
        return f"clan_platform_{slug}"

    @staticmethod
    def _get_tenant_db_name(admin_db: Session, email: str, tenant_id: Optional[str] = None) -> Optional[str]:
        """
        Resolve the tenant's dedicated DB name, derived from tenants.tenant_code
        (admin-service no longer stores a tenant_db_name column — see
        Tenant.tenant_db_name / TenantDatabaseManager.make_db_name: the client's
        onboarding company.client_code becomes tenants.tenant_code, and the DB
        name is clan_platform_<slug(tenant_code)>).
        - tenant_id provided → look up tenant_code by tenant_id first.
        - Always fall back to the tenant whose owner_email matches the login
          email. This is what makes a tenant's FIRST login work: the client
          sends only email + password (no tenant_id), and the seeded admin
          exists only in the tenant DB until the first successful login
          eager-syncs it to auth_users. tenants.owner_email is the admin's
          actual login credential (see admin-service
          OnboardingCompany.owner_email) — tenants.contact_email is just the
          tenant's general business contact, not a login field, and is
          deliberately NOT checked here: it can collide with another tenant's
          owner_email and resolve to the wrong tenant DB.
        Returns None for master-DB users / unknown emails.
        """
        try:
            # 1. Try by tenant_id when supplied
            if tenant_id:
                logger.info("[TENANT_LOOKUP] Searching by tenant_id=%s", tenant_id)
                row = admin_db.execute(
                    text("SELECT tenant_code FROM tenants WHERE tenant_id = :tid AND is_active = true"),
                    {"tid": str(tenant_id)},
                ).fetchone()
                db_name = LoginService._tenant_db_name_from_code(row.tenant_code if row else None)
                if db_name:
                    logger.info("[TENANT_LOOKUP] Derived tenant_db_name=%s from tenant_code", db_name)
                    return db_name
                logger.warning("[TENANT_LOOKUP] tenant_id=%s not found, falling back to email lookup", tenant_id)

            # 2. Fall back to the tenant whose owner_email (the actual admin
            # login email) matches (also the no-tenant_id path).
            row = admin_db.execute(
                text("SELECT tenant_code FROM tenants WHERE owner_email = :email AND is_active = true"),
                {"email": email},
            ).fetchone()
            db_name = LoginService._tenant_db_name_from_code(row.tenant_code if row else None)
            if db_name:
                logger.info("[TENANT_LOOKUP] Derived tenant_db_name=%s from tenant_code via owner_email", db_name)
                return db_name

            logger.info("[TENANT_LOOKUP] No tenant match for email=%s tenant_id=%s (master-DB user?)", email, tenant_id)
            return None
        except Exception as exc:
            logger.warning("[TENANT_LOOKUP] Error for email=%s: %s", email, exc)
            return None

    @staticmethod
    def _get_tenant_redirect_url(admin_db: Session, tenant_id: Optional[str]) -> Optional[str]:
        """
        Resolve the tenant's application URL from tenants.allowed_origins
        in the master admin DB (first entry — the tenant's frontend app).
        Returns None for master users or when no origin is configured.
        """
        if not tenant_id:
            return None
        try:
            row = admin_db.execute(
                text(
                    "SELECT allowed_origins FROM tenants "
                    "WHERE tenant_id = :tid AND is_active = true"
                ),
                {"tid": str(tenant_id)},
            ).fetchone()
            if row and row.allowed_origins:
                redirect_url = row.allowed_origins[0]
                logger.info("[TENANT_REDIRECT] tenant %s → %s", tenant_id, redirect_url)
                return redirect_url
            logger.info("[TENANT_REDIRECT] tenant %s has no allowed_origins configured", tenant_id)
            return None
        except Exception as exc:
            logger.warning("[TENANT_REDIRECT] Lookup failed for tenant %s: %s", tenant_id, exc)
            try:
                admin_db.rollback()
            except Exception:
                pass
            return None

    @staticmethod
    def _get_master_redirect_url(admin_db: Session, email: str) -> Optional[str]:
        """
        Resolve a master-DB user's application URL from
        usersetup_basic.allowed_origins in the master admin DB (first entry).
        Master users have no tenant row, so their redirect target is stored
        per user — the counterpart of tenants.allowed_origins for tenant users.
        """
        try:
            row = admin_db.execute(
                text("SELECT allowed_origins FROM usersetup_basic WHERE email = :email"),
                {"email": email},
            ).fetchone()
            if row and row.allowed_origins:
                redirect_url = row.allowed_origins[0]
                logger.info("[MASTER_REDIRECT] %s → %s", email, redirect_url)
                return redirect_url
            logger.info("[MASTER_REDIRECT] %s has no allowed_origins configured", email)
            return None
        except Exception as exc:
            logger.warning("[MASTER_REDIRECT] Lookup failed for %s: %s", email, exc)
            try:
                admin_db.rollback()
            except Exception:
                pass
            return None

    @staticmethod
    def _query_usersetup_basic(db: Session, email: str) -> Optional[Dict[str, Any]]:
        """Execute usersetup_basic lookup against a given SQLAlchemy session."""
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
                    ub.can_change_password,
                    ub.status,
                    ub.role_id,
                    ub.entity_id,
                    ub.user_group_id,
                    ub.send_invite_email,
                    ub.allowed_origins,
                    ub.created_at,
                    ub.updated_at,
                    ub.tenant_id
                FROM usersetup_basic ub
                WHERE ub.email = :email
            """)
            result = db.execute(query, {"email": email}).fetchone()
            if not result:
                return None
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
                "can_change_password": result.can_change_password,
                "status": result.status,
                "role_id": result.role_id,
                "entity_id": result.entity_id,
                "user_group_id": result.user_group_id,
                "send_invite_email": result.send_invite_email,
                "allowed_origins": result.allowed_origins,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "tenant_id": result.tenant_id,
            }
        except Exception as exc:
            logger.error("Error querying usersetup_basic: %s", exc)
            try:
                db.rollback()
            except Exception:
                pass
            return None

    @staticmethod
    def get_user_from_auth_service(db: Session, email: str) -> Optional[AuthUser]:
        """
        Get user from auth_users table by email.
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
    def _resolve_tenant_id(db: Session, email: str) -> Optional[str]:
        """
        Resolve a user's tenant_id by email from the local auth_users directory.
        Every user is eager-synced into auth_users at provisioning, so this is the
        single source of truth for tenant routing — the client never sends tenant_id.
        Returns the tenant UUID string, or None for master-DB users / unknown emails.
        """
        auth_user = LoginService.get_user_from_auth_service(db, email)
        if auth_user and auth_user.tenant_id:
            return str(auth_user.tenant_id)
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
                # Role assignment
                role_id=admin_user_data.get("role_id"),
                # Branch / location
                entity_id=admin_user_data.get("entity_id"),
                # Tenant
                tenant_id=admin_user_data.get("tenant_id"),
                # User group + invite flag + allowed origins
                user_group_id=admin_user_data.get("user_group_id"),
                send_invite_email=admin_user_data.get("send_invite_email", False),
                allowed_origins=admin_user_data.get("allowed_origins"),
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
    def get_user_from_admin_db(
        admin_db: Session,
        email: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get user from usersetup_basic by email.

        If tenant_id is provided (or the email matches a tenant's owner_email),
        queries that tenant's dedicated database.  Falls back to the master DB.

        usersetup_basic.password_hash is the single source of truth for login —
        admin-service's create_onboarding seeds the owner's row with the EXACT
        SAME hash as tenants.owner_password_hash (not a second, independently
        salted hash of the same password), so no override is needed here.
        """
        tenant_db_name = LoginService._get_tenant_db_name(admin_db, email, tenant_id)

        if tenant_db_name:
            admin_url = settings.ADMIN_DATABASE_URL
            tenant_url = admin_url.rsplit("/", 1)[0] + "/" + tenant_db_name
            logger.info("[USER_LOOKUP] Connecting to tenant DB: %s", tenant_db_name)
            tenant_engine = None
            try:
                tenant_engine = create_engine(tenant_url, pool_pre_ping=True, pool_size=2, max_overflow=3)
                TenantSession = sessionmaker(bind=tenant_engine)
                tenant_db = TenantSession()
                try:
                    user = LoginService._query_usersetup_basic(tenant_db, email)
                    if user:
                        logger.info("[USER_LOOKUP] User found in tenant DB %s — pw_hash prefix: %s",
                                    tenant_db_name, (user.get("password_hash") or "")[:20])
                        return user
                    logger.warning("[USER_LOOKUP] User %s NOT found in tenant DB %s", email, tenant_db_name)
                finally:
                    tenant_db.close()
            except Exception as exc:
                logger.warning("[USER_LOOKUP] Error querying tenant DB %s: %s", tenant_db_name, exc)
            finally:
                if tenant_engine:
                    tenant_engine.dispose()

        # Fallback: master DB
        logger.info("[USER_LOOKUP] Falling back to master DB for email=%s", email)
        user = LoginService._query_usersetup_basic(admin_db, email)
        if user:
            logger.info("[USER_LOOKUP] User found in master DB")
        else:
            logger.warning("[USER_LOOKUP] User %s NOT found in master DB either", email)
        return user

    @staticmethod
    def authenticate_user(
        db: Session,
        admin_db: Session,
        email: str,
        password: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate user by email and password.
        Priority: auth_users table → master usersetup_basic (fallback for first login).
        The user's tenant_id is taken from the resolved record — never supplied by the
        caller — and is carried onward only through the JWT.
        """
        # First, try to authenticate from auth_users table (local, faster)
        auth_user = LoginService.get_user_from_auth_service(db, email)

        if auth_user:
            if not LoginService._smart_verify(password, auth_user.password_hash):
                logger.warning(f"Invalid password for auth_user: {email}")
                return None
            return {
                "id": auth_user.id,
                "admin_user_id": auth_user.user_setup_id,
                "user_setup_id": auth_user.user_setup_id,
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
                "can_change_password": getattr(auth_user, "can_change_password", True),
                "status": auth_user.status,
                "role_id": auth_user.role_id,
                "entity_id": auth_user.entity_id,
                "created_at": auth_user.created_at,
                "updated_at": auth_user.updated_at,
                "tenant_id": auth_user.tenant_id,
                "source": "auth_service",
            }

        # Fallback: master DB usersetup_basic. Tenant users are eager-synced into
        # auth_users, so only master-DB users (tenant_id NULL) reach here — no tenant
        # routing is required.
        user = LoginService.get_user_from_admin_db(admin_db, email)

        if not user:
            logger.warning("[AUTH] User not found anywhere for email=%s", email)
            return None

        pw_match = LoginService._smart_verify(password, user["password_hash"])
        logger.info("[AUTH] Password verify for %s → %s (hash prefix: %s)",
                    email, pw_match, (user.get("password_hash") or "")[:20])
        if not pw_match:
            logger.warning("[AUTH] Password mismatch for email=%s", email)
            return None

        user["source"] = "admin_db"
        return user

    @staticmethod
    def _smart_verify(password_input: str, stored_hash: str) -> bool:
        """
        Accept either a plaintext password or the bcrypt hash itself.
        - If the input starts with a bcrypt prefix ($2a$, $2b$, $2y$),
          compare it directly against the stored hash (hash == hash).
        - Otherwise treat it as plaintext and run bcrypt verify.
        """
        if password_input.startswith(("$2a$", "$2b$", "$2y$")):
            return password_input == stored_hash
        return verify_password(password_input, stored_hash)

    @staticmethod
    def login(
        db: Session,
        admin_db: Session,
        login_data: LoginRequest,
        client_ip: str = None,
        user_agent: str = None,
    ) -> LoginResponse:
        """
        Login user and generate tokens
        - Authenticates from auth_users table (if exists) or tenant/master usersetup_basic (first login)
        - Automatically syncs latest user data from admin_service to auth_users on every login
        - Stores session in auth_service database
        - Returns 403 if password change is required
        """
        # Authenticate user (checks auth_users first, then master DB).
        # tenant_id is never taken from the request — it is derived from the resolved
        # user record below and propagated onward only through the JWT.
        user = LoginService.authenticate_user(
            db, admin_db, login_data.email, login_data.password,
        )

        if not user:
            # Log failed attempt in auth_service database
            LoginService._log_login_attempt(
                db, None, login_data.email, client_ip, user_agent, False, "invalid_credentials"
            )
            fire_audit_log(
                action="LOGIN_FAILED",
                object_type="AuthUser",
                new_values={"email": login_data.email, "reason": "invalid_credentials"},
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # tenant_id is derived from the authenticated record (auth_users / DB),
        # never from the request; it is propagated onward only through the JWT.
        tenant_id_str = str(user["tenant_id"]) if user.get("tenant_id") else None

        # AUTOMATIC SYNC: Sync latest user data from tenant/master DB to auth_users
        try:
            admin_user = LoginService.get_user_from_admin_db(admin_db, login_data.email, tenant_id_str)
            if admin_user:
                logger.info(f"Auto-syncing user data from admin_service for {login_data.email}")
                synced_user = SyncService.sync_user_from_admin_data(db, admin_user)
                if synced_user:
                    logger.info(f"Successfully synced user {login_data.email} to auth_users")
                    # Update user dict with synced data to ensure we have latest info
                    user["id"] = synced_user.id
                    user["user_setup_id"] = synced_user.user_setup_id
                else:
                    logger.warning(f"Failed to sync user {login_data.email}, continuing with existing data")
        except Exception as e:
            # Log the error but don't fail login - sync is non-critical
            logger.warning(f"Auto-sync failed for {login_data.email}: {e}")
            logger.exception("Sync exception (non-critical):")

        # Check if user is active
        if user["status"] != "active":
            LoginService._log_login_attempt(
                db, user["id"], login_data.email, client_ip, user_agent, False, "account_inactive",
                tenant_id=user.get("tenant_id"),
            )
            fire_audit_log(
                action="LOGIN_FAILED",
                object_type="AuthUser",
                object_id=str(user["id"]),
                tenant_id=str(user["tenant_id"]) if user.get("tenant_id") else None,
                user_id=str(user["id"]),
                new_values={"email": login_data.email, "reason": "account_inactive", "status": user["status"]},
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User account is {user['status']}. Please contact administrator.",
            )

        # Check if password change is required (first login).
        # Applies only when can_change_password is enabled — users with
        # can_change_password=False log straight in and are redirected to
        # their tenant application.
        if user.get("can_change_password", True) and user["is_password_change_required"]:
            # Log the attempt as successful but requiring password change
            LoginService._log_login_attempt(
                db, user["id"], login_data.email, client_ip, user_agent, True, "password_change_required",
                tenant_id=user.get("tenant_id"),
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
            "tenant_id": str(user["tenant_id"]) if user.get("tenant_id") else None,
        }

        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data, expires_delta=refresh_token_expires)

        # Create session in auth_service database
        session = LoginService._create_session(
            db, user["id"], access_token, refresh_token,
            client_ip, user_agent, refresh_token_expires,
        )

        # Log successful attempt in auth_service database
        LoginService._log_login_attempt(
            db, user["id"], login_data.email, client_ip, user_agent, True, None,
            tenant_id=user.get("tenant_id"),
            session_id=session.id,
        )
        fire_audit_log(
            action="LOGIN",
            object_type="AuthUser",
            object_id=str(user["id"]),
            tenant_id=tenant_id_str,
            user_id=str(user["id"]),
            session_id=str(session.id),
            new_values={"email": user["email"], "username": user.get("username")},
            ip_address=client_ip,
            user_agent=user_agent,
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
                    role_id=uuid_to_str(user.get("role_id")),
                    entity_id=user.get("entity_id"),  # list of UUID; pydantic serializes each
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
            role_id=user.get("role_id"),
            entity_id=user.get("entity_id"),
            admin_user_id=user["user_setup_id"],
            # tenant_id is NOT surfaced to the client — it travels in the JWT only.
        )

        # Tenant users land in their application (tenants.allowed_origins);
        # master users in theirs (usersetup_basic.allowed_origins).
        if tenant_id_str:
            redirect_to = LoginService._get_tenant_redirect_url(admin_db, tenant_id_str)
        else:
            redirect_to = LoginService._get_master_redirect_url(admin_db, login_data.email)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            is_password_change=user["is_password_change"],
            expires_in=int(access_token_expires.total_seconds()),
            session_id=session.id,
            user=user_info,
            redirect_to=redirect_to,
        )

    @staticmethod
    def change_password(
        db: Session,
        admin_db: Session,
        email: str,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> ChangePasswordResponse:
        """
        Change user password
        Updates password in admin_service.usersetup_basic AND creates/updates auth_users record.
        The target tenant DB is resolved from the local auth_users directory by email,
        not supplied by the caller.
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

        # Resolve the user's tenant from the local auth_users directory (eager-synced).
        # None ⇒ master-DB user. tenant_id is never supplied by the client.
        tenant_id = LoginService._resolve_tenant_id(db, email)

        # Get user from tenant DB or master DB
        admin_user = LoginService.get_user_from_admin_db(admin_db, email, tenant_id)
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

        # Users with can_change_password=False are not allowed to change
        # their password — they log in directly with the assigned password.
        if not admin_user.get("can_change_password", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Password change is not allowed for this account",
                    "error_code": "PASSWORD_CHANGE_NOT_ALLOWED",
                    "error_type": "validation_error",
                    "show_popup": True
                }
            )

        # Verify current password — accepts the plaintext password or the
        # stored bcrypt hash itself, same as login's _smart_verify.
        if not LoginService._smart_verify(current_password, admin_user["password_hash"]):
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

        # Resolve which DB to update (tenant DB or master DB)
        update_query = text("""
            UPDATE usersetup_basic
            SET password_hash = :password_hash,
                password_changed = :password_changed,
                is_password_change = true,
                updated_at = :updated_at
            WHERE email = :email
        """)
        update_params = {
            "password_hash": new_hash,
            "password_changed": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "email": email,
        }

        tenant_db_name = LoginService._get_tenant_db_name(admin_db, email, tenant_id)
        if tenant_db_name:
            admin_url = settings.ADMIN_DATABASE_URL
            tenant_url = admin_url.rsplit("/", 1)[0] + "/" + tenant_db_name
            tenant_engine = create_engine(tenant_url, pool_pre_ping=True, pool_size=2, max_overflow=3)
            try:
                TenantSession = sessionmaker(bind=tenant_engine)
                t_db = TenantSession()
                try:
                    t_db.execute(update_query, update_params)
                    t_db.commit()
                    logger.info("Password updated in tenant DB %s for %s", tenant_db_name, email)
                finally:
                    t_db.close()
            finally:
                tenant_engine.dispose()
        else:
            admin_db.execute(update_query, update_params)
            admin_db.commit()
            logger.info("Password updated in master DB for %s", email)

        # Keep tenants.owner_password_hash in sync when this email is a tenant
        # owner. Not required for login (usersetup_basic.password_hash above
        # is the actual source of truth there), but the two are seeded as the
        # same value at onboarding (see create_onboarding) and should stay
        # that way rather than silently drifting after a password change.
        try:
            result = admin_db.execute(
                text(
                    "UPDATE tenants SET owner_password_hash = :password_hash "
                    "WHERE owner_email = :email AND is_active = true"
                ),
                {"password_hash": new_hash, "email": email},
            )
            admin_db.commit()
            if result.rowcount:
                logger.info("owner_password_hash updated in tenants for %s", email)
        except Exception as exc:
            admin_db.rollback()
            logger.warning("Failed to sync owner_password_hash for %s: %s", email, exc)

        # AUTOMATIC SYNC: Sync updated user data to auth_users after password change
        try:
            logger.info(f"Auto-syncing user data after password change for {email}")
            updated_admin_user = LoginService.get_user_from_admin_db(admin_db, email, tenant_id)
            if updated_admin_user:
                synced_user = SyncService.sync_user_from_admin_data(db, updated_admin_user)
                if synced_user:
                    logger.info(f"Successfully synced user {email} to auth_users after password change")
                else:
                    logger.warning(f"Failed to sync user {email} after password change")
        except Exception as e:
            # Log the error but don't fail password change - sync is non-critical
            logger.warning(f"Auto-sync failed after password change for {email}: {e}")
            logger.exception("Sync exception (non-critical):")

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
                    role_id=uuid_to_str(admin_user.get("role_id")),
                    entity_id=admin_user.get("entity_id")  # list of UUID; pydantic serializes each
                )
            )
        except Exception as e:
            logger.warning(f"Failed to publish user_data_sync event: {e}")

        fire_audit_log(
            action="PASSWORD_CHANGE",
            object_type="AuthUser",
            object_id=str(admin_user["id"]),
            tenant_id=str(admin_user["tenant_id"]) if admin_user.get("tenant_id") else None,
            user_id=str(admin_user["id"]),
            new_values={"email": email, "changed_by": "user"},
        )
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
            "username": payload.get("username"),
            "tenant_id": payload.get("tenant_id"),
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
    def logout_user(
        db: Session,
        user_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        all_sessions: bool = False
    ) -> Dict[str, Any]:
        """Revoke session(s) in PostgreSQL and blacklist the access token in Redis."""
        sessions_revoked = 0

        try:
            if all_sessions:
                # Revoke all active sessions for this user in PostgreSQL
                sessions = (
                    db.query(UserSession)
                    .filter(
                        UserSession.user_id == user_id,
                        UserSession.is_active == True,
                        UserSession.is_revoked == False,
                    )
                    .all()
                )
                for s in sessions:
                    s.is_active = False
                    s.is_revoked = True
                    s.revoked_reason = "logout"
                    s.revoked_at = datetime.now(timezone.utc)
                db.commit()
                sessions_revoked = len(sessions)

                # Remove all sessions from Redis cache
                if REDIS_AVAILABLE:
                    remove_all_user_sessions(str(user_id))

            elif refresh_token:
                refresh_hash = hash_token(refresh_token)
                session = (
                    db.query(UserSession)
                    .filter(
                        UserSession.user_id == user_id,
                        UserSession.refresh_token_hash == refresh_hash,
                        UserSession.is_active == True,
                        UserSession.is_revoked == False,
                    )
                    .first()
                )
                if session:
                    session.is_active = False
                    session.is_revoked = True
                    session.revoked_reason = "logout"
                    session.revoked_at = datetime.now(timezone.utc)
                    db.commit()
                    sessions_revoked = 1

                    # Remove from Redis cache
                    if REDIS_AVAILABLE:
                        remove_session(str(session.id), str(user_id))

            else:
                # No refresh token — revoke the most recent active session
                session = (
                    db.query(UserSession)
                    .filter(
                        UserSession.user_id == user_id,
                        UserSession.is_active == True,
                        UserSession.is_revoked == False,
                    )
                    .order_by(UserSession.created_at.desc())
                    .first()
                )
                if session:
                    session.is_active = False
                    session.is_revoked = True
                    session.revoked_reason = "logout"
                    session.revoked_at = datetime.now(timezone.utc)
                    db.commit()
                    sessions_revoked = 1

                    if REDIS_AVAILABLE:
                        remove_session(str(session.id), str(user_id))

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to revoke session(s) for user {user_id}: {e}")

        # Blacklist the current access token so it's immediately invalid
        if access_token and REDIS_AVAILABLE:
            access_ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            blacklist_token(hash_token(access_token), ttl=access_ttl)

        auth_user = db.query(AuthUser).filter(AuthUser.id == user_id).first()
        fire_audit_log(
            action="LOGOUT",
            object_type="AuthUser",
            object_id=str(user_id),
            tenant_id=str(auth_user.tenant_id) if auth_user and auth_user.tenant_id else None,
            user_id=str(user_id),
            new_values={"sessions_revoked": sessions_revoked, "all_sessions": all_sessions},
        )
        return {
            "message": "Logged out successfully",
            "sessions_revoked": sessions_revoked,
        }

    @staticmethod
    def _create_session(
        db: Session,
        user_id,
        access_token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
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
                expires_at=datetime.now(timezone.utc) + expires_delta
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Cache session in Redis for fast lookup
            if REDIS_AVAILABLE:
                ttl = int(expires_delta.total_seconds())
                cache_session(
                    session_id=str(session.id),
                    user_id=str(user_id),
                    data={
                        "session_id": str(session.id),
                        "user_id": str(user_id),
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "expires_at": session.expires_at.isoformat(),
                        "is_active": True,
                    },
                    ttl=ttl,
                )

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
        failure_reason: str,
        tenant_id=None,
        session_id=None,
    ):
        """
        Log a login attempt, enriched server-side with device (parsed from
        User-Agent), network (ip_type/geo/ISP when GeoIP is configured),
        anonymizer flags, and a rule-based risk score.
        """
        # Enrichment is best-effort — never lose the attempt row over it
        try:
            from core.login_enrichment import enrich_login_attempt
            enrichment = enrich_login_attempt(ip_address, user_agent, is_successful)
        except Exception as exc:
            logger.warning(f"Login enrichment unavailable: {exc}")
            enrichment = {}

        try:
            attempt = LoginAttempt(
                user_id=user_id,
                tenant_id=tenant_id,
                session_id=session_id,
                email_or_username=email,
                ip_address=ip_address or "unknown",
                user_agent=user_agent,
                is_successful=is_successful,
                failure_reason=failure_reason,
                **enrichment,
            )
            db.add(attempt)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log login attempt: {e}")
            # Don't raise - login attempt logging is not critical
