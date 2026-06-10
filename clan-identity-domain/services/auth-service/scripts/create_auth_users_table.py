"""
Script to create the auth_users table in the auth_service database
Run this script to manually create the auth_users table if it's missing
"""
import sys
import os
from pathlib import Path

# Add the auth-service directory to Python path
auth_service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(auth_service_dir))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_auth_users_table():
    """Create auth_users table and verify all tables exist"""
    try:
        # Import database components
        from database.database import Base, engine, SessionLocal
        from models.login_user import AuthUser
        from models.session import Session
        from models.login_attempt import LoginAttempt
        
        logger.info("=" * 60)
        logger.info("Creating auth_users table in auth_service database")
        logger.info("=" * 60)
        
        # Check current tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        logger.info(f"\nExisting tables BEFORE creation: {existing_tables}")
        
        # Create all tables (will skip existing ones)
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
        else:
            logger.info(f"\n✓ All expected tables exist: {expected_tables}")
        
        # Test database connection
        logger.info("\nTesting database connection...")
        db = SessionLocal()
        try:
            result = db.execute("SELECT COUNT(*) FROM auth_users")
            count = result.scalar()
            logger.info(f"✓ Database query successful. auth_users has {count} records.")
        finally:
            db.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ ERROR: Failed to create auth_users table: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Starting database table creation script...")
    success = create_auth_users_table()
    
    if success:
        logger.info("\n✓ Script completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Script failed!")
        sys.exit(1)
