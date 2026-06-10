import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, database='auth_service', user='postgres', password='root')
cursor = conn.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'auth_users' ORDER BY ordinal_position")
columns = [row[0] for row in cursor.fetchall()]
print("Columns in auth_users table:")
for col in columns:
    print(f"  - {col}")
    
if 'user_setup_id' in columns:
    print("\n✓ user_setup_id exists")
else:
    print("\n✗ user_setup_id MISSING")
    print("\nSearching for similar column names...")
    for col in columns:
        if 'user' in col or 'setup' in col:
            print(f"  Found: {col}")
