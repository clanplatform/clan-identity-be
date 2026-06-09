# Auth-Service to Admin-Service Sync Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLAN IDENTITY DOMAIN                                │
│                         (identity-domain-be)                                │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         Auth-Service                                  │ │
│  │                         Port: 8003                                    │ │
│  │                                                                       │ │
│  │  ┌─────────────────┐         ┌──────────────────┐                   │ │
│  │  │  API Routes     │         │  Login Service   │                   │ │
│  │  │  /login/        │────────▶│  Business Logic  │                   │ │
│  │  │  /change-pass.. │         │                  │                   │ │
│  │  └─────────────────┘         └────────┬─────────┘                   │ │
│  │                                       │                              │ │
│  │                              ┌────────▼─────────┐                    │ │
│  │                              │  Event Publishers│                    │ │
│  │                              │  (Async/Non-    │                    │ │
│  │                              │   Blocking)     │                    │ │
│  │                              └────────┬─────────┘                    │ │
│  │                                       │                              │ │
│  └───────────────────────────────────────┼──────────────────────────────┘ │
│                                          │                                 │
│  ┌────────────────┐                      │  ┌────────────────────────┐    │
│  │  auth_service  │                      │  │  admin_service         │    │
│  │  Database      │                      │  │  Database (Read)       │    │
│  │                │                      │  │                        │    │
│  │  - sessions    │                      │  │  - usersetup_basic     │    │
│  │  - login_att.. │                      │  │    (authenticate)      │    │
│  │  - otps        │                      │  │                        │    │
│  └────────────────┘                      │  └────────────────────────┘    │
│                                          │                                 │
└──────────────────────────────────────────┼─────────────────────────────────┘
                                           │
                                           │ Publish Events
                                           ▼
                              ┌────────────────────────┐
                              │                        │
                              │    Apache Kafka        │
                              │    Event Bus           │
                              │                        │
                              │  Topics:               │
                              │  ├─ user.sync.*        │
                              │  ├─ auth.events.*      │
                              │  └─ session.events.*   │
                              │                        │
                              └────────┬───────────────┘
                                       │ Consume Events
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CLAN PLATFORM DOMAIN                                  │
│                       (platform-domain-be)                                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         Admin-Service                                 │ │
│  │                         Port: 8001                                    │ │
│  │                                                                       │ │
│  │  ┌─────────────────┐                                                 │ │
│  │  │  Kafka Consumer │                                                 │ │
│  │  │  (Background)   │                                                 │ │
│  │  │                 │                                                 │ │
│  │  │  - Consumes     │                                                 │ │
│  │  │    sync events  │                                                 │ │
│  │  │  - Updates DB   │                                                 │ │
│  │  └────────┬────────┘                                                 │ │
│  │           │                                                          │ │
│  │           ▼                                                          │ │
│  │  ┌──────────────────┐                                               │ │
│  │  │   user_setup     │                                               │ │
│  │  │   Database       │                                               │ │
│  │  │                  │                                               │ │
│  │  │  Updated Fields: │                                               │ │
│  │  │  - last_login_at │                                               │ │
│  │  │  - last_login_ip │                                               │ │
│  │  │  - password_ch.. │                                               │ │
│  │  └──────────────────┘                                               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Event Flow Sequence

### Login Flow with Sync

```
User                Auth-Service         Kafka               Admin-Service
  │                      │                 │                      │
  ├─POST /login/────────▶│                 │                      │
  │                      │                 │                      │
  │                      ├─Authenticate────┤                      │
  │                      │ (admin_service  │                      │
  │                      │  usersetup)     │                      │
  │                      │                 │                      │
  │                      ├─Create Session──┤                      │
  │                      │ (auth_service)  │                      │
  │                      │                 │                      │
  │◀─200 OK (tokens)─────┤                 │                      │
  │                      │                 │                      │
  │                      ├─Publish Event──▶│                      │
  │                      │ (async)         │                      │
  │                      │                 │                      │
  │                      │                 ├─Consume Event───────▶│
  │                      │                 │                      │
  │                      │                 │                      ├─Update DB
  │                      │                 │                      │ (user_setup)
  │                      │                 │                      │
  │                      │                 │ ◀─ACK────────────────┤
  │                      │                 │                      │
```

### Password Change Flow with Sync

```
User                Auth-Service         Kafka               Admin-Service
  │                      │                 │                      │
  ├─POST /change-pass───▶│                 │                      │
  │                      │                 │                      │
  │                      ├─Verify User─────┤                      │
  │                      │ (admin_service) │                      │
  │                      │                 │                      │
  │                      ├─Update Password─┤                      │
  │                      │ (admin_service  │                      │
  │                      │  usersetup)     │                      │
  │                      │                 │                      │
  │◀─200 OK──────────────┤                 │                      │
  │                      │                 │                      │
  │                      ├─Publish Event──▶│                      │
  │                      │ (async)         │                      │
  │                      │                 │                      │
  │                      │                 ├─Consume Event───────▶│
  │                      │                 │                      │
  │                      │                 │                      ├─Update DB
  │                      │                 │                      │ (password_
  │                      │                 │                      │  changed_at)
  │                      │                 │                      │
  │                      │                 │ ◀─ACK────────────────┤
```

## Data Flow

### What Gets Synced

#### On Login (sync_action: "login")
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "john_doe",
  "firstname": "John",
  "lastname": "Doe",
  "employee_id": "EMP001",
  "status": "active",
  "last_login_at": "2024-01-01T12:00:00Z",
  "last_login_ip": "192.168.1.1",
  "sync_action": "login",
  ...
}
```

#### On Password Change (sync_action: "password_change")
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "john_doe",
  "timestamp": "2024-01-01T12:05:00Z",
  "sync_action": "password_change",
  ...
}
```

## Database Schema Changes

### Admin-Service user_setup Table

Add these columns to track user activity:

```sql
ALTER TABLE user_setup 
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(50),
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_setup_last_login_at 
ON user_setup(last_login_at);

CREATE INDEX IF NOT EXISTS idx_user_setup_password_changed_at 
ON user_setup(password_changed_at);
```

## Component Details

### Auth-Service Components

```
events/
├── schemas.py                  # Event schemas (UserDataSyncEvent)
├── kafka_client.py            # Kafka producer/consumer client
└── producers/
    └── auth_events.py         # Event publishers
                               # - publish_user_data_sync_event()
                               # - publish_user_login_event()
                               # - publish_user_password_changed_event()

services/
└── login_service.py           # Business logic with event publishing
                               # - login() → publishes sync event
                               # - change_password() → publishes sync event

app/api/routes/v1/
└── login.py                   # API endpoints
```

### Admin-Service Components (To Be Implemented)

```
events/
├── kafka_client.py            # Kafka consumer client
└── consumers/
    └── user_sync_consumer.py  # Consumer for user sync events
                               # - start_user_sync_consumer()
                               # - process_user_sync_event()
                               # - handle_login_sync()
                               # - handle_password_change_sync()

main.py                        # FastAPI app with consumer startup
```

## Kafka Topics

### user.sync.admin_service.dev
- **Purpose:** Sync user data from auth-service to admin-service
- **Partitions:** 3
- **Key:** user_id (UUID)
- **Retention:** 7 days
- **Consumers:** admin-service

### auth.events.dev
- **Purpose:** Authentication events for audit and analytics
- **Partitions:** 3
- **Key:** user_id or email
- **Retention:** 30 days
- **Consumers:** analytics-service, audit-service

### session.events.dev
- **Purpose:** Session lifecycle events
- **Partitions:** 3
- **Key:** user_id
- **Retention:** 7 days
- **Consumers:** monitoring-service

## Error Handling & Resilience

### Auth-Service (Publisher)

```
┌─────────────────┐
│  User Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DB Operation   │  ◀── Critical Path (must succeed)
│  (Synchronous)  │
└────────┬────────┘
         │ Success
         ▼
┌─────────────────┐
│  Return 200 OK  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Publish Event  │  ◀── Best Effort (async, logged if fails)
│  (Async/NoOp)   │
└─────────────────┘
```

**Features:**
- Non-blocking event publishing
- NoOp mode if Kafka unavailable
- User operations succeed regardless of event publishing
- Errors logged but don't impact user

### Admin-Service (Consumer)

```
┌─────────────────┐
│  Receive Event  │
└────────┬────────┘
         │
         ▼
     ┌───────┐
     │ Valid?│─No─▶ Log & Skip
     └───┬───┘
         │ Yes
         ▼
┌─────────────────┐
│  Process Event  │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Success? │
    └────┬─────┘
         │
    Yes──┼──No
         │   │
         │   └─▶ Rollback → Log Error → Continue
         │
         ▼
┌─────────────────┐
│  Commit Offset  │
└─────────────────┘
```

**Features:**
- Idempotent processing (safe to retry)
- Transaction rollback on error
- Continues processing next events
- Consumer lag monitoring

## Monitoring & Observability

### Metrics to Track

#### Auth-Service
- `auth_sync_events_published_total` - Total sync events published
- `auth_sync_events_failed_total` - Failed publish attempts
- `auth_sync_event_publish_duration` - Time to publish events

#### Admin-Service
- `admin_sync_events_consumed_total` - Total sync events consumed
- `admin_sync_events_processed_total` - Successfully processed events
- `admin_sync_events_failed_total` - Failed processing attempts
- `admin_sync_consumer_lag` - Consumer lag in messages
- `admin_sync_processing_duration` - Time to process events

### Health Checks

#### Auth-Service `/health`
```json
{
  "status": "healthy",
  "kafka": "healthy",
  "event_publishing": "enabled"
}
```

#### Admin-Service `/health`
```json
{
  "status": "healthy",
  "kafka_consumer": "running",
  "consumer_lag": 0,
  "last_event_processed": "2024-01-01T12:00:00Z"
}
```

## Scalability

### Horizontal Scaling

```
Auth-Service Instances      Kafka Partitions      Admin-Service Instances
                                                   
┌──────────┐                   ┌────┐              ┌──────────┐
│ Auth-1   │──────────────────▶│ P0 │◀─────────────│ Admin-1  │
└──────────┘                   └────┘              └──────────┘
                                                   
┌──────────┐                   ┌────┐              ┌──────────┐
│ Auth-2   │──────────────────▶│ P1 │◀─────────────│ Admin-2  │
└──────────┘                   └────┘              └──────────┘
                                                   
┌──────────┐                   ┌────┐              ┌──────────┐
│ Auth-3   │──────────────────▶│ P2 │◀─────────────│ Admin-3  │
└──────────┘                   └────┘              └──────────┘
```

- **Auth-Service:** Scale horizontally (load balancer)
- **Kafka:** 3 partitions (can increase)
- **Admin-Service Consumer:** Max 3 instances (one per partition)

## Security Considerations

1. **Data in Transit**
   - Kafka SSL/TLS encryption
   - Service-to-Kafka authentication (SASL)

2. **Data at Rest**
   - Kafka encryption at rest
   - Database encryption

3. **Access Control**
   - Kafka ACLs for topic access
   - Service authentication via API keys/certs

4. **Sensitive Data**
   - No passwords in events
   - Hash or encrypt PII if needed
   - Short retention periods

## Future Enhancements

1. **Bidirectional Sync**
   - Admin-service publishes user updates → Auth-service consumes

2. **Event Replay**
   - Replay events for data recovery
   - Backfill historical data

3. **Dead Letter Queue**
   - Failed events sent to DLQ
   - Manual review and reprocessing

4. **Schema Registry**
   - Versioned event schemas
   - Schema evolution support

5. **Change Data Capture (CDC)**
   - Database changes automatically captured
   - Published as events

6. **Event Sourcing**
   - Complete audit trail
   - Time-travel queries
   - Event replay capabilities
