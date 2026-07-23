"""
Redis client for session cache and token blacklist.
All operations are fail-safe — Redis unavailability does NOT break auth.
"""
import json
import logging
from typing import Optional

import redis

try:
    from core.config import settings
except ImportError:
    from app.core.config import settings

logger = logging.getLogger(__name__)

SESSION_PREFIX = "auth:session:"
BLACKLIST_PREFIX = "auth:blacklist:"
USER_SESSIONS_PREFIX = "auth:user_sessions:"

_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    global _client
    if _client is not None:
        return _client
    if not settings.REDIS_ENABLED:
        return None
    try:
        _client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        _client.ping()
        logger.info(
            f"Redis connected at {settings.REDIS_HOST}:{settings.REDIS_PORT} db={settings.REDIS_DB}"
        )
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        _client = None
    return _client


def close_redis():
    global _client
    if _client:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


def cache_session(session_id: str, user_id: str, data: dict, ttl: int) -> bool:
    """Cache session data and register under the user's session set."""
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(f"{SESSION_PREFIX}{session_id}", ttl, json.dumps(data, default=str))
        r.sadd(f"{USER_SESSIONS_PREFIX}{user_id}", session_id)
        r.expire(f"{USER_SESSIONS_PREFIX}{user_id}", ttl)
        return True
    except Exception as e:
        logger.warning(f"Redis cache_session error: {e}")
        return False


def blacklist_token(token_hash: str, ttl: int) -> bool:
    """Add a token hash to the blacklist with the given TTL (seconds)."""
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(f"{BLACKLIST_PREFIX}{token_hash}", ttl, "1")
        return True
    except Exception as e:
        logger.warning(f"Redis blacklist_token error: {e}")
        return False


def is_token_blacklisted(token_hash: str) -> bool:
    """Return True if the token hash is in the blacklist."""
    r = get_redis()
    if not r:
        return False
    try:
        return bool(r.exists(f"{BLACKLIST_PREFIX}{token_hash}"))
    except Exception as e:
        logger.warning(f"Redis is_token_blacklisted error: {e}")
        return False


def remove_session(session_id: str, user_id: str) -> bool:
    """Remove a single session from cache and the user's session set."""
    r = get_redis()
    if not r:
        return False
    try:
        r.delete(f"{SESSION_PREFIX}{session_id}")
        r.srem(f"{USER_SESSIONS_PREFIX}{user_id}", session_id)
        return True
    except Exception as e:
        logger.warning(f"Redis remove_session error: {e}")
        return False


def remove_all_user_sessions(user_id: str) -> int:
    """Remove all cached sessions for a user. Returns number removed."""
    r = get_redis()
    if not r:
        return 0
    try:
        session_ids = r.smembers(f"{USER_SESSIONS_PREFIX}{user_id}")
        for sid in session_ids:
            r.delete(f"{SESSION_PREFIX}{sid}")
        r.delete(f"{USER_SESSIONS_PREFIX}{user_id}")
        return len(session_ids)
    except Exception as e:
        logger.warning(f"Redis remove_all_user_sessions error: {e}")
        return 0
