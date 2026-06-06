#!/usr/bin/env python3
"""
Script to drop all auth_db tables
WARNING: This will delete all data in the tables!
"""
import os
import sys
import asyncio
import asyncpg
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

TABLES = [
    "sessions",
    "login_attempts",
    "auth_users"
]


async def drop_tables():
    """Drop all auth tables"""
    print("="*80)
    print("WARNING: DROP AUTH TABLES")
    print("="*80)
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("="*80)
    print("\nThis will DELETE all tables and data!")
    
    response = input("\nType 'YES' to confirm: ")
    
    if response != "YES":
        print("\n✗ Operation cancelled")
        return 1
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("\n✓ Connected to auth_db")
        
        for table in TABLES:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"✓ Dropped table: {table}")
            except Exception as e:
                print(f"✗ Error dropping {table}: {e}")
        
        await conn.close()
        print("\n✓ All tables dropped successfully")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(drop_tables())
    sys.exit(exit_code)
