# Auth Service Database - Quick Start Guide

## 🚀 Initialize Database (Choose One Method)

### Method 1: Python (Recommended)
```bash
cd services/auth-service
python scripts/init_db.py
```

### Method 2: PowerShell (Windows)
```powershell
cd services/auth-service/scripts
.\init_db.ps1
```

### Method 3: Bash (Linux/Mac)
```bash
cd services/auth-service/scripts
chmod +x init_db.sh
./init_db.sh
```

### Method 4: Docker Compose
```bash
# From project root
docker-compose up -d postgres
docker-compose exec auth-service python scripts/init_db.py
```

---

## ✅ Verify Database Setup

```bash
cd services/auth-service
python scripts/verify_db.py
```

This will check:
- ✓ Database connection
- ✓ Admin database connection
- ✓ All tables exist (auth_users, sessions, login_attempts)
- ✓ Indexes are created
- ✓ Table statistics
- ✓ CRUD operations work

---

## 🗄️ Database Information

### Connection Details (Default)
- **Host:** localhost
- **Port:** 5432 (or 5433 for Docker)
- **Database:** clan_identity
- **User:** postgres
- **Password:** root

### Tables Created
1. **auth_users** - Authenticated user data (mirrors clan_platform)
2. **sessions** - User session and JWT token management
3. **login_attempts** - Security monitoring and rate limiting

---

## 🔧 Common Tasks

### Check Tables
```bash
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\dt"
```

### View Table Structure
```bash
psql -h localhost -p 5432 -U postgres -d clan_identity -c "\d auth_users"
```

### Count Records
```bash
psql -h localhost -p 5432 -U postgres -d clan_identity -c "SELECT 'auth_users' as table, COUNT(*) FROM auth_users UNION SELECT 'sessions', COUNT(*) FROM sessions UNION SELECT 'login_attempts', COUNT(*) FROM login_attempts;"
```

### Drop and Recreate
```bash
# Drop all tables
python scripts/drop_db.py

# Recreate tables
python scripts/init_db.py
```

---

## 🐛 Troubleshooting

### Cannot Connect to Database
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Check with Docker
docker-compose ps postgres
docker-compose logs postgres
```

### Tables Already Exist
The scripts use `CREATE TABLE IF NOT EXISTS`, so existing tables won't cause errors. To recreate:
```bash
python scripts/drop_db.py
python scripts/init_db.py
```

### Permission Denied
```sql
-- Grant superuser permission
ALTER USER postgres WITH SUPERUSER;

-- Or grant CREATE DATABASE
ALTER USER postgres CREATEDB;
```

---

## 📝 Environment Variables

Set these in your `.env` file or environment:

```bash
# Auth Service Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root
POSTGRES_DB=clan_identity

# Admin Service Database (for user lookup)
ADMIN_POSTGRES_HOST=localhost
ADMIN_POSTGRES_PORT=5432
ADMIN_POSTGRES_USER=postgres
ADMIN_POSTGRES_PASSWORD=root
ADMIN_DB=clan_platform
```

---

## 🎯 Next Steps

After database initialization:

1. **Start the Auth Service**
   ```bash
   cd services/auth-service
   python main.py
   ```

2. **Check Service Health**
   ```bash
   curl http://localhost:8001/health
   ```

3. **View API Docs**
   - Swagger UI: http://localhost:8001/docs
   - ReDoc: http://localhost:8001/redoc

4. **Test Database Connection**
   ```bash
   python scripts/test_admin_db_connection.ps1
   ```

---

## 📚 Need More Help?

- Full documentation: `scripts/README.md`
- Migration guide: `scripts/migrations/README.md`
- Database schema: `scripts/init_db.sql`

---

## ⚠️ Production Deployment

Before deploying to production:

1. ✓ Change default passwords
2. ✓ Use environment variables for credentials
3. ✓ Enable SSL/TLS for database connections
4. ✓ Set up regular backups
5. ✓ Configure connection pooling
6. ✓ Review security settings
7. ✓ Test in staging environment first

**Backup Command:**
```bash
pg_dump -h localhost -U postgres -d clan_identity > backup_$(date +%Y%m%d).sql
```
