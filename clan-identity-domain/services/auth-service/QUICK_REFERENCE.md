# Auth Service - Quick Reference

## What Was Fixed (TL;DR)

1. ✅ **Missing auth_users table** → Created with correct schema
2. ✅ **Transaction errors** → Added proper rollback handling
3. ✅ **Missing user_setup_id column** → Added via schema migration

## Current Status
- 🟢 Service: **Healthy**
- 🟢 Auth Database: **Connected**
- 🟢 Admin Database: **Connected**
- 🟢 Schema: **Complete**

## Quick Commands

### Check Service Health
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/health"
```

### View Users in auth_users
```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT email, firstname, lastname, is_password_change FROM auth_users;"
```

### Check if Column Exists
```bash
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'auth_users' AND column_name = 'user_setup_id';"
```

### Restart Service
```bash
docker-compose restart auth-service
```

### View Service Logs
```bash
docker logs clan-auth-service --tail 50 -f
```

## Test Endpoints

### Test Login
```bash
curl -X POST "http://localhost:8001/api/v1/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "arun@gmail.com",
    "password": "your_password",
    "device_fingerprint": "test-device"
  }'
```

### Test Change Password
```bash
curl -X POST "http://localhost:8001/api/v1/login/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "arun@gmail.com",
    "current_password": "current_password",
    "new_password": "NewPassword123!",
    "confirm_password": "NewPassword123!"
  }'
```

## Database Access

### From Docker Container
```bash
docker exec -it clan-identity-postgres psql -U postgres -d auth_service
```

### From Host Machine
```bash
psql -h localhost -p 5433 -U postgres -d auth_service
```

## Important Files

### Modified Application Files
- `database/database.py` - Fixed model imports
- `services/login_service.py` - Added error handling

### Scripts Created
- `scripts/migrate_auth_users_schema.sql` - Schema migration
- `scripts/verify_auth_users_table.py` - Verification
- `scripts/diagnose_database_issues.py` - Diagnostics

### Documentation
- `COMPLETE_RESOLUTION_SUMMARY.md` - Full details
- `COLUMN_MISSING_FIX.md` - Column issue details
- `TRANSACTION_ERROR_FIX.md` - Transaction error details
- `AUTH_USERS_TABLE_SETUP.md` - Initial setup details

## Troubleshooting

### If Service Won't Start
```bash
# Check logs
docker logs clan-auth-service --tail 100

# Restart service
docker-compose restart auth-service

# Rebuild if needed
docker-compose up -d --build auth-service
```

### If Column Missing Error Returns
```bash
# Verify schema in Docker
docker exec clan-identity-postgres psql -U postgres -d auth_service -c "\d auth_users"

# Re-run migration
Get-Content scripts\migrate_auth_users_schema.sql | docker exec -i clan-identity-postgres psql -U postgres -d auth_service
```

### If Transaction Errors Return
Check `services/login_service.py` for proper error handling:
```python
try:
    # Database operation
    db.commit()
except Exception as e:
    db.rollback()  # This is critical!
    logger.error(f"Error: {e}")
    raise
```

## Key Concepts

### Two Database Connections
- **auth_service DB** (postgres:5432 from Docker) → Sessions, login_attempts, auth_users
- **admin_service DB** (host.docker.internal:5432) → Master user data (usersetup_basic)

### Authentication Flow
1. **First login** → Check admin_service.usersetup_basic
2. **Password change required** → User changes password
3. **Create record** → Copy to auth_service.auth_users (with user_setup_id link)
4. **Subsequent logins** → Authenticate from auth_service.auth_users (faster)

### Important Columns
- `user_setup_id` → Links to admin_service user
- `is_password_change` → TRUE = password has been changed
- `is_password_change_required` → Legacy column (opposite logic)

## Contact & Support

For issues, check:
1. Service logs: `docker logs clan-auth-service`
2. Database schema: `\d auth_users` in psql
3. Health endpoint: `http://localhost:8001/health`
4. Documentation files in this directory

---

**Last Updated:** June 10, 2026  
**Status:** ✅ All issues resolved, service operational
