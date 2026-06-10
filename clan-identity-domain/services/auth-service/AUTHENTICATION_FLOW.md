# Authentication Flow - Updated Implementation

## Overview
The authentication system now implements a two-tier approach where users are initially authenticated against the admin service, but after their first password change, they are authenticated from the local auth_users table for improved performance.

## Authentication Flow

### 1. First Login (New User)
```
User Login Request
    ↓
Check auth_users table (not found)
    ↓
Check admin_service.usersetup_basic (found)
    ↓
Verify password
    ↓
Check is_password_change_required = true
    ↓
Return 403 - Password Change Required
```

### 2. Password Change (First Time)
```
Change Password Request
    ↓
Verify current password against admin_service
    ↓
Update password in admin_service.usersetup_basic
    ↓
Create NEW record in auth_users table
    ↓
Set is_password_change_required = false
    ↓
Return success (logout in 2 seconds)
```

### 3. Subsequent Logins
```
User Login Request
    ↓
Check auth_users table (FOUND ✓)
    ↓
Authenticate locally (faster)
    ↓
Create session and return tokens
```

### 4. Subsequent Password Changes
```
Change Password Request
    ↓
Verify current password against admin_service
    ↓
Update password in admin_service.usersetup_basic
    ↓
UPDATE existing record in auth_users table
    ↓
Return success (logout in 2 seconds)
```

## Database Tables

### auth_service.auth_users (Local Authentication)
```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY,
    admin_user_id UUID UNIQUE,  -- References admin_service user
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    employee_id VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'active',
    is_password_change_required BOOLEAN DEFAULT TRUE,
    password_changed TIMESTAMPTZ,
    roles UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### admin_service.usersetup_basic (Source of Truth)
- Contains all user data
- Updated on password changes
- Fallback for first-time authentication

## Key Service Methods

### `authenticate_user(auth_db, admin_db, email, password)`
**Priority:**
1. Check `auth_users` table first (local, faster)
2. Fallback to `admin_service.usersetup_basic` (first login)

**Returns:** User dictionary with `source` field (`auth_db` or `admin_db`)

### `create_auth_user_from_admin_data(auth_db, admin_user_data, password_hash)`
Creates a new user in `auth_users` table after first password change.

**Stores:**
- User credentials (email, username, password_hash)
- Basic info (firstname, lastname, employee_id)
- Roles from admin service
- Sets `is_password_change_required = false`

### `update_auth_user_password(auth_db, user, new_password_hash)`
Updates password for existing `auth_users` record.

## Benefits

### Performance
- ✅ Faster authentication (local database query)
- ✅ Reduced load on admin service
- ✅ Better scalability

### Security
- ✅ Passwords synced across both systems
- ✅ Admin service remains source of truth
- ✅ Local cache for quick verification

### Flexibility
- ✅ Can add auth-specific features (2FA, session limits)
- ✅ Independent password policies
- ✅ Audit trail in both systems

## Code Changes Summary

### `services/login_service.py`
1. Added `get_user_from_auth_db()` - Query auth_users table
2. Added `create_auth_user_from_admin_data()` - Create auth user after password change
3. Added `update_auth_user_password()` - Update existing auth user password
4. Updated `authenticate_user()` - Check auth_users first, fallback to admin
5. Updated `change_password()` - Update both admin and auth databases
6. Updated `login()` - Pass both database sessions

### `app/api/routes/v1/login.py`
1. Updated `change_password()` route - Now requires both `auth_db` and `admin_db`

### Models
- Using existing `models/login_user.py` (`AuthUser` model)

## Testing Checklist

- [ ] First login with default password → Password change required
- [ ] Change password → Creates record in auth_users table
- [ ] Second login → Authenticates from auth_users (check logs for "source": "auth_db")
- [ ] Change password again → Updates auth_users record
- [ ] Invalid password → Returns 401
- [ ] User not found → Returns 401
- [ ] Session creation → Works correctly
- [ ] JWT tokens → Generated correctly

## Monitoring

### Log Messages
- `"Created auth_user for {email}"` - New auth user created
- `"Updated password for existing auth_user: {email}"` - Password updated
- `"source": "auth_db"` - Authenticated from local table
- `"source": "admin_db"` - Authenticated from admin service (first login)

### Metrics to Watch
- Authentication latency (should decrease after migration)
- auth_users table growth
- Failed login attempts
- Password change frequency
