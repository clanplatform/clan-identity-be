"""
Test script to verify if we can insert into auth_users table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from uuid import uuid4
from datetime import datetime, timezone

def test_raw_sql_insert():
    """Test insert using raw SQL"""
    print("=" * 70)
    print("Testing RAW SQL INSERT into auth_users")
    print("=" * 70)
    
    conn = psycopg2.connect(
        host='localhost',
        port=5433,
        database='auth_service',
        user='postgres',
        password='root'
    )
    cursor = conn.cursor()
    
    try:
        test_id = uuid4()
        test_user_setup_id = uuid4()
        
        # Test the exact INSERT that's failing
        cursor.execute("""
            INSERT INTO auth_users (
                id, user_setup_id, firstname, lastname, employee_id,
                username, email, phone_number, password_hash,
                password_changed, is_password_change, status,
                start_date, end_date, tem_employee, department,
                division, job_code, manage_roles, default_dept,
                reporting_to, entities, default_entity, view, dashboard_view
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            RETURNING created_at, updated_at
        """, (
            test_id, test_user_setup_id, 'Test', 'User', 'TEST001',
            'testuser', 'test@example.com', None, 'test_hash',
            datetime.now(timezone.utc), True, 'active',
            None, None, False, None,
            None, None, None, None,
            None, None, None, None, None
        ))
        
        result = cursor.fetchone()
        conn.commit()
        
        print(f"✓ RAW SQL INSERT successful!")
        print(f"  ID: {test_id}")
        print(f"  user_setup_id: {test_user_setup_id}")
        print(f"  created_at: {result[0]}")
        print(f"  updated_at: {result[1]}")
        
        # Clean up test record
        cursor.execute("DELETE FROM auth_users WHERE id = %s", (test_id,))
        conn.commit()
        print(f"✓ Test record cleaned up")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ RAW SQL INSERT failed: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False


def test_sqlalchemy_insert():
    """Test insert using SQLAlchemy (same as the app)"""
    print("\n" + "=" * 70)
    print("Testing SQLALCHEMY INSERT into auth_users")
    print("=" * 70)
    
    try:
        from database.database import SessionLocal, Base, engine
        from models.login_user import AuthUser
        from uuid import uuid4
        from datetime import datetime, timezone
        
        # Check what database we're connected to
        with engine.connect() as conn:
            result = conn.execute("SELECT current_database()")
            db_name = result.scalar()
            print(f"Connected to database: {db_name}")
            
            # Check if auth_users table exists
            result = conn.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'auth_users' 
                AND column_name = 'user_setup_id'
            """)
            exists = result.fetchone()
            if exists:
                print(f"✓ Column 'user_setup_id' exists in auth_users table")
            else:
                print(f"✗ Column 'user_setup_id' DOES NOT exist in auth_users table")
                print(f"\nAvailable columns:")
                result = conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'auth_users'
                    ORDER BY ordinal_position
                """)
                for row in result:
                    print(f"  - {row[0]}")
                return False
        
        db = SessionLocal()
        
        try:
            test_user = AuthUser(
                user_setup_id=uuid4(),
                firstname='SQLAlchemy',
                lastname='Test',
                employee_id='SQLA001',
                username='sqlalchemytest',
                email='sqlalchemy@example.com',
                password_hash='test_hash',
                is_password_change=True,
                status='active'
            )
            
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            print(f"✓ SQLALCHEMY INSERT successful!")
            print(f"  ID: {test_user.id}")
            print(f"  user_setup_id: {test_user.user_setup_id}")
            print(f"  email: {test_user.email}")
            
            # Clean up
            db.delete(test_user)
            db.commit()
            print(f"✓ Test record cleaned up")
            
            db.close()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"✗ SQLALCHEMY INSERT failed: {e}")
            import traceback
            traceback.print_exc()
            db.close()
            return False
            
    except Exception as e:
        print(f"✗ Failed to initialize SQLAlchemy: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nTesting INSERT operations into auth_users table\n")
    
    # Test 1: Raw SQL
    raw_success = test_raw_sql_insert()
    
    # Test 2: SQLAlchemy
    sqlalchemy_success = test_sqlalchemy_insert()
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Raw SQL Insert: {'✓ PASSED' if raw_success else '✗ FAILED'}")
    print(f"SQLAlchemy Insert: {'✓ PASSED' if sqlalchemy_success else '✗ FAILED'}")
    print()
    
    sys.exit(0 if (raw_success and sqlalchemy_success) else 1)
