"""Redis client for caching and message queues."""

import redis.asyncio as redis
from app.config import settings
from app.utils.logger import logger
import json
from typing import Optional, Any


class RedisClient:
    """Redis client wrapper for async operations."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await redis.from_url(settings.redis_url)
            await self.redis.ping()
            logger.info("✅ Redis connection successful")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("✅ Redis disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"❌ Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis with TTL."""
        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"❌ Redis set error: {e}")
            return False

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        """
        Set a raw (already serialized) value with TTL.

        Difference from `set()`: this does not run `json.dumps`. Services that
        serialize their own payload use this; `set()` is for plain objects.
        """
        try:
            await self.redis.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"❌ Redis setex error: {e}")
            return False

    async def keys(self, pattern: str) -> list:
        """List keys matching a glob pattern (used for cache invalidation)."""
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            logger.error(f"❌ Redis keys error: {e}")
            return []

    async def delete(self, *keys: str) -> bool:
        """Delete one or more keys from Redis."""
        if not keys:
            return True
        try:
            await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"❌ Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ Redis exists error: {e}")
            return False

    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            return False


# Global instance
redis_client = RedisClient()
