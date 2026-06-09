# Auth-Service to Admin-Service Sync Mechanism

## Overview

This document describes the event-driven synchronization mechanism that syncs user activity data from **auth-service** (clan-identity-domain-be) to **admin-service** (clan-platform-domain-be).

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Auth-Service      │         │      Kafka       │         │   Admin-Service     │
│ (identity-domain)   │────────▶│   Event Bus      │────────▶│ (platform-domain)   │
│                     │  Publish│                  │ Consume │                     │
│  - Login Events     │         │  Topic:          │         │  - Update user_setup│
│  - Password Change  │         │  user.sync.*     │         │  - Track activity   │
│  - User Activity    │         │                  │         │  - Audit logs       │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

## Flow Direction

**auth-service → Kafka → admin-service**

When users perform authentication operations in auth-service, events are published to Kafka topics. Admin-service consumes these events and updates its `user_setup` table accordingly.

## Events Published

### 1. User Data Sync Event

**Topic:** `user.sync.admin_service.dev`

**Schema:** `UserDataSyncEvent`

**Triggered by:**
- User login (sync_action: "login")
- Password change (sync_action: "password_change")

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "user.data_sync",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "auth-service",
  "version": "1.0",
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "john_doe",
  "firstname": "John",
  "lastname": "Doe",
  "employee_id": "EMP001",
  "phone_number": "+1234567890",
  "status": "active",
  "department": "Engineering",
  "division": "Technology",
  "job_code": "ENG001",
  "manage_roles": ["user", "developer"],
  "default_dept": "Engineering",
  "reporting_to": "manager_id",
  "entities": ["entity1", "entity2"],
  "default_entity": "entity1",
  "tenant_id": "tenant_uuid",
  "sync_source": "auth-service",
  "sync_action": "login",
  "last_login_at": "2024-01-01T12:00:00Z",
  "last_login_ip": "192.168.1.1"
}
```

### 2. User Login Event

**Topic:** `auth.events.dev`

**Schema:** `UserLoginEvent`

**Purpose:** Track login activities for audit and analytics

### 3. User Password Changed Event

**Topic:** `auth.events.dev`

**Schema:** `UserPasswordChangedEvent`

**Purpose:** Track password changes for security audit

### 4. Session Created Event

**Topic:** `session.events.dev`

**Schema:** `SessionCreatedEvent`

**Purpose:** Track active sessions for security monitoring

## Implementation Details

### Auth-Service Components

#### 1. Event Schemas (`events/schemas.py`)

```python
class UserDataSyncEvent(BaseEvent):
    """Event published to sync user data to admin-service"""
    event_type: str = "user.data_sync"
    user_id: UUID
    email: str
    # ... user profile fields
    sync_action: str  # login, password_change, profile_update
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
```

#### 2. Event Publisher (`events/producers/auth_events.py`)

```python
async def publish_user_data_sync_event(
    user_id: UUID,
    email: str,
    sync_action: str,
    # ... other user fields
) -> bool:
    """Publish user data sync event to admin-service"""
    # Creates event and publishes to Kafka
```

#### 3. Service Integration (`services/login_service.py`)

Events are published asynchronously (non-blocking) after successful operations:

**On Login:**
```python
asyncio.create_task(
    publish_user_data_sync_event(
        user_id=user["id"],
        email=user["email"],
        sync_action="login",
        last_login_at=datetime.now(timezone.utc),
        last_login_ip=client_ip,
        # ... other user fields
    )
)
```

**On Password Change:**
```python
asyncio.create_task(
    publish_user_data_sync_event(
        user_id=user["id"],
        email=user["email"],
        sync_action="password_change",
        # ... other user fields
    )
)
```

## Admin-Service Consumer (To Be Implemented)

The admin-service in `clan-platform-domain-be` needs to implement a Kafka consumer to process these events.

### Recommended Implementation

#### 1. Create Kafka Consumer

```python
# admin-service/events/consumers/user_sync_consumer.py

from aiokafka import AIOKafkaConsumer
import json
import logging

logger = logging.getLogger(__name__)

USER_SYNC_TOPIC = "user.sync.admin_service.dev"

async def start_user_sync_consumer(db_session_factory):
    """Start consuming user sync events"""
    consumer = AIOKafkaConsumer(
        USER_SYNC_TOPIC,
        bootstrap_servers="localhost:9092",
        group_id="admin-service-user-sync",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    await consumer.start()
    logger.info(f"Started consuming from {USER_SYNC_TOPIC}")
    
    try:
        async for message in consumer:
            event = message.value
            await process_user_sync_event(event, db_session_factory)
    finally:
        await consumer.stop()

async def process_user_sync_event(event: dict, db_session_factory):
    """Process user sync event and update user_setup table"""
    try:
        sync_action = event.get("sync_action")
        user_id = event.get("user_id")
        
        db = db_session_factory()
        
        if sync_action == "login":
            # Update last_login_at and last_login_ip in user_setup table
            update_query = text("""
                UPDATE user_setup 
                SET last_login_at = :last_login_at,
                    last_login_ip = :last_login_ip,
                    updated_at = :updated_at
                WHERE id = :user_id
            """)
            db.execute(update_query, {
                "user_id": user_id,
                "last_login_at": event.get("last_login_at"),
                "last_login_ip": event.get("last_login_ip"),
                "updated_at": datetime.utcnow()
            })
            db.commit()
            logger.info(f"Updated login info for user {user_id}")
            
        elif sync_action == "password_change":
            # Update password_changed timestamp
            update_query = text("""
                UPDATE user_setup 
                SET password_changed_at = :timestamp,
                    updated_at = :updated_at
                WHERE id = :user_id
            """)
            db.execute(update_query, {
                "user_id": user_id,
                "timestamp": event.get("timestamp"),
                "updated_at": datetime.utcnow()
            })
            db.commit()
            logger.info(f"Updated password change info for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error processing user sync event: {str(e)}")
        db.rollback()
    finally:
        db.close()
```

#### 2. Start Consumer on Application Startup

```python
# admin-service/main.py

from events.consumers.user_sync_consumer import start_user_sync_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Admin Service...")
    
    # Start user sync consumer
    asyncio.create_task(start_user_sync_consumer(SessionLocal))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Admin Service...")
```

## Configuration

### Auth-Service Environment Variables

```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP=auth-service
```

### Admin-Service Environment Variables

```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP=admin-service-user-sync
```

## Kafka Topic Configuration

Create the required Kafka topics:

```bash
# Create user sync topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic user.sync.admin_service.dev \
  --partitions 3 \
  --replication-factor 1

# Create auth events topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic auth.events.dev \
  --partitions 3 \
  --replication-factor 1

# Create session events topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic session.events.dev \
  --partitions 3 \
  --replication-factor 1
```

## Testing

### 1. Test Event Publishing (Auth-Service)

```bash
# Start auth-service
cd services/auth-service
uvicorn main:app --reload --port 8003

# Monitor Kafka topic
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic user.sync.admin_service.dev \
  --from-beginning

# Perform login
curl -X POST http://localhost:8003/api/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Check Kafka topic for published event
```

### 2. Test Event Consumption (Admin-Service)

Once admin-service consumer is implemented:

```bash
# Start admin-service
cd clan-platform-domain-be/admin-service
uvicorn main:app --reload --port 8001

# Monitor logs for event processing
tail -f logs/admin-service.log | grep "user sync"

# Verify database updates
psql -d admin_service_db
SELECT id, email, last_login_at, last_login_ip FROM user_setup WHERE email='user@example.com';
```

## Monitoring & Observability

### Key Metrics to Track

1. **Event Publishing Rate** (auth-service)
   - Number of sync events published per minute
   - Failed publishing attempts

2. **Event Processing Rate** (admin-service)
   - Number of sync events consumed per minute
   - Processing latency
   - Failed processing attempts

3. **Kafka Health**
   - Consumer lag
   - Topic partition distribution
   - Message retention

### Logging

Both services log sync operations:

```
[INFO] Published user_data_sync event for user <uuid> with action 'login'
[INFO] Updated login info for user <uuid>
[ERROR] Failed to publish user_data_sync event: <error>
```

## Error Handling

### Auth-Service (Publisher)

- **Event publishing is non-blocking** - Login/password change operations succeed even if event publishing fails
- Failed events are logged but don't impact user operations
- Kafka NoOp mode when Kafka is disabled/unavailable

### Admin-Service (Consumer)

- **Implement retry logic** for failed event processing
- **Dead letter queue** for events that fail after max retries
- **Idempotent processing** to handle duplicate events
- **Database transaction rollback** on processing errors

## Benefits

1. **Decoupled Services** - Auth and admin services operate independently
2. **Scalability** - Kafka handles high-throughput event streams
3. **Reliability** - Events are persisted in Kafka, replayable if consumer fails
4. **Audit Trail** - Complete history of user activities
5. **Real-time Sync** - Near real-time data propagation
6. **Extensibility** - Easy to add more consumers for analytics, notifications, etc.

## Future Enhancements

1. **Bidirectional Sync** - Admin-service can publish user profile updates back to auth-service
2. **Event Versioning** - Support multiple event schema versions
3. **Event Transformation** - Add event transformation layer for complex mappings
4. **Analytics Consumer** - Separate consumer for user behavior analytics
5. **Notification Consumer** - Send notifications on specific events (password changes, suspicious logins)

## Troubleshooting

### Events Not Publishing

1. Check Kafka connection: `KAFKA_BOOTSTRAP_SERVERS` environment variable
2. Verify Kafka broker is running: `docker ps | grep kafka`
3. Check auth-service logs for Kafka errors
4. Test Kafka connectivity manually

### Events Not Consumed

1. Check admin-service consumer is started
2. Verify consumer group ID matches configuration
3. Check consumer lag: `kafka-consumer-groups.sh --describe --group admin-service-user-sync`
4. Review admin-service logs for processing errors

### Data Inconsistency

1. Check event ordering by partition key (user_id)
2. Verify idempotent processing in consumer
3. Review dead letter queue for failed events
4. Manual reconciliation if needed

## Contact & Support

For questions or issues with the sync mechanism:
- Review this documentation
- Check Kafka topic messages for debugging
- Review service logs for error details
- Contact DevOps team for Kafka infrastructure issues
