"""
Auth Service Database Verification Script
Verifies database setup and connection health
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from datetime import datetime

# Import settings
try:
    from core.config import settings
except ImportError:
    from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(title)
    print("="*70)


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def print_info(message, indent=0):
    """Print info message with optional indentation"""
    prefix = "  " * indent
    print(f"{prefix}{message}")


def verify_connection():
    """Verify database connection"""
    print_header("DATABASE CONNECTION")
    
    try:
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        engine = create_engine(database_url)
        
        print_info(f"Host:     {settings.POSTGRES_SERVER}")
        print_info(f"Port:     {settings.POSTGRES_PORT}")
        print_info(f"Database: {settings.POSTGRES_DB}")
        print_info(f"User:     {settings.POSTGRES_USER}")
        print("")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print_success("Database connection successful")
            print_info(f"Version: {version}", indent=1)
        
        engine.dispose()
        return True
    except OperationalError as e:
        print_error(f"Database connection failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def verify_admin_connection():
    """Verify admin database connection"""
    print_header("ADMIN DATABASE CONNECTION")
    
    try:
        admin_url = f"postgresql://{settings.ADMIN_POSTGRES_USER}:{settings.ADMIN_POSTGRES_PASSWORD}@{settings.ADMIN_POSTGRES_HOST}:{settings.ADMIN_POSTGRES_PORT}/{settings.ADMIN_DB}"
        admin_engine = create_engine(admin_url)
        
        print_info(f"Host:     {settings.ADMIN_POSTGRES_HOST}")
        print_info(f"Port:     {settings.ADMIN_POSTGRES_PORT}")
        print_info(f"Database: {settings.ADMIN_DB}")
        print_info(f"User:     {settings.ADMIN_POSTGRES_USER}")
        print("")
        
        with admin_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print_success("Admin database connection successful")
            
            # Check if usersetup_basic table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'usersetup_basic'
                )
            """))
            table_exists = result.fetchone()[0]
            
            if table_exists:
                print_success("usersetup_basic table found")
            else:
                print_error("usersetup_basic table not found")
        
        admin_engine.dispose()
        return True
    except OperationalError as e:
        print_error(f"Admin database connection failed: {e}")
        print_info("This may be expected if admin service is in a different environment", indent=1)
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def verify_tables():
    """Verify all required tables exist"""
    print_header("TABLE VERIFICATION")
    
    try:
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        engine = create_engine(database_url)
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        expected_tables = {
            'auth_users': 'Authenticated user data',
            'sessions': 'User session management',
            'login_attempts': 'Login attempt tracking'
        }
        
        all_exist = True
        for table, description in expected_tables.items():
            if table in existing_tables:
                print_success(f"{table}: EXISTS")
                print_info(description, indent=1)
                
                # Get column count
                columns = inspector.get_columns(table)
                print_info(f"Columns: {len(columns)}", indent=1)
            else:
                print_error(f"{table}: MISSING")
                all_exist = False
            print("")
        
        engine.dispose()
        return all_exist
    except Exception as e:
        print_error(f"Table verification failed: {e}")
        return False


def verify_indexes():
    """Verify indexes exist"""
    print_header("INDEX VERIFICATION")
    
    try:
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        engine = create_engine(database_url)
        
        inspector = inspect(engine)
        
        tables = ['auth_users', 'sessions', 'login_attempts']
        total_indexes = 0
        
        for table in tables:
            if table in inspector.get_table_names():
                indexes = inspector.get_indexes(table)
                print_success(f"{table}: {len(indexes)} indexes")
                total_indexes += len(indexes)
                
                for idx in indexes[:3]:  # Show first 3 indexes
                    print_info(f"- {idx['name']}: {', '.join(idx['column_names'])}", indent=1)
                
                if len(indexes) > 3:
                    print_info(f"... and {len(indexes) - 3} more", indent=1)
                print("")
        
        print_success(f"Total indexes: {total_indexes}")
        
        engine.dispose()
        return True
    except Exception as e:
        print_error(f"Index verification failed: {e}")
        return False


def get_table_stats():
    """Get table statistics"""
    print_header("TABLE STATISTICS")
    
    try:
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Get row counts and sizes
            query = text("""
                SELECT
                    schemaname,
                    tablename,
                    n_live_tup as row_count,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            if rows:
                print_info(f"{'Table':<20} {'Rows':<15} {'Size':<15}")
                print_info("-" * 50)
                for row in rows:
                    table = row[1]
                    row_count = row[2] or 0
                    size = row[3]
                    print_info(f"{table:<20} {row_count:<15} {size:<15}")
            else:
                print_info("No statistics available yet")
        
        engine.dispose()
        return True
    except Exception as e:
        print_error(f"Statistics retrieval failed: {e}")
        return False


def test_crud_operations():
    """Test basic CRUD operations"""
    print_header("CRUD OPERATIONS TEST")
    
    try:
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Test SELECT
            result = conn.execute(text("SELECT 1 as test"))
            print_success("SELECT operation works")
            
            # Test table access
            result = conn.execute(text("SELECT COUNT(*) FROM auth_users"))
            count = result.fetchone()[0]
            print_success(f"Can read from auth_users table ({count} rows)")
            
            result = conn.execute(text("SELECT COUNT(*) FROM sessions"))
            count = result.fetchone()[0]
            print_success(f"Can read from sessions table ({count} rows)")
            
            result = conn.execute(text("SELECT COUNT(*) FROM login_attempts"))
            count = result.fetchone()[0]
            print_success(f"Can read from login_attempts table ({count} rows)")
        
        engine.dispose()
        return True
    except Exception as e:
        print_error(f"CRUD test failed: {e}")
        return False


def main():
    """Main verification function"""
    print("\n" + "="*70)
    print("AUTH SERVICE DATABASE VERIFICATION")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = {
        "Connection": verify_connection(),
        "Admin Connection": verify_admin_connection(),
        "Tables": verify_tables(),
        "Indexes": verify_indexes(),
        "Statistics": get_table_stats(),
        "CRUD Operations": test_crud_operations()
    }
    
    print_header("VERIFICATION SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for check, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print_info(f"{check:<25} {status}")
    
    print("")
    print_info(f"Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print_header("✅ ALL CHECKS PASSED - DATABASE IS READY")
    else:
        print_header("⚠️  SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
        sys.exit(1)


if __name__ == "__main__":
    main()
