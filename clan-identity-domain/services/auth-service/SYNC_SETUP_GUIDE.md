# Auth-Service Sync Setup Guide

## Quick Start

This guide explains how to set up the sync mechanism between auth-service (clan-identity-domain-be) and admin-service (clan-platform-domain-be).

## What Was Implemented

✅ **Event Schemas** - Added `UserDataSyncEvent` schema for syncing user data
✅ **Event Publishers** - Added `publish_user_data_sync_event()` function
✅ **Service Integration** - Integrated sync events into login and password change flows
✅ **Non-blocking Publishing** - Events published asynchronously without impacting user operations
✅ **Documentation** - Complete documentation and examples

## Files Modified/Created

### Modified Files
1. `events/schemas.py` - Added `UserDataSyncEvent` schema
2. `events/producers/auth_events.py` - Added sync event publisher
3. `services/login_service.py` - Integrated event publishing on login and password change

### New Files
1. `SYNC_MECHANISM.md` - Complete documentation
2. `ADMIN_SERVICE_CONSUMER_EXAMPLE.py` - Consumer implementation for admin-service
3. `SYNC_SETUP_GUIDE.md` - This file

## How It Works

```
User Login/Password Change
         ↓
   Auth-Service API
         ↓
   Login Service (Business Logic)
         ↓
   Database Update (auth_service + admin_service)
         ↓
   Publish Events to Kafka (async, non-blocking)
         ↓
   Kafka Topic: user.sync.admin_service.dev
         ↓
   Admin-Service Consumer (to be implemented)
         ↓
   Update user_setup table in admin-service
```

## Events Published

### 1. On User Login
- **Topic:** `user.sync.admin_service.dev`
- **Data:** User profile + last_login_at + last_login_ip
- **Action:** `sync_action: "login"`

### 2. On Password Change
- **Topic:** `user.sync.admin_service.dev`
- **Data:** User profile + password_changed timestamp
- **Action:** `sync_action: "password_change"`

## Setup Instructions

### Auth-Service (Already Configured)

The auth-service is already configured to publish events. Just ensure Kafka is available:

1. **Environment Variables** (`.env` file):
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

2. **Start Kafka** (if not running):
```bash
docker-compose up -d kafka
```

3. **Create Kafka Topic**:
```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic user.sync.admin_service.dev \
  --partitions 3 \
  --replication-factor 1
```

4. **Start Auth-Service**:
```bash
cd services/auth-service
uvicorn main:app --reload --port 8003
```

### Admin-Service (Needs Implementation)

The admin-service needs to consume these events. Follow these steps:

1. **Copy Consumer File**:
   - Copy `ADMIN_SERVICE_CONSUMER_EXAMPLE.py` to clan-platform-domain-be project
   - Place at: `admin-service/events/consumers/user_sync_consumer.py`

2. **Install Dependencies** (admin-service):
```bash
pip install aiokafka==0.10.0
```

Or add to `requirements.txt`:
```
aiokafka==0.10.0
```

3. **Update Admin-Service main.py**:
```python
from events.consumers.user_sync_consumer import start_user_sync_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Admin Service...")
    
    # Start user sync consumer
    consumer_task = asyncio.create_task(
        start_user_sync_consumer(SessionLocal)
    )
    app.state.consumer_task = consumer_task
    
    yield
    
    # Shutdown
    if hasattr(app.state, 'consumer_task'):
        app.state.consumer_task.cancel()

app = FastAPI(lifespan=lifespan)
```

4. **Add Database Columns** (if not exists):
```sql
-- Add to user_setup table in admin-service database
ALTER TABLE user_setup 
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(50),
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;
```

5. **Environment Variables** (admin-service `.env`):
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

6. **Start Admin-Service**:
```bash
cd clan-platform-domain-be/admin-service
uvicorn main:app --reload --port 8001
```

## Testing

### 1. Test Event Publishing (Auth-Service)

```bash
# Monitor Kafka topic
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic user.sync.admin_service.dev \
  --from-beginning

# In another terminal, perform login
curl -X POST http://localhost:8003/api/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# Check Kafka console - you should see the event
```

### 2. Test Event Consumption (Admin-Service)

```bash
# Check admin-service logs
tail -f logs/admin-service.log | grep "user sync"

# Should see:
# ✓ Started consuming from topic: user.sync.admin_service.dev
# ✓ Updated login info for user test@example.com (IP: 192.168.1.1)

# Verify database update
psql -d admin_service_db
SELECT email, last_login_at, last_login_ip 
FROM user_setup 
WHERE email='test@example.com';
```

### 3. Test Password Change Sync

```bash
# Change password
curl -X POST http://localhost:8003/api/v1/login/change-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "current_password": "password123",
    "new_password": "newpassword456",
    "confirm_password": "newpassword456"
  }'

# Verify sync in admin-service database
psql -d admin_service_db
SELECT email, password_changed_at 
FROM user_setup 
WHERE email='test@example.com';
```

## Monitoring

### Check Consumer Status

```bash
# Check consumer lag
kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group admin-service-user-sync \
  --describe

# Output shows:
# - Current offset
# - Log end offset
# - Lag (should be 0 or low)
```

### Key Metrics to Monitor

1. **Event Publishing** (auth-service logs):
   - `Published user_data_sync event for user <id> with action 'login'`

2. **Event Consumption** (admin-service logs):
   - `✓ Updated login info for user <email>`
   - `✓ Updated password change info for user <email>`

3. **Kafka Health**:
   - Consumer lag < 100 messages
   - No connection errors

## Troubleshooting

### Events Not Publishing

**Symptom:** No events appearing in Kafka topic

**Solutions:**
1. Check Kafka is running: `docker ps | grep kafka`
2. Check auth-service logs for Kafka errors
3. Verify `KAFKA_BOOTSTRAP_SERVERS` environment variable
4. Test Kafka manually:
   ```bash
   echo "test" | kafka-console-producer.sh \
     --bootstrap-server localhost:9092 \
     --topic user.sync.admin_service.dev
   ```

### Events Not Consumed

**Symptom:** Events in Kafka but not processed by admin-service

**Solutions:**
1. Check admin-service consumer started: Look for "Started consuming from topic" in logs
2. Verify consumer group ID is correct
3. Check for processing errors in admin-service logs
4. Verify database connection in admin-service

### Database Not Updated

**Symptom:** Events consumed but database not updated

**Solutions:**
1. Check user exists in user_setup table
2. Verify database columns exist (last_login_at, last_login_ip, password_changed_at)
3. Check database permissions
4. Review admin-service logs for SQL errors

## Kafka NoOp Mode

If Kafka is not available, auth-service automatically falls back to NoOp mode:
- Events are logged but not published
- User operations (login, password change) continue to work
- Sync functionality is disabled until Kafka is available

## Next Steps

1. ✅ Set up Kafka infrastructure
2. ✅ Start auth-service (already configured)
3. ⬜ Implement consumer in admin-service (copy example file)
4. ⬜ Add database columns to user_setup table
5. ⬜ Test end-to-end sync
6. ⬜ Monitor consumer lag and processing
7. ⬜ Set up alerts for sync failures

## Additional Resources

- **Full Documentation:** `SYNC_MECHANISM.md`
- **Consumer Example:** `ADMIN_SERVICE_CONSUMER_EXAMPLE.py`
- **Event Schemas:** `events/schemas.py`
- **Event Publishers:** `events/producers/auth_events.py`

## Support

For issues:
1. Check logs in both services
2. Verify Kafka topic has messages
3. Check consumer lag
4. Review this guide and SYNC_MECHANISM.md
5. Contact DevOps team for Kafka infrastructure issues
