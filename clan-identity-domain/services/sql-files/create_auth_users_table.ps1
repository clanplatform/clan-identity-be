# PowerShell Script to Create auth_users Table using Docker
# Usage: .\create_auth_users_table.ps1 [container_name]

param(
    [string]$ContainerName = "clan-identity-domain-be-postgres-1"
)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Create auth_users Table" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$DB_NAME = "auth_service"
$SQL_FILE = "01_create_auth_users_table.sql"

Write-Host "Using Docker container: $ContainerName" -ForegroundColor Yellow
Write-Host "Database: $DB_NAME" -ForegroundColor Yellow
Write-Host ""

# Check if SQL file exists
if (-not (Test-Path $SQL_FILE)) {
    Write-Host "ERROR: SQL file not found: $SQL_FILE" -ForegroundColor Red
    Write-Host "  Please run this script from the sql-files directory" -ForegroundColor Yellow
    exit 1
}

# Check if container is running
Write-Host "Checking if container is running..." -ForegroundColor Yellow
docker ps --format "{{.Names}}" | Select-String -Pattern $ContainerName -Quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Container '$ContainerName' not found or not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Available containers:" -ForegroundColor Yellow
    docker ps --format "{{.Names}}"
    Write-Host ""
    Write-Host "Usage: .\create_auth_users_table.ps1 [container_name]" -ForegroundColor Yellow
    Write-Host "Example: .\create_auth_users_table.ps1 my-postgres-container" -ForegroundColor Yellow
    exit 1
}

Write-Host "Container found!" -ForegroundColor Green
Write-Host ""

# Copy SQL file into container
Write-Host "Copying SQL file to container..." -ForegroundColor Yellow
docker cp $SQL_FILE "${ContainerName}:/tmp/01_create_auth_users_table.sql"

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED to copy SQL file to container" -ForegroundColor Red
    exit 1
}
Write-Host "File copied successfully" -ForegroundColor Green
Write-Host ""

# Execute SQL file
Write-Host "Creating auth_users table..." -ForegroundColor Yellow
docker exec -i $ContainerName psql -U postgres -d $DB_NAME -f /tmp/01_create_auth_users_table.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS: Created auth_users table" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "FAILED to create table" -ForegroundColor Red
    Write-Host "Make sure database '$DB_NAME' exists" -ForegroundColor Yellow
    exit 1
}

# Cleanup
docker exec -i $ContainerName rm /tmp/01_create_auth_users_table.sql

Write-Host ""

# Verify table was created
Write-Host "Table structure:" -ForegroundColor Yellow
Write-Host "----------------" -ForegroundColor Gray
docker exec -i $ContainerName psql -U postgres -d $DB_NAME -c "\d auth_users"

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Table creation completed!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart the auth-service container" -ForegroundColor Gray
Write-Host "  2. Test password change to create user in auth_users table" -ForegroundColor Gray
Write-Host ""

# Query to verify
Write-Host "To verify data later, run:" -ForegroundColor Cyan
Write-Host "  docker exec -i $ContainerName psql -U postgres -d $DB_NAME -c ""SELECT * FROM auth_users;""" -ForegroundColor Gray
Write-Host ""
