"""Shared Redis client utilities."""

import redis.asyncio as aioredis
from typing import Optional, Any
import json
import os


class RedisClient:
    """Redis client wrapper."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Establish Redis connection."""
        self.client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        
        if not isinstance(value, str):
            value = json.dumps(value)
        
        return await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> int:
        """Delete key from Redis."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        
        return await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        
        return await self.client.exists(key) > 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        
        return await self.client.expire(key, seconds)
