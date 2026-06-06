#!/usr/bin/env python3
"""
Script to create auth_db database tables
Executes all SQL files in order to set up the database schema
"""
import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from config/environments/.env.local
env_path = Path(__file__).parent.parent.parent / "config" / "environments" / ".env.local"
load_dotenv(env_path)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "root"),
    "database": "auth_db"
}

# SQL files directory
SQL_DIR = Path(__file__).parent.parent / "sql-files"

# SQL files to execute in order
SQL_FILES = [
    "00_init_auth_database.sql",
    "01_create_auth_users_table.sql",
    "02_create_login_attempts_table.sql",
    "03_create_sessions_table.sql",
]


async def execute_sql_file(conn, filepath: Path):
    """Execute a SQL file"""
    print(f"\n{'='*80}")
    print(f"Executing: {filepath.name}")
    print(f"{'='*80}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        await conn.execute(sql)
        print(f"✓ Successfully executed {filepath.name}")
        return True
    except Exception as e:
        print(f"✗ Error executing {filepath.name}: {e}")
        return False


async def create_database_if_not_exists():
    """Create auth_db database if it doesn't exist"""
    try:
        # Connect to default postgres database
        conn = await asyncpg.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database="postgres"
        )
        
        # Check if auth_db exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'auth_db'"
        )
        
        if not result:
            print("Creating auth_db database...")
            await conn.execute("CREATE DATABASE auth_db")
            print("✓ Database auth_db created successfully")
        else:
            print("✓ Database auth_db already exists")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False


async def main():
    """Main function to create all tables"""
    print("="*80)
    print("AUTH DATABASE TABLE CREATION SCRIPT")
    print("="*80)
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"User: {DB_CONFIG['user']}")
    print("="*80)
    
    # Create database if it doesn't exist
    if not await create_database_if_not_exists():
        sys.exit(1)
    
    try:
        # Connect to auth_db
        conn = await asyncpg.connect(**DB_CONFIG)
        print("\n✓ Connected to auth_db successfully")
        
        # Execute SQL files
        success_count = 0
        for sql_file in SQL_FILES:
            filepath = SQL_DIR / sql_file
            if not filepath.exists():
                print(f"\n✗ SQL file not found: {filepath}")
                continue
            
            if await execute_sql_file(conn, filepath):
                success_count += 1
        
        await conn.close()
        
        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total SQL files: {len(SQL_FILES)}")
        print(f"Successfully executed: {success_count}")
        print(f"Failed: {len(SQL_FILES) - success_count}")
        
        if success_count == len(SQL_FILES):
            print("\n✓ All tables created successfully!")
            print("="*80)
            return 0
        else:
            print("\n✗ Some tables failed to create")
            print("="*80)
            return 1
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
