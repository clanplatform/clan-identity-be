"""
Verification script to check if auth_users table exists and show its structure
"""
import psycopg2
import sys

def verify_auth_users_table():
    """Verify auth_users table exists and show structure"""
    
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
    print("Verifying auth_users table")
    print("=" * 70)
    print(f"\nDatabase: {db_params['host']}:{db_params['port']}/{db_params['database']}\n")
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"All tables in auth_service database:")
        for table in tables:
            print(f"  ✓ {table}")
        
        # Check if auth_users exists
        if 'auth_users' not in tables:
            print("\n✗ ERROR: auth_users table does NOT exist!")
            return False
        
        print(f"\n✓ auth_users table EXISTS")
        
        # Get detailed column information
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'auth_users'
            ORDER BY ordinal_position
        """)
        
        print(f"\nColumn Details:")
        print("-" * 70)
        for col in cursor.fetchall():
            col_name, data_type, max_length, nullable, default = col
            length_str = f"({max_length})" if max_length else ""
            null_str = "NULL" if nullable == 'YES' else "NOT NULL"
            default_str = f" DEFAULT {default}" if default else ""
            print(f"{col_name:20} {data_type}{length_str:15} {null_str:10}{default_str}")
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM auth_users")
        count = cursor.fetchone()[0]
        print(f"\nTotal records in auth_users: {count}")
        
        # Get indexes
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes
            WHERE tablename = 'auth_users'
            ORDER BY indexname
        """)
        indexes = cursor.fetchall()
        print(f"\nIndexes ({len(indexes)} total):")
        for idx_name, idx_def in indexes:
            print(f"  ✓ {idx_name}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✓ Verification complete - auth_users table is ready!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_auth_users_table()
    sys.exit(0 if success else 1)
