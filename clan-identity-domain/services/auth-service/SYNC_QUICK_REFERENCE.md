# Auth-Service Sync - Quick Reference Card

## 📋 At a Glance

| Aspect | Details |
|--------|---------|
| **Status** | ✅ Auth-service complete, ⏳ Admin-service pending |
| **Method** | Event-driven via Kafka |
| **Direction** | Auth-service → Admin-service |
| **Impact** | Zero (non-blocking, async) |
| **Kafka Topic** | `user.sync.admin_service.dev` |

---

## 🎯 What Gets Synced

### On Login
```
✅ last_login_at
✅ last_login_ip
✅ Full user profile
```

### On Password Change
```
✅ password_changed_at
✅ Full user profile
```

---

## 🚀 Quick Start

### Auth-Service (Ready ✅)
```bash
# Ensure Kafka is running
docker-compose up -d kafka

# Create topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic user.sync.admin_service.dev \
  --partitions 3 \
  --replication-factor 1

# Start service
uvicorn main:app --reload --port 8003
```

### Admin-Service (Needs Setup ⏳)
```bash
# 1. Copy consumer
cp ADMIN_SERVICE_CONSUMER_EXAMPLE.py \
   <admin-service>/events/consumers/user_sync_consumer.py

# 2. Install dependency
pip install aiokafka

# 3. Add DB columns
ALTER TABLE user_setup ADD COLUMN last_login_at TIMESTAMP;
ALTER TABLE user_setup ADD COLUMN last_login_ip VARCHAR(50);
ALTER TABLE user_setup ADD COLUMN password_changed_at TIMESTAMP;

# 4. Update main.py (see SYNC_SETUP_GUIDE.md)

# 5. Start service
uvicorn main:app --reload --port 8001
```

---

## 🧪 Testing

### Publish Test
```bash
# Monitor Kafka
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic user.sync.admin_service.dev

# Login
curl -X POST http://localhost:8003/api/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "pass"}'

# Check Kafka console for event ✅
```

### Consume Test
```bash
# Check admin-service logs
tail -f logs/admin-service.log | grep "sync"

# Login again
# Should see: ✓ Updated login info for user test@example.com

# Verify DB
psql -d admin_service_db
SELECT email, last_login_at, last_login_ip FROM user_setup;
```

---

## 📊 Event Schema

```json
{
  "event_type": "user.data_sync",
  "user_id": "uuid",
  "email": "user@example.com",
  "sync_action": "login",
  "last_login_at": "2024-01-01T12:00:00Z",
  "last_login_ip": "192.168.1.1",
  "firstname": "John",
  "lastname": "Doe",
  "status": "active"
}
```

---

## 🔍 Monitoring

### Auth-Service Logs
```
✅ Published user_data_sync event for user <id> with action 'login'
❌ Failed to publish user_data_sync event: <error>
```

### Admin-Service Logs
```
✅ Started consuming from topic: user.sync.admin_service.dev
✅ Updated login info for user test@example.com (IP: 192.168.1.1)
❌ Error processing user sync event for user <id>: <error>
```

### Kafka Health
```bash
# Check consumer lag
kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group admin-service-user-sync \
  --describe

# Lag should be 0 or low
```

---

## 🐛 Troubleshooting

### Problem: Events not publishing

**Check:**
- [ ] Kafka running? `docker ps | grep kafka`
- [ ] Topic exists? `kafka-topics.sh --list`
- [ ] Auth-service logs for errors?
- [ ] `KAFKA_BOOTSTRAP_SERVERS` set in .env?

**Fix:**
```bash
# Restart Kafka
docker-compose restart kafka

# Recreate topic
kafka-topics.sh --create --topic user.sync.admin_service.dev ...
```

### Problem: Events not consumed

**Check:**
- [ ] Admin-service consumer started?
- [ ] Consumer group exists?
- [ ] Database columns exist?
- [ ] Admin-service logs for errors?

**Fix:**
```bash
# Check consumer status
kafka-consumer-groups.sh --describe --group admin-service-user-sync

# Check logs
tail -f logs/admin-service.log
```

### Problem: Database not updated

**Check:**
- [ ] User exists in user_setup table?
- [ ] Columns exist? (last_login_at, last_login_ip, password_changed_at)
- [ ] SQL errors in logs?

**Fix:**
```sql
-- Add missing columns
ALTER TABLE user_setup ADD COLUMN last_login_at TIMESTAMP;
ALTER TABLE user_setup ADD COLUMN last_login_ip VARCHAR(50);
ALTER TABLE user_setup ADD COLUMN password_changed_at TIMESTAMP;
```

---

## 📚 Documentation

| Document | When to Use |
|----------|-------------|
| `README_SYNC.md` | Start here - overview |
| `SYNC_SETUP_GUIDE.md` | Setting up admin-service |
| `SYNC_MECHANISM.md` | Deep dive technical details |
| `SYNC_ARCHITECTURE.md` | Architecture & diagrams |
| `ADMIN_SERVICE_CONSUMER_EXAMPLE.py` | Copy this for admin-service |
| `CHANGES_SUMMARY.md` | See what changed |
| `SYNC_QUICK_REFERENCE.md` | This card - quick lookup |

---

## ⚙️ Configuration

### Auth-Service .env
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Admin-Service .env
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

---

## 🔢 Key Metrics

### Publisher (Auth-Service)
- Events published per minute
- Failed publish attempts
- Publish latency

### Consumer (Admin-Service)
- Events consumed per minute
- Consumer lag
- Processing latency
- Failed processing attempts

---

## 📞 Need Help?

1. Check this quick reference
2. Review `SYNC_SETUP_GUIDE.md`
3. Check service logs
4. Verify Kafka health
5. Review `SYNC_MECHANISM.md` for details
6. Contact DevOps for Kafka issues

---

## ✅ Checklist

### Auth-Service
- [x] Event schema added
- [x] Event publisher added
- [x] Login integration
- [x] Password change integration
- [x] Documentation complete

### Admin-Service
- [ ] Copy consumer file
- [ ] Install aiokafka
- [ ] Add DB columns
- [ ] Update main.py
- [ ] Test end-to-end
- [ ] Set up monitoring

---

## 🎯 Success Criteria

✅ User logs in → Event in Kafka within 1 second  
✅ Admin-service processes event within 1 second  
✅ Database updated with last_login_at and last_login_ip  
✅ No errors in logs  
✅ Consumer lag < 100 messages  
✅ User operations not impacted  

---

## 📈 Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Publish Time | < 100ms | Async, non-blocking |
| Consumer Lag | < 100 msgs | Real-time processing |
| Processing Time | < 500ms | Per event |
| DB Update Time | < 200ms | Per event |
| User Impact | 0ms | Fully async |

---

**Version:** 1.0  
**Last Updated:** June 9, 2026  
**Print this card for quick reference! 📄**
