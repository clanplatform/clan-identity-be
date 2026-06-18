#!/bin/bash
# PostgreSQL Multi-Database Initialization Script
# Creates multiple databases for microservices architecture

set -e
set -u

echo "🚀 Initializing multiple databases..."

# Function to create database if it doesn't exist
create_database() {
    local database=$1
    echo "📦 Creating database: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
    echo "✓ Database '$database' ready"
}

# Parse POSTGRES_MULTIPLE_DATABASES environment variable
if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
    echo "📋 Databases to create: $POSTGRES_MULTIPLE_DATABASES"
    
    # Split by comma and create each database
    IFS=',' read -ra DATABASES <<< "$POSTGRES_MULTIPLE_DATABASES"
    for db in "${DATABASES[@]}"; do
        # Trim whitespace
        db=$(echo "$db" | xargs)
        
        # Skip if it's the default database (already exists)
        if [ "$db" != "$POSTGRES_DB" ]; then
            create_database "$db"
        else
            echo "ℹ️  Database '$db' is the default database (already exists)"
        fi
    done
    
    echo ""
    echo "✅ All databases initialized successfully!"
    echo "📊 Available databases:"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\l" | grep -E "auth_service|user_service|session_service|rbac_service|oauth_service" || true
else
    echo "⚠️  POSTGRES_MULTIPLE_DATABASES not set, skipping additional database creation"
fi

echo ""
echo "🎉 Database initialization complete!"
