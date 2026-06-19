# Test script to verify clan_platform database connection from auth-service
# PowerShell version for Windows

Write-Host "ðŸ” Testing Admin Service Database Connection..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if admin-service PostgreSQL is accessible from host
Write-Host "1ï¸âƒ£  Testing admin-service PostgreSQL from host machine..." -ForegroundColor Yellow
$adminPostgres = docker ps --format "{{.Names}}" | Select-String "admin.*postgres"

if ($adminPostgres) {
    Write-Host "   âœ… admin-service-postgres container is running" -ForegroundColor Green
    
    # Check if port is exposed
    $portInfo = docker port $adminPostgres 2>$null | Select-String "5432"
    if ($portInfo) {
        Write-Host "   âœ… PostgreSQL exposed on host: $portInfo" -ForegroundColor Green
    } else {
        Write-Host "   âš ï¸  PostgreSQL not exposed to host machine" -ForegroundColor Yellow
        Write-Host "   ðŸ’¡ Tip: Add 'ports: - `"5432:5432`"' to admin-service postgres in docker-compose.yml" -ForegroundColor Gray
    }
} else {
    Write-Host "   âŒ admin-service-postgres container is NOT running" -ForegroundColor Red
    Write-Host "   ðŸ’¡ Tip: Start admin-service: cd ..\clan-platform-domain-be; docker-compose up -d" -ForegroundColor Gray
}
Write-Host ""

# Test 2: Test connection from auth-service container
Write-Host "2ï¸âƒ£  Testing connection from auth-service to clan_platform database..." -ForegroundColor Yellow
try {
    $result = docker exec clan-auth-service psql -h host.docker.internal -U postgres -d clan_platform -c "SELECT 1" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   âœ… Successfully connected to clan_platform database!" -ForegroundColor Green
    } else {
        throw "Connection failed"
    }
} catch {
    Write-Host "   âŒ Failed to connect to clan_platform database" -ForegroundColor Red
    Write-Host "   ðŸ’¡ Possible causes:" -ForegroundColor Gray
    Write-Host "      - admin-service PostgreSQL is not running" -ForegroundColor Gray
    Write-Host "      - PostgreSQL not exposed on port 5432" -ForegroundColor Gray
    Write-Host "      - Wrong credentials in .env.local" -ForegroundColor Gray
}
Write-Host ""

# Test 3: Check if usersetup_basic table exists
Write-Host "3ï¸âƒ£  Checking if usersetup_basic table exists..." -ForegroundColor Yellow
try {
    $tableCheck = docker exec clan-auth-service psql -h host.docker.internal -U postgres -d clan_platform -c "\dt usersetup_basic" 2>&1
    
    if ($tableCheck -match "usersetup_basic") {
        Write-Host "   âœ… usersetup_basic table exists!" -ForegroundColor Green
        
        # Count users
        $userCount = docker exec clan-auth-service psql -h host.docker.internal -U postgres -d clan_platform -t -c "SELECT COUNT(*) FROM usersetup_basic" 2>&1
        $userCount = $userCount.Trim()
        Write-Host "   ðŸ“Š Total users in usersetup_basic: $userCount" -ForegroundColor Cyan
    } else {
        Write-Host "   âŒ usersetup_basic table does NOT exist" -ForegroundColor Red
        Write-Host "   ðŸ’¡ Tip: Run migrations in clan-platform-domain-be repository" -ForegroundColor Gray
    }
} catch {
    Write-Host "   âŒ Could not check table existence" -ForegroundColor Red
}
Write-Host ""

# Test 4: Check auth-service health endpoint
Write-Host "4ï¸âƒ£  Checking auth-service health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -ErrorAction Stop
    $healthJson = $health.Content | ConvertFrom-Json
    
    if ($healthJson.admin_database -eq "healthy") {
        Write-Host "   âœ… Admin database connection is HEALTHY" -ForegroundColor Green
    } else {
        Write-Host "   âš ï¸  Admin database status: $($healthJson.admin_database)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "   Full Health Status:" -ForegroundColor Cyan
    Write-Host "   - Auth Database: $($healthJson.auth_database)" -ForegroundColor Gray
    Write-Host "   - Admin Database: $($healthJson.admin_database)" -ForegroundColor Gray
    Write-Host "   - Kafka: $($healthJson.kafka)" -ForegroundColor Gray
} catch {
    Write-Host "   âŒ Could not get health status from http://localhost:8001/health" -ForegroundColor Red
}
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "ðŸ“ Summary:" -ForegroundColor Cyan
Write-Host "   - Review CROSS_REPO_DATABASE_ACCESS.md for detailed configuration" -ForegroundColor Gray
Write-Host "   - Ensure admin-service PostgreSQL is running and accessible" -ForegroundColor Gray
Write-Host "   - Update config/environments/.env.local with correct admin database credentials" -ForegroundColor Gray
Write-Host ""
