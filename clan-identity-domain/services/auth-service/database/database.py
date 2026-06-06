"""
Auth Service Database Configuration
Connects to:
1. auth_service PostgreSQL database (for sessions, login_attempts, otps)
2. admin_service PostgreSQL database (for user authentication from usersetup_basic)
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import logging

try:
    from core.config import settings
except ImportError:
    from app.core.config import settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models - MUST be defined before models import it
Base = declarative_base()

# Metadata for database operations
metadata = MetaData()

# ============================================================================
# Auth Service Database Engine (auth_service DB)
# ============================================================================
if settings.DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================================================
# Admin Service Database Engine (admin_service DB - for user lookup)
# ============================================================================
admin_engine = create_engine(
    settings.ADMIN_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10
)

AdminSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_engine)


def get_db() -> Generator:
    """
    Dependency to get database session for auth_service database
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_db() -> Generator:
    """
    Dependency to get database session for admin_service database
    Used for reading user data from usersetup_basic table
    """
    db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables
    Call this on application startup to create all tables
    """
    # Import all models to register them with Base.metadata
    try:
        from models.user import AuthUser
        from models.otp import OTP
        from models.session import Session
        from models.login_attempt import LoginAttempt
    except ImportError:
        try:
            from app.models.user import AuthUser
            from app.models.otp import OTP
            from app.models.session import Session
            from app.models.login_attempt import LoginAttempt
        except ImportError:
            logger.warning("Could not import models - tables may not be created")
            return

    logger.info(f"Connecting to auth_service database: {settings.POSTGRES_DB}")
    logger.info(f"Database URL: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

    # Create all tables in auth_service database
    Base.metadata.create_all(bind=engine)

    # Log created tables
    logger.info(f"Tables in auth_service: {list(Base.metadata.tables.keys())}")

    # Verify admin_service connection
    try:
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected to admin_service database: {settings.ADMIN_DB}")
    except Exception as e:
        logger.warning(f"Could not connect to admin_service database: {e}")

