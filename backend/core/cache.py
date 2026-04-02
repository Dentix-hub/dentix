import os
import redis
import json
import logging
from typing import Any, Optional

logger = logging.getLogger("smart_clinic")


class CacheManager:
    """
    Smart Cache Manager that tries to use Redis, but falls back to in-memory dictionary
    if Redis is not configured or unreachable.
    """

    def __init__(self):
        self.redis_client = None
        self.local_cache = {}
        self.use_redis = False

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Quick ping to verify connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info(f"✅ Redis Cache Connected: {redis_url}")

                # Initialize Stampede Protection
                from backend.core.cache_stampede import init_stampede_protection
                init_stampede_protection(self.redis_client)
            except Exception as e:
                logger.warning(f"⚠️ Redis Connection Failed (Using Local Memory): {e}")
                self.use_redis = False
        else:
            logger.info("ℹ️ No REDIS_URL found. Using Local Memory Cache.")

    def get_redis_client(self) -> Optional[redis.Redis]:
        """Return the Redis client if available."""
        if self.use_redis:
            return self.redis_client
        return None

    def get(self, key: str) -> Optional[Any]:
        try:
            if self.use_redis and self.redis_client:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val)
                return None
            else:
                val = self.local_cache.get(key)
                if val:
                    return json.loads(val)
                return None
        except Exception as e:
            logger.error(f"Cache GET Error: {e}")
            return None

    def set(self, key: str, value: Any, expire: int = 300):
        try:
            val_str = json.dumps(value, default=str)
            if self.use_redis and self.redis_client:
                self.redis_client.setex(key, expire, val_str)
            else:
                self.local_cache[key] = val_str
        except Exception as e:
            logger.error(f"Cache SET Error: {e}")

    def delete(self, key: str):
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.delete(key)
            else:
                if key in self.local_cache:
                    del self.local_cache[key]
        except Exception as e:
            logger.error(f"Cache DELETE Error: {e}")


# Global Instance
cache = CacheManager()
