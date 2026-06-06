#!/usr/bin/env python3
"""
Script to verify auth_db tables and their structure
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


async def verify_tables():
    """Verify all auth tables exist and show their structure"""
    print("="*80)
    print("AUTH DATABASE VERIFICATION")
    print("="*80)
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("="*80)
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("\n✓ Connected to auth_db successfully")
        
        # List all tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        print(f"\n{'='*80}")
        print(f"TABLES IN DATABASE ({len(tables)} found)")
        print(f"{'='*80}")
        
        for table in tables:
            tablename = table['tablename']
            print(f"\n📋 Table: {tablename}")
            
            # Get column information
            columns = await conn.fetch(f"""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = '{tablename}'
                ORDER BY ordinal_position
            """)
            
            print(f"   Columns ({len(columns)}):")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"   - {col['column_name']:<30} {col['data_type']:<20} {nullable}{default}")
            
            # Get indexes
            indexes = await conn.fetch(f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = '{tablename}'
                ORDER BY indexname
            """)
            
            if indexes:
                print(f"\n   Indexes ({len(indexes)}):")
                for idx in indexes:
                    print(f"   - {idx['indexname']}")
            
            # Get row count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {tablename}")
            print(f"\n   Row count: {count}")
        
        # Get table sizes
        print(f"\n{'='*80}")
        print("TABLE SIZES")
        print(f"{'='*80}")
        
        sizes = await conn.fetch("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        
        for size in sizes:
            print(f"{size['tablename']:<30} {size['size']}")
        
        await conn.close()
        
        print(f"\n{'='*80}")
        print("✓ Verification complete")
        print(f"{'='*80}")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(verify_tables())
    sys.exit(exit_code)
