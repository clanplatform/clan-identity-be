# Test Change Password Functionality

## Issue Resolved
✅ Fixed NOT NULL constraint violation for `is_active` column

### What Was Wrong
The database table had legacy columns with NOT NULL constraints but no default values:
- `is_active` (no default)
- `is_verified` (no default)
- `two_factor_enabled` (no default)
- `is_password_change_required` (no default)
- `failed_login_attempts` (no default)

When creating a new user record in `auth_users`, these columns were not being set, causing:
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation) 
null value in column "is_active" of relation "auth_users" violates not-null constraint
```

### Solution Applied
Added default values to all legacy NOT NULL columns:
```sql
ALTER TABLE auth_users ALTER COLUMN is_active SET DEFAULT true;
ALTER TABLE auth_users ALTER COLUMN is_verified SET DEFAULT false;
ALTER TABLE auth_users ALTER COLUMN two_factor_enabled SET DEFAULT false;
ALTER TABLE auth_users ALTER COLUMN is_password_change_required SET DEFAULT false;
ALTER TABLE auth_users ALTER COLUMN failed_login_attempts SET DEFAULT '0';
```

## Test the Fix

### Prerequisites
1. Have a user in the `admin_service.usersetup_basic` table
2. User should require password change (first login)

### Test Scenario 1: Change Password for First-Time User

**Using PowerShell:**
```powershell
$body = @{
    email = "ani@gmail.com"
    current_password = "current_password_here"
    new_password = "NewPassword123!"
    confirm_password = "NewPassword123!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/login/change-password" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

**Using curl:**
```bash
curl -X POST "http://localhost:8001/api/v1/login/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ani@gmail.com",
    "current_password": "current_password_here",
    "new_password": "NewPassword123!",
    "confirm_password": "NewPassword123!"
  }'
```

**Expected Result:**
```json
{
  "message": "The password is successfully changed. You will logout in 2 sec",
  "email": "ani@gmail.com",
  "show_popup": true,
  "logout_in_seconds": 2
}
```

### Test Scenario 2: Verify User Created in auth_users

After successful password change, verify the user was created:

```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT email, firstname, lastname, user_setup_id, is_password_change, is_active, is_verified FROM auth_users WHERE email = 'ani@gmail.com';"
```

**Expected Result:**
- User record should exist
- `is_password_change` should be `true`
- `is_active` should be `true` (with default)
- `is_verified` should be `false` (with default)
- `user_setup_id` should link to admin_service user

### Test Scenario 3: Login After Password Change

**Using PowerShell:**
```powershell
$body = @{
    email = "ani@gmail.com"
    password = "NewPassword123!"
    device_fingerprint = "test-device"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/login" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

**Expected Result:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "is_password_change": true,
  "expires_in": 3600,
  "session_id": "uuid-here",
  "user": {
    "id": "uuid",
    "email": "ani@gmail.com",
    "username": "aneesh",
    "firstname": "Aneesh",
    "lastname": "sherlin",
    "employee_id": "GYP001",
    "status": "active",
    "roles": [...],
    "admin_user_id": "uuid"
  }
}
```

## Verification Commands

### Check Legacy Column Defaults
```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'auth_users' AND column_name IN ('is_active', 'is_verified', 'two_factor_enabled', 'failed_login_attempts');"
```

### Check All Users in auth_users
```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT email, firstname, lastname, is_password_change, is_active FROM auth_users ORDER BY created_at DESC;"
```

### Monitor Service Logs
```bash
docker logs clan-auth-service -f
```

## Troubleshooting

### If Still Getting NOT NULL Errors

1. **Check if defaults are set:**
   ```bash
   docker exec clan-identity-postgres psql -U postgres -d auth_service -c "\d auth_users"
   ```

2. **Re-run the default value migration:**
   ```bash
   docker exec clan-identity-postgres psql -U postgres -d auth_service -c "ALTER TABLE auth_users ALTER COLUMN is_active SET DEFAULT true; ALTER TABLE auth_users ALTER COLUMN is_verified SET DEFAULT false;"
   ```

3. **Restart the service:**
   ```bash
   docker-compose restart auth-service
   ```

### If Password Change Fails

1. **Check admin_service has the user:**
   ```bash
   docker exec clan-identity-postgres psql -U postgres -d admin_service -c "SELECT email, firstname, lastname, is_password_change FROM usersetup_basic WHERE email = 'ani@gmail.com';"
   ```

2. **Verify current password is correct**

3. **Check service logs for detailed error:**
   ```bash
   docker logs clan-auth-service --tail 50
   ```

## Summary

### Changes Made
- ✅ Added default values to 5 legacy NOT NULL columns
- ✅ Updated existing records with default values
- ✅ Restarted auth-service

### Current Status
- 🟢 Service: Healthy
- 🟢 Auth Database: Connected
- 🟢 Legacy columns: Have defaults
- 🟢 Ready for testing

### Next Step
**Test the change-password endpoint with a real user!**

---

**Date:** June 10, 2026  
**Issue:** NOT NULL constraint violation on is_active  
**Status:** ✅ RESOLVED
