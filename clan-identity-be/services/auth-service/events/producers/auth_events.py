"""Auth event producers

Functions to publish authentication-related events to Kafka
"""
import logging
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from ..kafka_client import get_producer, KAFKA_ENABLED
from ..schemas import (
    UserLoginEvent,
    UserLogoutEvent,
    UserPasswordChangedEvent,
    TokenRefreshedEvent,
    TokenRevokedEvent,
    SessionCreatedEvent,
    SessionExpiredEvent,
    SessionRevokedEvent,
    LoginFailedEvent,
    OTPGeneratedEvent,
    OTPVerifiedEvent,
    OTPExpiredEvent,
    UserDataSyncEvent,
)

logger = logging.getLogger(__name__)

# Kafka topics
AUTH_EVENTS_TOPIC = "auth.events.dev"
SESSION_EVENTS_TOPIC = "session.events.dev"
USER_SYNC_TOPIC = "user.sync.admin_service.dev"


async def publish_user_login_event(
    user_id: UUID,
    email: str,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    login_method: str = "password",
    correlation_id: Optional[str] = None
) -> bool:
    """Publish user login event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping user_login event")
        return False

    try:
        event = UserLoginEvent(
            user_id=user_id,
            email=email,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            login_method=login_method,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()
        
        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published user_login event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish user_login event: {str(e)}")
        return False


async def publish_user_logout_event(
    user_id: UUID,
    email: str,
    session_id: Optional[str] = None,
    logout_reason: str = "user_initiated",
    correlation_id: Optional[str] = None
) -> bool:
    """Publish user logout event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping user_logout event")
        return False

    try:
        event = UserLogoutEvent(
            user_id=user_id,
            email=email,
            session_id=session_id,
            logout_reason=logout_reason,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()
        
        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published user_logout event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish user_logout event: {str(e)}")
        return False


async def publish_user_password_changed_event(
    user_id: UUID,
    email: str,
    changed_by: str = "user",
    is_first_login: bool = False,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish user password changed event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping user_password_changed event")
        return False

    try:
        event = UserPasswordChangedEvent(
            user_id=user_id,
            email=email,
            changed_by=changed_by,
            is_first_login=is_first_login,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()
        
        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published user_password_changed event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish user_password_changed event: {str(e)}")
        return False


async def publish_token_refreshed_event(
    user_id: UUID,
    email: str,
    old_token_id: Optional[str] = None,
    new_token_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish token refreshed event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping token_refreshed event")
        return False

    try:
        event = TokenRefreshedEvent(
            user_id=user_id,
            email=email,
            old_token_id=old_token_id,
            new_token_id=new_token_id,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published token_refreshed event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish token_refreshed event: {str(e)}")
        return False


async def publish_token_revoked_event(
    user_id: UUID,
    email: str,
    token_id: Optional[str] = None,
    revoked_by: str = "user",
    reason: str = "user_logout",
    correlation_id: Optional[str] = None
) -> bool:
    """Publish token revoked event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping token_revoked event")
        return False

    try:
        event = TokenRevokedEvent(
            user_id=user_id,
            email=email,
            token_id=token_id,
            revoked_by=revoked_by,
            reason=reason,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published token_revoked event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish token_revoked event: {str(e)}")
        return False


async def publish_session_created_event(
    user_id: UUID,
    email: str,
    session_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    expires_at: datetime = None,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish session created event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping session_created event")
        return False

    try:
        event = SessionCreatedEvent(
            user_id=user_id,
            email=email,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at or datetime.utcnow(),
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=SESSION_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published session_created event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish session_created event: {str(e)}")
        return False


async def publish_session_expired_event(
    user_id: UUID,
    email: str,
    session_id: str,
    expired_at: datetime = None,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish session expired event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping session_expired event")
        return False

    try:
        event = SessionExpiredEvent(
            user_id=user_id,
            email=email,
            session_id=session_id,
            expired_at=expired_at or datetime.utcnow(),
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=SESSION_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published session_expired event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish session_expired event: {str(e)}")
        return False


async def publish_session_revoked_event(
    user_id: UUID,
    email: str,
    session_id: str,
    revoked_by: str = "user",
    reason: str = "user_logout",
    correlation_id: Optional[str] = None
) -> bool:
    """Publish session revoked event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping session_revoked event")
        return False

    try:
        event = SessionRevokedEvent(
            user_id=user_id,
            email=email,
            session_id=session_id,
            revoked_by=revoked_by,
            reason=reason,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=SESSION_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published session_revoked event for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish session_revoked event: {str(e)}")
        return False


async def publish_login_failed_event(
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    failure_reason: str = "invalid_credentials",
    attempt_count: int = 1,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish login failed event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping login_failed event")
        return False

    try:
        event = LoginFailedEvent(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=failure_reason,
            attempt_count=attempt_count,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=email.encode("utf-8")
        )

        logger.info(f"Published login_failed event for email {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish login_failed event: {str(e)}")
        return False


async def publish_otp_generated_event(
    email: str,
    user_id: Optional[UUID] = None,
    otp_type: str = "login",
    expires_at: datetime = None,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish OTP generated event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping otp_generated event")
        return False

    try:
        event = OTPGeneratedEvent(
            user_id=user_id,
            email=email,
            otp_type=otp_type,
            expires_at=expires_at or datetime.utcnow(),
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=email.encode("utf-8")
        )

        logger.info(f"Published otp_generated event for email {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish otp_generated event: {str(e)}")
        return False


async def publish_otp_verified_event(
    email: str,
    user_id: Optional[UUID] = None,
    otp_type: str = "login",
    verified_at: datetime = None,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish OTP verified event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping otp_verified event")
        return False

    try:
        event = OTPVerifiedEvent(
            user_id=user_id,
            email=email,
            otp_type=otp_type,
            verified_at=verified_at or datetime.utcnow(),
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=email.encode("utf-8")
        )

        logger.info(f"Published otp_verified event for email {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish otp_verified event: {str(e)}")
        return False


async def publish_otp_expired_event(
    email: str,
    user_id: Optional[UUID] = None,
    otp_type: str = "login",
    expired_at: datetime = None,
    correlation_id: Optional[str] = None
) -> bool:
    """Publish OTP expired event"""
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping otp_expired event")
        return False

    try:
        event = OTPExpiredEvent(
            user_id=user_id,
            email=email,
            otp_type=otp_type,
            expired_at=expired_at or datetime.utcnow(),
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()

        await producer.send_and_wait(
            topic=AUTH_EVENTS_TOPIC,
            value=event_json.encode("utf-8"),
            key=email.encode("utf-8")
        )

        logger.info(f"Published otp_expired event for email {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish otp_expired event: {str(e)}")
        return False



async def publish_user_data_sync_event(
    user_id: UUID,
    email: str,
    sync_action: str,
    username: Optional[str] = None,
    firstname: Optional[str] = None,
    lastname: Optional[str] = None,
    employee_id: Optional[str] = None,
    phone_number: Optional[str] = None,
    status: str = "active",
    role_id: Optional[str] = None,
    last_login_at: Optional[datetime] = None,
    last_login_ip: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user data sync event to admin-service
    
    This event is consumed by admin-service to sync user activity data
    from auth-service back to the user_setup table in clan-platform-domain-be
    
    Args:
        user_id: User UUID
        email: User email
        sync_action: Action triggering sync (login, password_change, etc.)
        ... (user profile fields)
        last_login_at: Last login timestamp
        last_login_ip: Last login IP address
    """
    if not KAFKA_ENABLED:
        logger.debug("Kafka disabled, skipping user_data_sync event")
        return False

    try:
        event = UserDataSyncEvent(
            user_id=user_id,
            email=email,
            username=username,
            firstname=firstname,
            lastname=lastname,
            employee_id=employee_id,
            phone_number=phone_number,
            status=status,
            role_id=role_id,
            sync_action=sync_action,
            last_login_at=last_login_at,
            last_login_ip=last_login_ip,
            correlation_id=correlation_id
        )

        producer = await get_producer()
        event_json = event.model_dump_json()
        
        await producer.send_and_wait(
            topic=USER_SYNC_TOPIC,
            value=event_json.encode("utf-8"),
            key=str(user_id).encode("utf-8")
        )

        logger.info(f"Published user_data_sync event for user {user_id} with action '{sync_action}'")
        return True
    except Exception as e:
        logger.error(f"Failed to publish user_data_sync event: {str(e)}")
        return False
