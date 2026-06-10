"""
Direct SQL script to create the auth_users table
This bypasses SQLAlchemy and creates the table directly with SQL
"""
import psycopg2
import sys

def create_auth_users_table():
    """Create auth_users table using direct SQL"""
    
    # Database connection parameters
    # Adjust these based on your setup
    db_params = {
        'host': 'localhost',
        'port': 5433,  # Docker exposed port
        'database': 'auth_service',
        'user': 'postgres',
        'password': 'root'
    }
    
    # Allow command line override: python script.py <host> <port>
    if len(sys.argv) > 1:
        db_params['host'] = sys.argv[1]
    if len(sys.argv) > 2:
        db_params['port'] = int(sys.argv[2])
    
    print("=" * 70)
    print("Creating auth_users table in auth_service database")
    print("=" * 70)
    print(f"\nConnecting to: {db_params['host']}:{db_params['port']}/{db_params['database']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Check existing tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nExisting tables BEFORE: {existing_tables}")
        
        # Create auth_users table
        print("\nCreating auth_users table...")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS auth_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_setup_id UUID UNIQUE,
            
            -- Personal Information
            firstname VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            employee_id VARCHAR(50) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            phone_number VARCHAR(20),
            
            -- Authentication
            password_hash VARCHAR(255) NOT NULL,
            password_changed TIMESTAMP WITH TIME ZONE,
            is_password_change BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- Employment Status
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            start_date DATE,
            end_date DATE,
            tem_employee BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- Organizational Structure (UUIDs, no FK constraints)
            department UUID,
            division UUID,
            job_code UUID,
            
            -- Role Management
            manage_roles UUID[],
            
            -- Default Settings
            default_dept UUID,
            reporting_to UUID,
            
            -- Entity Access
            entities UUID[],
            default_entity UUID,
            
            -- View Preferences
            view VARCHAR(50),
            dashboard_view VARCHAR(50),
            
            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        cursor.execute(create_table_sql)
        
        # Create indexes
        print("Creating indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS ix_auth_users_user_setup_id ON auth_users(user_setup_id);",
            "CREATE INDEX IF NOT EXISTS ix_auth_users_employee_id ON auth_users(employee_id);",
            "CREATE INDEX IF NOT EXISTS ix_auth_users_username ON auth_users(username);",
            "CREATE INDEX IF NOT EXISTS ix_auth_users_email ON auth_users(email);",
            "CREATE INDEX IF NOT EXISTS ix_auth_users_status ON auth_users(status);"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Commit changes
        conn.commit()
        
        # Verify tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        current_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nExisting tables AFTER: {current_tables}")
        
        # Check if auth_users was created
        if 'auth_users' in current_tables:
            print("\n✓ SUCCESS: auth_users table created successfully!")
            
            # Get column information
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'auth_users'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print(f"\nauth_users table has {len(columns)} columns:")
            for col_name, col_type, nullable in columns:
                null_str = "NULL" if nullable == 'YES' else "NOT NULL"
                print(f"  - {col_name}: {col_type} {null_str}")
            
            # Check indexes
            cursor.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'auth_users'
                ORDER BY indexname
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            print(f"\nIndexes on auth_users: {indexes}")
            
            # Test query
            cursor.execute("SELECT COUNT(*) FROM auth_users")
            count = cursor.fetchone()[0]
            print(f"\n✓ Table query successful. auth_users has {count} records.")
            
        else:
            print("\n✗ ERROR: auth_users table was not created!")
            return False
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✓ Database setup completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Restart your auth-service application")
        print("2. The service will now be able to use the auth_users table")
        print("3. Test the login endpoint")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nUsage: python create_auth_users_table_direct.py [host] [port]")
    print("Example: python create_auth_users_table_direct.py localhost 5433\n")
    
    success = create_auth_users_table()
    sys.exit(0 if success else 1)
