"""
Diagnostic script to check for database issues that might cause transaction failures
"""
import psycopg2
import sys
from datetime import datetime, timezone

def diagnose_database():
    """Run various diagnostic checks on the auth_service database"""
    
    db_params = {
        'host': 'localhost',
        'port': 5433,
        'database': 'auth_service',
        'user': 'postgres',
        'password': 'root'
    }
    
    if len(sys.argv) > 1:
        db_params['host'] = sys.argv[1]
    if len(sys.argv) > 2:
        db_params['port'] = int(sys.argv[2])
    
    print("=" * 70)
    print("AUTH_SERVICE DATABASE DIAGNOSTICS")
    print("=" * 70)
    print(f"\nDatabase: {db_params['host']}:{db_params['port']}/{db_params['database']}\n")
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Check 1: Verify all expected tables exist
        print("1. Checking tables...")
        print("-" * 70)
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['auth_users', 'sessions', 'login_attempts', 'otps']
        
        for table in expected_tables:
            if table in tables:
                print(f"  ✓ {table} exists")
            else:
                print(f"  ✗ {table} MISSING")
        
        # Check 2: Verify auth_users table structure
        print("\n2. Checking auth_users table structure...")
        print("-" * 70)
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'auth_users'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        required_columns = {
            'id': 'uuid',
            'email': 'character varying',
            'username': 'character varying',
            'password_hash': 'character varying',
            'firstname': 'character varying',
            'lastname': 'character varying',
            'employee_id': 'character varying',
            'is_password_change': 'boolean',
            'status': 'character varying'
        }
        
        found_columns = {col[0]: col[1] for col in columns}
        for col_name, expected_type in required_columns.items():
            if col_name in found_columns:
                actual_type = found_columns[col_name]
                if expected_type in actual_type:
                    print(f"  ✓ {col_name}: {actual_type}")
                else:
                    print(f"  ⚠ {col_name}: {actual_type} (expected {expected_type})")
            else:
                print(f"  ✗ {col_name} MISSING")
        
        # Check 3: Verify sessions table structure
        print("\n3. Checking sessions table structure...")
        print("-" * 70)
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'sessions'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        required_session_columns = {
            'id': 'uuid',
            'user_id': 'uuid',
            'access_token_hash': 'character varying',
            'refresh_token_hash': 'character varying',
            'is_active': 'boolean',
            'is_revoked': 'boolean',
            'expires_at': 'timestamp',
            'created_at': 'timestamp',
            'last_activity': 'timestamp'
        }
        
        found_columns = {col[0]: col[1] for col in columns}
        for col_name, expected_type in required_session_columns.items():
            if col_name in found_columns:
                actual_type = found_columns[col_name]
                if expected_type in actual_type:
                    print(f"  ✓ {col_name}: {actual_type}")
                else:
                    print(f"  ⚠ {col_name}: {actual_type} (expected {expected_type})")
            else:
                print(f"  ✗ {col_name} MISSING")
        
        # Check 4: Test inserting and rolling back a session
        print("\n4. Testing session insert/rollback...")
        print("-" * 70)
        try:
            import uuid
            test_id = uuid.uuid4()
            test_user_id = uuid.uuid4()
            
            cursor.execute("""
                INSERT INTO sessions (
                    id, user_id, access_token_hash, refresh_token_hash,
                    is_active, is_revoked, expires_at
                ) VALUES (
                    %s, %s, 'test_hash', 'test_hash',
                    true, false, %s
                )
            """, (test_id, test_user_id, datetime.now(timezone.utc)))
            
            print(f"  ✓ Test insert successful")
            
            conn.rollback()  # Rollback the test insert
            print(f"  ✓ Rollback successful")
            
        except Exception as e:
            print(f"  ✗ Test insert failed: {e}")
            conn.rollback()
        
        # Check 5: Check for any constraints or triggers
        print("\n5. Checking constraints...")
        print("-" * 70)
        cursor.execute("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                tc.constraint_type
            FROM information_schema.table_constraints tc
            WHERE tc.table_schema = 'public'
            AND tc.table_name IN ('auth_users', 'sessions', 'login_attempts')
            ORDER BY tc.table_name, tc.constraint_type
        """)
        constraints = cursor.fetchall()
        if constraints:
            for constraint_name, table_name, constraint_type in constraints:
                print(f"  {table_name}.{constraint_name}: {constraint_type}")
        else:
            print("  No constraints found")
        
        # Check 6: Check for active connections and locks
        print("\n6. Checking active connections...")
        print("-" * 70)
        cursor.execute("""
            SELECT COUNT(*) as connection_count
            FROM pg_stat_activity
            WHERE datname = %s
        """, (db_params['database'],))
        count = cursor.fetchone()[0]
        print(f"  Active connections: {count}")
        
        # Check 7: Check table row counts
        print("\n7. Checking table row counts...")
        print("-" * 70)
        for table in ['auth_users', 'sessions', 'login_attempts', 'otps']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✓ Diagnostics complete!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ DIAGNOSTIC ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nUsage: python diagnose_database_issues.py [host] [port]")
    print("Example: python diagnose_database_issues.py localhost 5433\n")
    
    success = diagnose_database()
    sys.exit(0 if success else 1)
