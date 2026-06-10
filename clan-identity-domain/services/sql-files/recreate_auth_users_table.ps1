# PowerShell Script to Recreate auth_users Table
# Run this script from the host machine (not inside Docker)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Recreate auth_users Table Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Database connection parameters
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_USER = "postgres"
$DB_PASSWORD = "root"
$DB_NAME = "auth_service"

# Set PostgreSQL password environment variable
$env:PGPASSWORD = $DB_PASSWORD

Write-Host "Database Connection Info:" -ForegroundColor Yellow
Write-Host "  Host: $DB_HOST" -ForegroundColor Gray
Write-Host "  Port: $DB_PORT" -ForegroundColor Gray
Write-Host "  Database: $DB_NAME" -ForegroundColor Gray
Write-Host "  User: $DB_USER" -ForegroundColor Gray
Write-Host ""

# Step 1: Drop existing table
Write-Host "[Step 1/2] Dropping existing auth_users table..." -ForegroundColor Yellow
$dropSQL = "DROP TABLE IF EXISTS auth_users CASCADE;"
try {
    $dropResult = psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $dropSQL 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Dropped auth_users table" -ForegroundColor Green
    } else {
        Write-Host "FAILED to drop table: $dropResult" -ForegroundColor Red
        Write-Host ""
        Write-Host "Note: If psql command not found, install PostgreSQL client tools" -ForegroundColor Yellow
        Remove-Item Env:\PGPASSWORD
        exit 1
    }
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Remove-Item Env:\PGPASSWORD
    exit 1
}

Write-Host ""

# Step 2: Run the SQL file to create new table
Write-Host "[Step 2/2] Creating new auth_users table..." -ForegroundColor Yellow
$sqlFilePath = "01_create_auth_users_table.sql"

if (Test-Path $sqlFilePath) {
    try {
        $createResult = psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $sqlFilePath 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Created auth_users table" -ForegroundColor Green
        } else {
            Write-Host "FAILED to create table: $createResult" -ForegroundColor Red
            Remove-Item Env:\PGPASSWORD
            exit 1
        }
    } catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
        Remove-Item Env:\PGPASSWORD
        exit 1
    }
} else {
    Write-Host "ERROR: SQL file not found: $sqlFilePath" -ForegroundColor Red
    Write-Host "  Please run this script from the sql-files directory" -ForegroundColor Yellow
    Remove-Item Env:\PGPASSWORD
    exit 1
}

Write-Host ""

# Step 3: Verify table was created
Write-Host "[Verification] Checking table structure..." -ForegroundColor Yellow
$verifySQL = "\d auth_users"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $verifySQL

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Table recreation completed!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart the auth-service container" -ForegroundColor Gray
Write-Host "  2. Test password change to create user in auth_users table" -ForegroundColor Gray
Write-Host ""

# Clear password environment variable
Remove-Item Env:\PGPASSWORD
