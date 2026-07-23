import logging
import os
import asyncio
from typing import Optional

# Try to import Kafka libraries with fallback
try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except Exception as e:
    logging.warning(f"Kafka libraries not available: {e}")
    KAFKA_AVAILABLE = False
    class AIOKafkaProducer:
        pass
    class AIOKafkaConsumer:
        pass
    class KafkaError(Exception):
        pass

logger = logging.getLogger(__name__)

# Kafka configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "auth-service")

# Check if Kafka is enabled
KAFKA_ENABLED = bool(KAFKA_BOOTSTRAP_SERVERS and KAFKA_BOOTSTRAP_SERVERS.strip() and KAFKA_AVAILABLE)

# Producer singleton
_producer = None

async def get_producer():
    """
    Returns a singleton Kafka producer instance
    """
    global _producer
    if _producer is None:
        if not KAFKA_ENABLED:
            logger.warning("Kafka is disabled. Using NoOpKafkaProducer.")
            _producer = NoOpKafkaProducer()
        else:
            if not KAFKA_AVAILABLE:
                logger.warning("Kafka libraries not available. Using NoOpKafkaProducer.")
                _producer = NoOpKafkaProducer()
            else:
                try:
                    # Initialize real Kafka producer
                    _producer = AIOKafkaProducer(
                        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                        value_serializer=lambda v: v if isinstance(v, bytes) else v.encode('utf-8'),
                        key_serializer=lambda k: k if isinstance(k, bytes) else k.encode('utf-8') if k else None,
                        retry_backoff_ms=100,
                        request_timeout_ms=10000,
                        connections_max_idle_ms=540000,
                        max_batch_size=16384
                    )
                    await _producer.start()
                    logger.info("Real Kafka producer initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Kafka producer: {str(e)}")
                    logger.warning("Falling back to NoOpKafkaProducer")
                    _producer = NoOpKafkaProducer()

    return _producer

async def get_consumer(topic: str):
    """
    Creates a new Kafka consumer for the specified topic

    Args:
        topic: The Kafka topic to subscribe to
    """
    if not KAFKA_ENABLED:
        logger.warning(f"Kafka is disabled. Using NoOpKafkaConsumer for topic {topic}.")
        return NoOpKafkaConsumer(topic)

    if not KAFKA_AVAILABLE:
        logger.warning(f"Kafka libraries not available. Using NoOpKafkaConsumer for topic {topic}.")
        return NoOpKafkaConsumer(topic)

    try:
        # Initialize real Kafka consumer
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            consumer_timeout_ms=1000,
            max_poll_records=500,
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000
        )
        await consumer.start()
        logger.info(f"Real Kafka consumer initialized successfully for topic {topic}")
        return consumer
    except Exception as e:
        logger.error(f"Failed to initialize Kafka consumer for topic {topic}: {str(e)}")
        logger.warning(f"Falling back to NoOpKafkaConsumer for topic {topic}")
        return NoOpKafkaConsumer(topic)

async def close_producer():
    """
    Closes the Kafka producer
    """
    global _producer
    if _producer is not None:
        try:
            if hasattr(_producer, 'stop'):
                await _producer.stop()
            _producer = None
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {str(e)}")
            _producer = None

# No-op implementations for when Kafka is disabled
class NoOpKafkaProducer:
    async def send_and_wait(self, topic, value, key=None):
        logger.debug(f"NoOp producer: Message to topic {topic} discarded (Kafka disabled)")
        return {"topic": topic, "partition": 0, "offset": 0}
    
    async def stop(self):
        logger.debug("NoOp producer: Stopped")

class NoOpKafkaConsumer:
    def __init__(self, topic):
        self.topic = topic
        logger.debug(f"NoOp consumer: Created for topic {self.topic} (Kafka disabled)")
    
    async def start(self):
        logger.debug(f"NoOp consumer: Started for topic {self.topic} (Kafka disabled)")
    
    async def getmany(self, timeout_ms=1000):
        # Always return empty dict when Kafka is disabled
        return {}
    
    async def stop(self):
        logger.debug(f"NoOp consumer: Stopped for topic {self.topic} (Kafka disabled)")

# Utility functions for Kafka health checks
async def check_kafka_health():
    """
    Check if Kafka is available and healthy
    """
    if not KAFKA_ENABLED or not KAFKA_AVAILABLE:
        return False

    try:
        # Try to create a temporary producer to test connection
        test_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            request_timeout_ms=5000
        )
        await test_producer.start()
        await test_producer.stop()
        return True
    except Exception as e:
        logger.error(f"Kafka health check failed: {str(e)}")
        return False

