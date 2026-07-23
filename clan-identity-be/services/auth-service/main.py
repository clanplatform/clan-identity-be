"""
Auth Service - Main Application Entry Point
Handles user authentication with separate auth_service database
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import os

from core.config import settings

# Configure logging FIRST before using logger
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from database.connection import init_db
except ImportError:
    try:
        from app.db.database import init_db
    except ImportError:
        def init_db():
            logger.warning("Database initialization not available")
            pass

# Try to import routers
login = None
sync = None
auth_users = None

try:
    from app.api.routes.v1.login import router as login_router
    login = type('obj', (object,), {'router': login_router})()
    logger.info("Successfully imported login routes")
except ImportError as e:
    logger.error(f"Cannot import login routes: {e}")

try:
    from app.api.routes.v1.sync import router as sync_router
    sync = type('obj', (object,), {'router': sync_router})()
    logger.info("Successfully imported sync routes")
except ImportError as e:
    logger.error(f"Cannot import sync routes: {e}")

try:
    from app.api.routes.v1.auth_users import router as auth_users_router
    auth_users = type('obj', (object,), {'router': auth_users_router})()
    logger.info("Successfully imported auth_users routes")
except ImportError as e:
    logger.error(f"Cannot import auth_users routes: {e}")

# Import encryption components
encryption_manager = None
if settings.PAYLOAD_ENCRYPTION_ENABLED:
    try:
        import sys
        # Add libs path to Python path
        libs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "libs"))
        if libs_path not in sys.path:
            sys.path.insert(0, libs_path)
        
        from identity_shared.encryption import create_encryption_from_env
        from identity_shared.encryption_middleware import setup_encryption_middleware
        
        # Create encryption manager with service-specific keys
        encryption_manager = create_encryption_from_env(
            default_key_var="PAYLOAD_ENCRYPTION_KEY",
            service_keys={
                "auth": "AUTH_SERVICE_ENCRYPTION_KEY",
                "default": "PAYLOAD_ENCRYPTION_KEY"
            }
        )
        
        if encryption_manager:
            logger.info("✓ Encryption manager initialized successfully")
        else:
            logger.warning("⚠ Encryption enabled but no keys configured")
            
    except ImportError as e:
        logger.error(f"Failed to import encryption modules: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
else:
    logger.info("Encryption is disabled (PAYLOAD_ENCRYPTION_ENABLED=false)")

# Try to import Redis client
try:
    from database.redis_client import get_redis, close_redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    def get_redis(): return None
    def close_redis(): pass

# Try to import Kafka client
try:
    from events.kafka_client import get_producer, close_producer, KAFKA_ENABLED
    KAFKA_AVAILABLE = True
except Exception as e:
    try:
        from app.events.kafka_client import get_producer, close_producer, KAFKA_ENABLED
        KAFKA_AVAILABLE = True
    except Exception as e2:
        logger.warning(f"Kafka client not available: {e}, {e2}")
        KAFKA_AVAILABLE = False
        KAFKA_ENABLED = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.POSTGRES_DB}")

    # Initialize database tables
    try:
        init_db()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Initialize Redis connection
    if REDIS_AVAILABLE:
        r = get_redis()
        if r:
            logger.info("Redis initialized successfully")
        else:
            logger.warning("Redis unavailable — session cache and token blacklist disabled")

    # Initialize Kafka producer
    if KAFKA_AVAILABLE and KAFKA_ENABLED:
        try:
            producer = await get_producer()
            logger.info("Kafka producer initialized successfully")
            app.state.kafka_enabled = True
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            app.state.kafka_enabled = False
    else:
        logger.info("Kafka is disabled - events will not be published")
        app.state.kafka_enabled = False

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")

    # Close Redis connection
    if REDIS_AVAILABLE:
        close_redis()
        logger.info("Redis connection closed")

    # Close Kafka producer
    if KAFKA_AVAILABLE and KAFKA_ENABLED:
        try:
            await close_producer()
            logger.info("Kafka producer closed successfully")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    Auth Service API - Handles user authentication
    
    ## Features
    - User login with email and password
    - JWT token generation and validation
    - Password change and reset
    - Session management
    - Login attempt tracking
    
    ## Database
    Uses separate `auth_service` PostgreSQL database for:
    - auth_users: User authentication credentials
    - sessions: Active user sessions
    - otps: One-time passwords for verification
    - login_attempts: Login audit trail
    """,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)


# --- Dynamic CORS — origins from clients.allowed_origins (admin DB) --------
# Validated against the centralized clients table so no redeploy is needed
# when onboarding a new tenant. CORS_ORIGINS env var is still honoured as a
# static fallback (useful for local dev / shared tooling origins).
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.dynamic_cors import DynamicCORSMiddleware as _DynamicCORSMiddleware

    _admin_engine = create_engine(
        settings.ADMIN_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
    )
    _AdminSession = sessionmaker(bind=_admin_engine)

    # Reuse the Redis client from the existing Redis connection if available.
    _redis_client = None
    try:
        import redis as _redis_lib
        _redis_client = _redis_lib.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _redis_client.ping()
    except Exception:
        _redis_client = None

    app.add_middleware(
        _DynamicCORSMiddleware,
        session_factory=_AdminSession,
        redis_client=_redis_client,
    )
    logger.info("Dynamic CORS middleware enabled (admin DB + Redis cache)")
except Exception as _cors_err:
    logger.warning("Dynamic CORS setup failed (%s) — no CORS headers will be set", _cors_err)
# ---------------------------------------------------------------------------

# Add CORS middleware
# Add encryption middleware (must be added after CORS)
if settings.PAYLOAD_ENCRYPTION_ENABLED and encryption_manager:
    try:
        from identity_shared.encryption_middleware import setup_encryption_middleware
        
        setup_encryption_middleware(
            app=app,
            encryption_manager=encryption_manager,
            config={
                "enabled": True,
                "exclude_paths": settings.ENCRYPTION_EXCLUDED_PATHS,
                "service_name": "auth",
                "require_encryption": settings.ENCRYPTION_REQUIRE_ENCRYPTED_REQUESTS
            }
        )
        logger.info("✓ Encryption middleware enabled for production")
    except Exception as e:
        logger.error(f"Failed to setup encryption middleware: {e}")
else:
    if settings.PAYLOAD_ENCRYPTION_ENABLED:
        logger.warning("⚠ Encryption enabled but middleware not configured")


# Include routers
if login and hasattr(login, 'router'):
    app.include_router(
        login.router,
        prefix=f"{settings.API_V1_STR}/login"
    )
else:
    logger.error("Login router not available - API endpoints will not be registered")

if sync and hasattr(sync, 'router'):
    app.include_router(
        sync.router,
        prefix=f"{settings.API_V1_STR}/sync",
        tags=["Sync"]
    )
    logger.info("Sync router registered at /sync")
else:
    logger.warning("Sync router not available - sync endpoints will not be registered")

if auth_users and hasattr(auth_users, 'router'):
    app.include_router(
        auth_users.router,
        prefix=f"{settings.API_V1_STR}/auth/users",
        tags=["Auth", "Sync"]
    )
    logger.info("Auth users router registered at /auth/users (admin-service compatible)")
else:
    logger.warning("Auth users router not available - admin-service sync endpoint will not be registered")



@app.get("/")
async def root():
    """Root endpoint - Service health check"""
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "database": settings.POSTGRES_DB
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        from database.connection import engine, admin_engine
    except ImportError:
        try:
            from app.db.database import engine, admin_engine
        except ImportError:
            return {
                "status": "unhealthy",
                "auth_database": "not configured",
                "admin_database": "not configured",
                "kafka": "disabled",
                "service": settings.PROJECT_NAME
            }
    
    from sqlalchemy import text

    try:
        # Test auth_service database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        auth_service_status = "healthy"
    except Exception as e:
        auth_service_status = f"unhealthy: {str(e)}"

    try:
        # Test admin_service database connection
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        admin_db_status = "healthy"
    except Exception as e:
        admin_db_status = f"unhealthy: {str(e)}"

    # Check Redis status
    if REDIS_AVAILABLE:
        try:
            r = get_redis()
            if r:
                r.ping()
                redis_status = "healthy"
            else:
                redis_status = "disabled"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
    else:
        redis_status = "unavailable"

    # Check Kafka status
    if KAFKA_AVAILABLE and KAFKA_ENABLED:
        try:
            from app.events.kafka_client import check_kafka_health
            kafka_healthy = await check_kafka_health()
            kafka_status = "healthy" if kafka_healthy else "unhealthy"
        except Exception as e:
            kafka_status = f"unhealthy: {str(e)}"
    else:
        kafka_status = "disabled"

    return {
        "status": "healthy",
        "auth_database": auth_service_status,
        "admin_database": admin_db_status,
        "redis": redis_status,
        "kafka": kafka_status,
        "service": settings.PROJECT_NAME
    }


@app.get("/.well-known/jwks.json", tags=["Authentication"])
async def jwks_endpoint():
    """JWKS — RSA public keys the API gateway (Envoy) uses to verify RS256 tokens."""
    try:
        from core.jwks import jwks as _jwks
    except ImportError:
        from app.core.jwks import jwks as _jwks
    return _jwks()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.DEBUG
    )

