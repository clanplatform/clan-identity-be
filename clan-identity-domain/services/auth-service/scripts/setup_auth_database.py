"""
Script to set up the auth_service database and create all required tables
This script will:
1. Create the auth_service database if it doesn't exist
2. Create all tables including auth_users
"""
import sys
import os
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the auth-service directory to Python path
auth_service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(auth_service_dir))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_config():
    """Get database configuration from environment or defaults"""
    # Try to load from environment file
    env_file = Path(__file__).parent.parent.parent.parent / "config" / "environments" / ".env.local"
    
    config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'root',
        'database': 'auth_service'
    }
    
    # Try to read from .env file
    if env_file.exists():
        logger.info(f"Reading configuration from: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'POSTGRES_HOST' and value != 'postgres':
                        config['host'] = value
                    elif key == 'POSTGRES_PORT':
                        config['port'] = int(value)
                    elif key == 'POSTGRES_USER':
                        config['user'] = value
                    elif key == 'POSTGRES_PASSWORD':
                        config['password'] = value
                    elif key == 'POSTGRES_DB':
                        config['database'] = value
    
    # Allow command line override
    if len(sys.argv) > 1:
        config['host'] = sys.argv[1]
    if len(sys.argv) > 2:
        config['port'] = int(sys.argv[2])
    
    logger.info(f"Database config: host={config['host']}, port={config['port']}, database={config['database']}")
    return config


def create_database_if_not_exists(config):
    """Create the auth_service database if it doesn't exist"""
    logger.info("=" * 60)
    logger.info("Step 1: Checking if auth_service database exists")
    logger.info("=" * 60)
    
    try:
        # Connect to postgres database (default database)
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config['database'],)
        )
        exists = cursor.fetchone()
        
        if exists:
            logger.info(f"✓ Database '{config['database']}' already exists")
        else:
            logger.info(f"Creating database '{config['database']}'...")
            cursor.execute(f"CREATE DATABASE {config['database']}")
            logger.info(f"✓ Database '{config['database']}' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ ERROR: Failed to create database: {e}")
        return False


def create_tables(config):
    """Create all tables in the auth_service database"""
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Creating tables in auth_service database")
    logger.info("=" * 60)
    
    try:
        # Import database components
        from database.database import Base, engine
        from models.login_user import AuthUser
        from models.session import Session
        from models.login_attempt import LoginAttempt
        
        # Check current tables
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        logger.info(f"\nExisting tables BEFORE creation: {existing_tables}")
        
        # Create all tables (will skip existing ones)
        logger.info("\nCreating tables...")
        Base.metadata.create_all(bind=engine)
        
        # Check tables after creation
        inspector = inspect(engine)
        current_tables = inspector.get_table_names()
        
        logger.info(f"\nTables AFTER creation: {current_tables}")
        
        # Verify auth_users table
        if 'auth_users' in current_tables:
            logger.info("\n✓ SUCCESS: auth_users table created successfully!")
            
            # Get column information
            columns = inspector.get_columns('auth_users')
            logger.info(f"\nauth_users table has {len(columns)} columns:")
            for col in columns:
                logger.info(f"  - {col['name']}: {col['type']}")
        else:
            logger.error("\n✗ ERROR: auth_users table was not created!")
            return False
        
        # Verify all expected tables exist
        expected_tables = ['auth_users', 'sessions', 'login_attempts']
        missing_tables = [t for t in expected_tables if t not in current_tables]
        
        if missing_tables:
            logger.warning(f"\nWarning: Some expected tables are missing: {missing_tables}")
            logger.info("This is normal if you have an 'otps' table from a previous setup")
        else:
            logger.info(f"\n✓ All expected tables exist: {expected_tables}")
        
        # Test database connection
        logger.info("\nTesting database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM auth_users"))
            count = result.scalar()
            logger.info(f"✓ Database query successful. auth_users has {count} records.")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ ERROR: Failed to create tables: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main setup function"""
    logger.info("Starting auth_service database setup...")
    logger.info("\nUsage: python setup_auth_database.py [host] [port]")
    logger.info("Example: python setup_auth_database.py localhost 5433")
    logger.info("")
    
    # Get configuration
    config = get_db_config()
    
    # Step 1: Create database if it doesn't exist
    if not create_database_if_not_exists(config):
        logger.error("\n✗ Failed to create database!")
        return False
    
    # Step 2: Create tables
    if not create_tables(config):
        logger.error("\n✗ Failed to create tables!")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Database setup completed successfully!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Verify the auth_users table exists in your database")
    logger.info("2. Start the auth-service application")
    logger.info("3. Test the login endpoint")
    logger.info("")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
