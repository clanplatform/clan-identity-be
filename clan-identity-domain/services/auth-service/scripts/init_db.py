"""
Auth Service Database Initialization Script
Creates all tables for auth_service database
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Import Base and models
try:
    from database.database import Base, engine, settings
    from models.login_user import AuthUser
    from models.session import Session
    from models.login_attempt import LoginAttempt
except ImportError:
    from app.database.database import Base, engine, settings
    from app.models.login_user import AuthUser
    from app.models.session import Session
    from app.models.login_attempt import LoginAttempt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_exists() -> bool:
    """Check if the database exists"""
    try:
        # Create connection to postgres database to check if target DB exists
        admin_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.POSTGRES_DB}
            )
            exists = result.fetchone() is not None
        
        admin_engine.dispose()
        return exists
    except Exception as e:
        logger.error(f"Error checking database existence: {e}")
        return False


def create_database():
    """Create the database if it doesn't exist"""
    try:
        if check_database_exists():
            logger.info(f"Database '{settings.POSTGRES_DB}' already exists")
            return True
        
        # Connect to postgres database to create new database
        admin_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        with admin_engine.connect() as conn:
            logger.info(f"Creating database '{settings.POSTGRES_DB}'...")
            conn.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
            logger.info(f"Database '{settings.POSTGRES_DB}' created successfully")
        
        admin_engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def check_tables_exist() -> dict:
    """Check which tables exist in the database"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        expected_tables = ['auth_users', 'sessions', 'login_attempts']
        table_status = {
            table: table in existing_tables
            for table in expected_tables
        }
        
        return table_status
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return {}


def create_tables():
    """Create all tables defined in the models"""
    try:
        logger.info("Checking existing tables...")
        table_status = check_tables_exist()
        
        for table, exists in table_status.items():
            status = "EXISTS" if exists else "MISSING"
            logger.info(f"  - {table}: {status}")
        
        logger.info("\nCreating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("\nVerifying created tables...")
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        
        for table in created_tables:
            columns = [col['name'] for col in inspector.get_columns(table)]
            logger.info(f"\n  Table: {table}")
            logger.info(f"  Columns: {', '.join(columns)}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False


def verify_database_connection():
    """Verify database connection"""
    try:
        logger.info("Verifying database connection...")
        logger.info(f"  Host: {settings.POSTGRES_SERVER}")
        logger.info(f"  Port: {settings.POSTGRES_PORT}")
        logger.info(f"  Database: {settings.POSTGRES_DB}")
        logger.info(f"  User: {settings.POSTGRES_USER}")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"  PostgreSQL version: {version}")
        
        return True
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Please ensure PostgreSQL is running and credentials are correct")
        return False


def create_indexes():
    """Create additional indexes for performance"""
    try:
        logger.info("\nCreating additional indexes...")
        
        indexes = [
            # Login attempts indexes for security queries
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_user_created ON login_attempts(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_created ON login_attempts(ip_address, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_suspicious ON login_attempts(is_suspicious, created_at DESC) WHERE is_suspicious = true",
            
            # Auth users indexes for authentication
            "CREATE INDEX IF NOT EXISTS idx_auth_users_status_active ON auth_users(status) WHERE status = 'active'",
            "CREATE INDEX IF NOT EXISTS idx_auth_users_employee_status ON auth_users(employee_id, status)",
            
            # Sessions indexes for active session queries
            "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(user_id, expires_at) WHERE is_active = true",
            "CREATE INDEX IF NOT EXISTS idx_sessions_cleanup ON sessions(expires_at, is_active) WHERE is_active = true",
        ]
        
        with engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.info(f"  ✓ Created index")
                except Exception as e:
                    logger.warning(f"  ✗ Index creation warning: {e}")
        
        logger.info("Index creation completed")
        return True
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return False


def main():
    """Main initialization function"""
    logger.info("="*70)
    logger.info("AUTH SERVICE DATABASE INITIALIZATION")
    logger.info("="*70)
    
    # Step 1: Verify connection
    if not verify_database_connection():
        logger.error("\n❌ Database initialization failed: Connection error")
        sys.exit(1)
    
    # Step 2: Create database if needed
    if not create_database():
        logger.error("\n❌ Database initialization failed: Could not create database")
        sys.exit(1)
    
    # Step 3: Create tables
    if not create_tables():
        logger.error("\n❌ Database initialization failed: Could not create tables")
        sys.exit(1)
    
    # Step 4: Create indexes
    if not create_indexes():
        logger.warning("\n⚠️  Some indexes could not be created, but tables are ready")
    
    logger.info("\n" + "="*70)
    logger.info("✅ AUTH SERVICE DATABASE INITIALIZED SUCCESSFULLY")
    logger.info("="*70)
    logger.info("\nCreated tables:")
    logger.info("  - auth_users: Stores authenticated user data")
    logger.info("  - sessions: Manages user sessions")
    logger.info("  - login_attempts: Tracks login attempts for security")
    logger.info("\nYou can now start the auth service!")


if __name__ == "__main__":
    main()
