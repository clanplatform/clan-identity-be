# PowerShell Script to Recreate auth_users Table using Docker
# Run this if psql is not installed on your host machine

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Recreate auth_users Table (Docker)" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$CONTAINER_NAME = "postgres"
$DB_NAME = "auth_service"
$SQL_FILE = "01_create_auth_users_table.sql"

Write-Host "Using Docker container: $CONTAINER_NAME" -ForegroundColor Yellow
Write-Host ""

# Check if SQL file exists
if (-not (Test-Path $SQL_FILE)) {
    Write-Host "ERROR: SQL file not found: $SQL_FILE" -ForegroundColor Red
    Write-Host "  Please run this script from the sql-files directory" -ForegroundColor Yellow
    exit 1
}

# Step 1: Drop existing table
Write-Host "[Step 1/2] Dropping existing auth_users table..." -ForegroundColor Yellow
$dropSQL = "DROP TABLE IF EXISTS auth_users CASCADE;"
try {
    docker exec -i $CONTAINER_NAME psql -U postgres -d $DB_NAME -c $dropSQL
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Dropped auth_users table" -ForegroundColor Green
    } else {
        Write-Host "FAILED to drop table" -ForegroundColor Red
        Write-Host "  Make sure Docker container '$CONTAINER_NAME' is running" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Copy SQL file into container and execute
Write-Host "[Step 2/2] Creating new auth_users table..." -ForegroundColor Yellow

# Copy SQL file to container
docker cp $SQL_FILE "${CONTAINER_NAME}:/tmp/01_create_auth_users_table.sql"

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED to copy SQL file to container" -ForegroundColor Red
    exit 1
}

# Execute SQL file
docker exec -i $CONTAINER_NAME psql -U postgres -d $DB_NAME -f /tmp/01_create_auth_users_table.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Created auth_users table" -ForegroundColor Green
} else {
    Write-Host "FAILED to create table" -ForegroundColor Red
    exit 1
}

# Cleanup
docker exec -i $CONTAINER_NAME rm /tmp/01_create_auth_users_table.sql

Write-Host ""

# Step 3: Verify table was created
Write-Host "[Verification] Checking table structure..." -ForegroundColor Yellow
docker exec -i $CONTAINER_NAME psql -U postgres -d $DB_NAME -c "\d auth_users"

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Table recreation completed!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart the auth-service container: docker restart auth-service" -ForegroundColor Gray
Write-Host "  2. Test password change to create user in auth_users table" -ForegroundColor Gray
Write-Host ""
