# Recreate auth_users Table

This guide explains how to recreate the `auth_users` table in the `auth_service` database.

## Why Recreate?

The `auth_users` table schema has been updated to mirror the `usersetup_basic` table structure from admin_service. This ensures all user fields are properly synchronized between both databases.

## Prerequisites

- PostgreSQL is running (either locally or in Docker)
- Database `auth_service` exists
- You have access to the database (user: postgres, password: root)

## Option 1: Using PowerShell Script (Recommended if psql is installed)

Navigate to the sql-files directory and run:

```powershell
cd C:\Users\arung\OneDrive\Documents\clan_archi\identity-domain-be\clan-identity-domain-be\clan-identity-domain\services\sql-files

.\recreate_auth_users_table.ps1
```

## Option 2: Using Docker (Recommended if psql is NOT installed)

Navigate to the sql-files directory and run:

```powershell
cd C:\Users\arung\OneDrive\Documents\clan_archi\identity-domain-be\clan-identity-domain-be\clan-identity-domain\services\sql-files

.\recreate_auth_users_table_docker.ps1
```

**Note:** Make sure your PostgreSQL container name is `postgres`. If different, edit the script and change `$CONTAINER_NAME`.

## Option 3: Manual Steps

If you prefer to run commands manually:

### Using psql (if installed):

```powershell
# Set password
$env:PGPASSWORD = "root"

# Drop old table
psql -h localhost -p 5432 -U postgres -d auth_service -c "DROP TABLE IF EXISTS auth_users CASCADE;"

# Create new table
psql -h localhost -p 5432 -U postgres -d auth_service -f 01_create_auth_users_table.sql

# Verify
psql -h localhost -p 5432 -U postgres -d auth_service -c "\d auth_users"

# Clear password
Remove-Item Env:\PGPASSWORD
```

### Using Docker:

```powershell
# Drop old table
docker exec -i postgres psql -U postgres -d auth_service -c "DROP TABLE IF EXISTS auth_users CASCADE;"

# Copy SQL file
docker cp 01_create_auth_users_table.sql postgres:/tmp/

# Create new table
docker exec -i postgres psql -U postgres -d auth_service -f /tmp/01_create_auth_users_table.sql

# Verify
docker exec -i postgres psql -U postgres -d auth_service -c "\d auth_users"

# Cleanup
docker exec -i postgres rm /tmp/01_create_auth_users_table.sql
```

## Verification

After running the script, you should see output showing the new table structure with these key fields:

- `id` (UUID, Primary Key)
- `user_setup_id` (UUID, references admin_service user)
- Personal info: `firstname`, `lastname`, `employee_id`, `username`, `email`, `phone_number`
- Authentication: `password_hash`, `password_changed`, `is_password_change`
- Employment: `status`, `start_date`, `end_date`, `tem_employee`
- Organization: `department`, `division`, `job_code`, `manage_roles`
- Settings: `default_dept`, `reporting_to`, `entities`, `default_entity`
- Views: `view`, `dashboard_view`
- Timestamps: `created_at`, `updated_at`

## After Recreation

1. **Restart auth-service container:**
   ```powershell
   docker restart auth-service
   ```
   Or if running locally:
   ```powershell
   # Stop the service (Ctrl+C) and restart it
   ```

2. **Test the authentication flow:**
   - Login with a user who needs to change password (first login)
   - Change the password
   - Check that user data is now in `auth_users` table:
     ```sql
     SELECT * FROM auth_users;
     ```

3. **Subsequent logins** should now authenticate from the local `auth_users` table for better performance.

## Troubleshooting

### Error: "psql: command not found"
- Use Option 2 (Docker method) instead
- Or install PostgreSQL client tools

### Error: "docker: command not found"
- Install Docker Desktop
- Or use Option 1 (psql method)

### Error: "FATAL: database does not exist"
- Make sure the `auth_service` database exists
- Create it if needed:
  ```powershell
  docker exec -i postgres psql -U postgres -c "CREATE DATABASE auth_service;"
  ```

### Error: "could not connect to server"
- Check if PostgreSQL is running:
  ```powershell
  docker ps | findstr postgres
  ```
- Check if port 5432 is accessible

### Table is created but still empty after password change
- Check auth-service logs for errors
- Verify the AuthUser model matches the table schema
- Restart auth-service after table recreation

## Need Help?

Check the application logs for detailed error messages:
```powershell
docker logs auth-service -f
```
