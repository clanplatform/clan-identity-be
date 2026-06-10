# Verification script to confirm auth_users schema is correct in Docker PostgreSQL

Write-Host "========================================================================"
Write-Host "Verifying auth_users schema in Docker PostgreSQL"
Write-Host "========================================================================"
Write-Host ""

# Check if user_setup_id exists
Write-Host "1. Checking if user_setup_id column exists..."
$result = docker exec clan-identity-postgres psql -U postgres -d auth_service -t -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'auth_users' AND column_name = 'user_setup_id';"
if ($result -match "user_setup_id") {
    Write-Host "   ✓ user_setup_id column exists" -ForegroundColor Green
} else {
    Write-Host "   ✗ user_setup_id column MISSING" -ForegroundColor Red
    exit 1
}

# Check if is_password_change exists
Write-Host ""
Write-Host "2. Checking if is_password_change column exists..."
$result = docker exec clan-identity-postgres psql -U postgres -d auth_service -t -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'auth_users' AND column_name = 'is_password_change';"
if ($result -match "is_password_change") {
    Write-Host "   ✓ is_password_change column exists" -ForegroundColor Green
} else {
    Write-Host "   ✗ is_password_change column MISSING" -ForegroundColor Red
    exit 1
}

# Check other required columns
Write-Host ""
Write-Host "3. Checking other required columns..."
$requiredColumns = @(
    'firstname', 'lastname', 'email', 'username', 'employee_id',
    'password_hash', 'status', 'department', 'division', 'job_code',
    'manage_roles', 'entities', 'default_entity'
)

$allPresent = $true
foreach ($col in $requiredColumns) {
    $result = docker exec clan-identity-postgres psql -U postgres -d auth_service -t -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'auth_users' AND column_name = '$col';"
    if ($result -match $col) {
        Write-Host "   ✓ $col" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $col MISSING" -ForegroundColor Red
        $allPresent = $false
    }
}

# Check auth-service health
Write-Host ""
Write-Host "4. Checking auth-service health..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get -TimeoutSec 5
    if ($response.status -eq "healthy") {
        Write-Host "   ✓ Auth-service is healthy" -ForegroundColor Green
        Write-Host "   - Auth Database: $($response.auth_database)"
        Write-Host "   - Admin Database: $($response.admin_database)"
    } else {
        Write-Host "   ⚠ Auth-service status: $($response.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Cannot reach auth-service" -ForegroundColor Red
    Write-Host "   Error: $_"
}

# Show current user count
Write-Host ""
Write-Host "5. Current data in auth_users table..."
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT COUNT(*) as user_count FROM auth_users;"

Write-Host ""
Write-Host "========================================================================"
if ($allPresent) {
    Write-Host "✓ All verifications passed!" -ForegroundColor Green
    Write-Host "========================================================================"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "1. Test the change-password endpoint"
    Write-Host "2. Test login with a first-time user"
    Write-Host "3. Verify user record is created in auth_users table"
} else {
    Write-Host "✗ Some verifications failed!" -ForegroundColor Red
    Write-Host "========================================================================"
    exit 1
}
