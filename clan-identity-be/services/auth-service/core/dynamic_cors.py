"""
Dynamic CORS middleware for the auth service.

Identical logic to the admin service version — origins are loaded from the
master admin DB via ADMIN_DATABASE_URL (`tenants.allowed_origins` for tenant
applications, `usersetup_basic.allowed_origins` for master/platform users),
cached in Redis, and supplemented by the CORS_ORIGINS env var.

Usage (auth service main.py):
    from core.dynamic_cors import DynamicCORSMiddleware, invalidate_cors_cache
    from core.config import settings

    # Build a session factory that connects to the admin DB.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    _admin_engine = create_engine(settings.ADMIN_DATABASE_URL, pool_pre_ping=True)
    AdminSession = sessionmaker(bind=_admin_engine)

    app.add_middleware(
        DynamicCORSMiddleware,
        session_factory=AdminSession,
        redis_client=redis_client,   # your existing Redis client or None
    )
"""

import asyncio
import json
import logging
import os
import time
from typing import Callable, Optional, Set

from sqlalchemy import text

logger = logging.getLogger(__name__)

_REDIS_KEY = "cors:allowed_origins"
_DEFAULT_TTL = 300


def _static_origins() -> Set[str]:
    raw = (os.getenv("CORS_ORIGINS") or "").strip()
    if not raw:
        return set()
    if raw == "*":
        return {"*"}
    if raw.startswith("["):
        try:
            return {str(o).strip() for o in json.loads(raw) if str(o).strip()}
        except Exception:
            return set()
    return {o.strip() for o in raw.split(",") if o.strip()}


class DynamicCORSMiddleware:
    def __init__(
        self,
        app,
        session_factory: Callable,
        redis_client=None,
        ttl: int = _DEFAULT_TTL,
    ):
        self.app = app
        self.session_factory = session_factory
        self.redis = redis_client
        self.ttl = ttl
        self._mem: Set[str] = set()
        self._mem_ts: float = 0.0
        self._lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        origin = headers.get(b"origin", b"").decode()

        if not origin:
            await self.app(scope, receive, send)
            return

        allowed = await self._is_allowed(origin)

        if not allowed:
            await self.app(scope, receive, send)
            return

        if scope.get("method") == "OPTIONS":
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": [
                    (b"access-control-allow-origin", origin.encode()),
                    (b"access-control-allow-methods", b"GET,POST,PUT,PATCH,DELETE,OPTIONS"),
                    (b"access-control-allow-headers", b"*"),
                    (b"access-control-allow-credentials", b"true"),
                    (b"access-control-max-age", b"600"),
                    (b"content-length", b"0"),
                    (b"vary", b"Origin"),
                ],
            })
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                hdrs = list(message.get("headers", []))
                hdrs += [
                    (b"access-control-allow-origin", origin.encode()),
                    (b"access-control-allow-credentials", b"true"),
                    (b"vary", b"Origin"),
                ]
                message = {**message, "headers": hdrs}
            await send(message)

        await self.app(scope, receive, send_with_cors)

    async def _is_allowed(self, origin: str) -> bool:
        static = _static_origins()
        if "*" in static or origin in static:
            return True

        # Only trust Redis when the key actually exists; a missing/expired key
        # must fall through to a DB refresh (which repopulates Redis) instead
        # of denying everything.
        if self.redis:
            try:
                if self.redis.exists(_REDIS_KEY):
                    return bool(self.redis.sismember(_REDIS_KEY, origin))
            except Exception:
                pass

        now = time.monotonic()
        if now - self._mem_ts > self.ttl:
            async with self._lock:
                if now - self._mem_ts > self.ttl:
                    await self._refresh()

        return origin in self._mem

    async def _refresh(self) -> None:
        try:
            origins = await asyncio.get_event_loop().run_in_executor(
                None, self._load_from_db
            )
            self._mem = origins
            self._mem_ts = time.monotonic()

            if self.redis and origins:
                try:
                    pipe = self.redis.pipeline()
                    pipe.delete(_REDIS_KEY)
                    pipe.sadd(_REDIS_KEY, *origins)
                    pipe.expire(_REDIS_KEY, self.ttl)
                    pipe.execute()
                except Exception as exc:
                    logger.warning("DynamicCORS: Redis update failed: %s", exc)

        except Exception as exc:
            logger.error("DynamicCORS: DB refresh failed: %s", exc)
            self._mem_ts = time.monotonic()

    def _load_from_db(self) -> Set[str]:
        """
        Union of:
          - tenants.allowed_origins          → tenant application origins
          - usersetup_basic.allowed_origins  → master/platform user origins
                                               (rows with tenant_id IS NULL)
        Each query is guarded independently so a missing table/column
        (e.g. migration not yet applied) cannot wipe out the other set.
        """
        origins: Set[str] = set()
        queries = (
            ("tenant",
             "SELECT unnest(allowed_origins) AS origin "
             "FROM tenants "
             "WHERE is_active = TRUE "
             "  AND deleted_at IS NULL "
             "  AND allowed_origins IS NOT NULL"),
            ("master-user",
             "SELECT unnest(allowed_origins) AS origin "
             "FROM usersetup_basic "
             "WHERE tenant_id IS NULL "
             "  AND status = 'active' "
             "  AND allowed_origins IS NOT NULL"),
        )
        try:
            db = self.session_factory()
            try:
                for label, query in queries:
                    try:
                        rows = db.execute(text(query)).fetchall()
                        origins.update(r[0] for r in rows if r[0])
                    except Exception as exc:
                        logger.warning("DynamicCORS: %s origins query failed: %s", label, exc)
                        try:
                            db.rollback()
                        except Exception:
                            pass
            finally:
                db.close()
        except Exception as exc:
            logger.error("DynamicCORS: DB query failed: %s", exc)
        return origins


def invalidate_cors_cache(redis_client) -> None:
    if redis_client:
        try:
            redis_client.delete(_REDIS_KEY)
        except Exception as exc:
            logger.warning("DynamicCORS: cache invalidation failed: %s", exc)
