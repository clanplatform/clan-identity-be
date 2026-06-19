"""
Auth Service Database Drop Script
Drops all tables from clan_identity database (USE WITH CAUTION!)
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Import settings
try:
    from core.config import settings
except ImportError:
    from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def confirm_drop():
    """Get user confirmation before dropping database"""
    print("\n" + "="*70)
    print("WARNING: DATABASE DROP OPERATION")
    print("="*70)
    print(f"\nYou are about to drop ALL TABLES from database: {settings.POSTGRES_DB}")
    print(f"Host: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
    print("\nThis action will:")
    print("  - Delete all data in auth_users table")
    print("  - Delete all data in sessions table")
    print("  - Delete all data in login_attempts table")
    print("  - This action CANNOT be undone!")
    print("\n" + "="*70)
    
    response = input("\nType 'DROP DATABASE' to confirm: ")
    return response == "DROP DATABASE"


def drop_tables():
    """Drop all tables from the database"""
    try:
        # Create connection to the database
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        engine = create_engine(database_url)
        
        logger.info(f"Connecting to database: {settings.POSTGRES_DB}")
        
        with engine.connect() as conn:
            # Drop tables in correct order (considering potential FKs)
            tables = ['login_attempts', 'sessions', 'auth_users']
            
            logger.info("Dropping tables...")
            for table in tables:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
                    conn.commit()
                    logger.info(f"  ✓ Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"  ✗ Could not drop table {table}: {e}")
            
            # Drop the update trigger function if exists
            try:
                conn.execute(text('DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE'))
                conn.commit()
                logger.info("  ✓ Dropped trigger function: update_updated_at_column")
            except Exception as e:
                logger.warning(f"  ✗ Could not drop trigger function: {e}")
        
        engine.dispose()
        logger.info("\n✓ All tables dropped successfully")
        return True
        
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        return False


def drop_database():
    """Drop the entire database"""
    try:
        # Connect to postgres database to drop target database
        admin_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        logger.info(f"Dropping database: {settings.POSTGRES_DB}")
        
        with admin_engine.connect() as conn:
            # Terminate all connections to the database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{settings.POSTGRES_DB}'
                AND pid <> pg_backend_pid()
            """))
            
            # Drop the database
            conn.execute(text(f'DROP DATABASE IF EXISTS "{settings.POSTGRES_DB}"'))
            logger.info(f"✓ Database '{settings.POSTGRES_DB}' dropped successfully")
        
        admin_engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Error dropping database: {e}")
        return False


def main():
    """Main drop function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Drop auth service database or tables')
    parser.add_argument(
        '--full',
        action='store_true',
        help='Drop the entire database (not just tables)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt (USE WITH EXTREME CAUTION!)'
    )
    
    args = parser.parse_args()
    
    if not args.force:
        if not confirm_drop():
            logger.info("Operation cancelled by user")
            sys.exit(0)
    
    logger.info("\n" + "="*70)
    logger.info("DROPPING AUTH SERVICE DATABASE")
    logger.info("="*70 + "\n")
    
    if args.full:
        # Drop entire database
        if drop_database():
            logger.info("\n" + "="*70)
            logger.info("✅ DATABASE DROPPED SUCCESSFULLY")
            logger.info("="*70)
            logger.info("\nTo recreate, run: python scripts/init_db.py")
        else:
            logger.error("\n❌ Failed to drop database")
            sys.exit(1)
    else:
        # Drop only tables
        if drop_tables():
            logger.info("\n" + "="*70)
            logger.info("✅ TABLES DROPPED SUCCESSFULLY")
            logger.info("="*70)
            logger.info("\nTo recreate tables, run: python scripts/init_db.py")
        else:
            logger.error("\n❌ Failed to drop tables")
            sys.exit(1)


if __name__ == "__main__":
    main()
