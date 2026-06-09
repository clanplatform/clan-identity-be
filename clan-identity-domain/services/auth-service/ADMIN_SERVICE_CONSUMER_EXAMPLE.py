"""
User Sync Consumer for Admin-Service
=====================================

This file should be placed in the clan-platform-domain-be admin-service project.
Path: admin-service/events/consumers/user_sync_consumer.py

This consumer listens to user sync events from auth-service and updates
the user_setup table in the admin-service database.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Callable
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Kafka configuration
USER_SYNC_TOPIC = "user.sync.admin_service.dev"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
CONSUMER_GROUP_ID = "admin-service-user-sync"


async def start_user_sync_consumer(db_session_factory: Callable[[], Session]):
    """
    Start consuming user sync events from auth-service
    
    Args:
        db_session_factory: Factory function to create database sessions
    """
    consumer = None
    
    try:
        # Initialize Kafka consumer
        consumer = AIOKafkaConsumer(
            USER_SYNC_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000
        )
        
        # Start the consumer
        await consumer.start()
        logger.info(f"✓ Started consuming from topic: {USER_SYNC_TOPIC}")
        logger.info(f"  Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"  Consumer group: {CONSUMER_GROUP_ID}")
        
        # Process messages
        async for message in consumer:
            try:
                event = message.value
                logger.debug(f"Received event: {event.get('event_type')} for user {event.get('email')}")
                
                # Process the sync event
                await process_user_sync_event(event, db_session_factory)
                
            except Exception as e:
                logger.error(f"Error processing message from topic {message.topic}: {str(e)}")
                # Continue processing next messages
                continue
                
    except KafkaError as e:
        logger.error(f"Kafka error in consumer: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in consumer: {str(e)}")
        raise
    finally:
        # Cleanup
        if consumer:
            await consumer.stop()
            logger.info("User sync consumer stopped")


async def process_user_sync_event(event: dict, db_session_factory: Callable[[], Session]):
    """
    Process a user sync event and update the user_setup table
    
    Args:
        event: Event payload from Kafka
        db_session_factory: Factory function to create database sessions
    """
    db = None
    
    try:
        sync_action = event.get("sync_action")
        user_id = event.get("user_id")
        email = event.get("email")
        
        if not user_id or not email:
            logger.warning(f"Invalid event: missing user_id or email")
            return
        
        # Create database session
        db = db_session_factory()
        
        if sync_action == "login":
            # Update last login information
            await handle_login_sync(db, event)
            
        elif sync_action == "password_change":
            # Update password change information
            await handle_password_change_sync(db, event)
            
        else:
            logger.warning(f"Unknown sync_action: {sync_action}")
            
    except Exception as e:
        logger.error(f"Error processing user sync event for user {event.get('user_id')}: {str(e)}")
        if db:
            db.rollback()
        # Don't raise - we want to continue processing other events
        
    finally:
        if db:
            db.close()


async def handle_login_sync(db: Session, event: dict):
    """
    Handle login sync event - update last login timestamp and IP
    
    Args:
        db: Database session
        event: Event payload
    """
    user_id = event.get("user_id")
    email = event.get("email")
    last_login_at = event.get("last_login_at")
    last_login_ip = event.get("last_login_ip")
    
    try:
        # Check if user exists
        check_query = text("""
            SELECT id FROM user_setup WHERE id = :user_id
        """)
        result = db.execute(check_query, {"user_id": user_id}).fetchone()
        
        if not result:
            logger.warning(f"User {user_id} ({email}) not found in user_setup table - skipping sync")
            return
        
        # Update last login info
        update_query = text("""
            UPDATE user_setup 
            SET last_login_at = :last_login_at,
                last_login_ip = :last_login_ip,
                updated_at = :updated_at
            WHERE id = :user_id
        """)
        
        db.execute(update_query, {
            "user_id": user_id,
            "last_login_at": last_login_at,
            "last_login_ip": last_login_ip,
            "updated_at": datetime.utcnow()
        })
        db.commit()
        
        logger.info(f"✓ Updated login info for user {email} (IP: {last_login_ip})")
        
    except Exception as e:
        logger.error(f"Error updating login info for user {user_id}: {str(e)}")
        db.rollback()
        raise


async def handle_password_change_sync(db: Session, event: dict):
    """
    Handle password change sync event - update password changed timestamp
    
    Args:
        db: Database session
        event: Event payload
    """
    user_id = event.get("user_id")
    email = event.get("email")
    timestamp = event.get("timestamp")
    
    try:
        # Check if user exists
        check_query = text("""
            SELECT id FROM user_setup WHERE id = :user_id
        """)
        result = db.execute(check_query, {"user_id": user_id}).fetchone()
        
        if not result:
            logger.warning(f"User {user_id} ({email}) not found in user_setup table - skipping sync")
            return
        
        # Update password changed timestamp
        update_query = text("""
            UPDATE user_setup 
            SET password_changed_at = :timestamp,
                updated_at = :updated_at
            WHERE id = :user_id
        """)
        
        db.execute(update_query, {
            "user_id": user_id,
            "timestamp": timestamp,
            "updated_at": datetime.utcnow()
        })
        db.commit()
        
        logger.info(f"✓ Updated password change info for user {email}")
        
    except Exception as e:
        logger.error(f"Error updating password change info for user {user_id}: {str(e)}")
        db.rollback()
        raise


# ============================================================================
# Integration with Admin-Service Main Application
# ============================================================================
"""
To integrate this consumer into your admin-service, add the following to main.py:

1. Import the consumer:
   from events.consumers.user_sync_consumer import start_user_sync_consumer

2. Start consumer on application startup:

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Admin Service...")
    
    # Start user sync consumer in background
    consumer_task = asyncio.create_task(
        start_user_sync_consumer(SessionLocal)
    )
    app.state.consumer_task = consumer_task
    
    yield
    
    # Shutdown
    logger.info("Shutting down Admin Service...")
    if hasattr(app.state, 'consumer_task'):
        app.state.consumer_task.cancel()
        try:
            await app.state.consumer_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Admin Service",
    lifespan=lifespan
)

3. Add dependencies to requirements.txt or pyproject.toml:
   aiokafka==0.10.0
   
4. Add environment variables to .env:
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092
"""


# ============================================================================
# Testing the Consumer
# ============================================================================
"""
To test the consumer standalone:

1. Start Kafka:
   docker-compose up -d kafka

2. Create the topic:
   kafka-topics.sh --create \\
     --bootstrap-server localhost:9092 \\
     --topic user.sync.admin_service.dev \\
     --partitions 3 \\
     --replication-factor 1

3. Run the consumer:
   python -m asyncio user_sync_consumer.py

4. In another terminal, trigger a login in auth-service:
   curl -X POST http://localhost:8003/api/v1/login/ \\
     -H "Content-Type: application/json" \\
     -d '{"email": "user@example.com", "password": "password123"}'

5. Check consumer logs for processing confirmation

6. Verify database update:
   psql -d admin_service_db
   SELECT id, email, last_login_at, last_login_ip FROM user_setup WHERE email='user@example.com';
"""


if __name__ == "__main__":
    # For standalone testing
    import sys
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Replace with your actual database URL
    DATABASE_URL = "postgresql://user:password@localhost:5432/admin_service_db"
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(start_user_sync_consumer(SessionLocal))
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
        sys.exit(0)
