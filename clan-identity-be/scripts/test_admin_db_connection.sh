#!/bin/bash
# Test script to verify admin_service database connection from auth-service

echo "🔍 Testing Admin Service Database Connection..."
echo "================================================"
echo ""

# Test 1: Check if admin-service PostgreSQL is accessible from host
echo "1️⃣  Testing admin-service PostgreSQL from host machine..."
if docker ps | grep -q "admin-service-postgres"; then
    echo "   ✅ admin-service-postgres container is running"
    
    # Get the port
    PORT=$(docker port admin-service-postgres 2>/dev/null | grep 5432 | cut -d':' -f2)
    if [ -n "$PORT" ]; then
        echo "   ✅ PostgreSQL exposed on host port: $PORT"
    else
        echo "   ⚠️  PostgreSQL not exposed to host machine"
        echo "   💡 Tip: Add 'ports: - \"5432:5432\"' to admin-service postgres in docker-compose.yml"
    fi
else
    echo "   ❌ admin-service-postgres container is NOT running"
    echo "   💡 Tip: Start admin-service: cd ../clan-platform-domain-be && docker-compose up -d"
fi
echo ""

# Test 2: Test connection from auth-service container
echo "2️⃣  Testing connection from auth-service to admin_service database..."
if docker exec clan-auth-service psql \
    -h host.docker.internal \
    -U postgres \
    -d admin_service \
    -c "SELECT 1" \
    > /dev/null 2>&1; then
    echo "   ✅ Successfully connected to admin_service database!"
else
    echo "   ❌ Failed to connect to admin_service database"
    echo "   💡 Possible causes:"
    echo "      - admin-service PostgreSQL is not running"
    echo "      - PostgreSQL not exposed on port 5432"
    echo "      - Wrong credentials in .env.local"
fi
echo ""

# Test 3: Check if usersetup_basic table exists
echo "3️⃣  Checking if usersetup_basic table exists..."
if docker exec clan-auth-service psql \
    -h host.docker.internal \
    -U postgres \
    -d admin_service \
    -c "\dt usersetup_basic" \
    2>/dev/null | grep -q "usersetup_basic"; then
    
    echo "   ✅ usersetup_basic table exists!"
    
    # Count users
    USER_COUNT=$(docker exec clan-auth-service psql \
        -h host.docker.internal \
        -U postgres \
        -d admin_service \
        -t -c "SELECT COUNT(*) FROM usersetup_basic" \
        2>/dev/null | tr -d ' ')
    
    echo "   📊 Total users in usersetup_basic: $USER_COUNT"
else
    echo "   ❌ usersetup_basic table does NOT exist"
    echo "   💡 Tip: Run migrations in clan-platform-domain-be repository"
fi
echo ""

# Test 4: Check auth-service health endpoint
echo "4️⃣  Checking auth-service health endpoint..."
HEALTH=$(curl -s http://localhost:8001/health 2>/dev/null)

if echo "$HEALTH" | grep -q "admin_database.*healthy"; then
    echo "   ✅ Admin database connection is HEALTHY"
elif echo "$HEALTH" | grep -q "admin_database"; then
    ADMIN_STATUS=$(echo "$HEALTH" | grep -o '"admin_database":"[^"]*"' | cut -d'"' -f4)
    echo "   ⚠️  Admin database status: $ADMIN_STATUS"
else
    echo "   ❌ Could not get health status"
fi
echo ""

echo "================================================"
echo "📝 Summary:"
echo "   - Review CROSS_REPO_DATABASE_ACCESS.md for detailed configuration"
echo "   - Ensure admin-service PostgreSQL is running and accessible"
echo "   - Update .env.local with correct admin database credentials"
echo ""
