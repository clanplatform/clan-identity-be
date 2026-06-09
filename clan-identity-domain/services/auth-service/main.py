"""
Auth Service - Main Application Entry Point
Handles user authentication with separate auth_service database
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from core.config import settings
try:
    from database.connection import init_db
except ImportError:
    try:
        from app.db.database import init_db
    except ImportError:
        def init_db():
            logger.warning("Database initialization not available")
            pass

try:
    from app.api.routes.v1 import login
except ImportError:
    try:
        from app.api.routes import login
    except ImportError:
        logger.error("Cannot import login routes")
        login = None

# Try to import Kafka client
try:
    from events.kafka_client import get_producer, close_producer, KAFKA_ENABLED
    KAFKA_AVAILABLE = True
except ImportError as e:
    try:
        from app.events.kafka_client import get_producer, close_producer, KAFKA_ENABLED
        KAFKA_AVAILABLE = True
    except ImportError as e2:
        logging.warning(f"Kafka client not available: {e}, {e2}")
        KAFKA_AVAILABLE = False
        KAFKA_ENABLED = False

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
if login and hasattr(login, 'router'):
    app.include_router(
        login.router,
        prefix=f"{settings.API_V1_STR}/login"
    )
else:
    logger.error("Login router not available - API endpoints will not be registered")



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
        auth_db_status = "healthy"
    except Exception as e:
        auth_db_status = f"unhealthy: {str(e)}"

    try:
        # Test admin_service database connection
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        admin_db_status = "healthy"
    except Exception as e:
        admin_db_status = f"unhealthy: {str(e)}"

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
        "auth_database": auth_db_status,
        "admin_database": admin_db_status,
        "kafka": kafka_status,
        "service": settings.PROJECT_NAME
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.DEBUG
    )

