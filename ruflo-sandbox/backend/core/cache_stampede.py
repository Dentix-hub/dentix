"""
Cache Stampede (Thundering Herd) Protection
============================================

Uses Distributed Mutex Locks to ensure only ONE request
computes a cache value on miss. Others wait and get the cached result.

Flow:
    1. Cache Miss detected
    2. First request acquires lock (Redis SET NX EX + UUID)
    3. Other requests poll cache every 50ms
    4. First request computes, caches, releases lock
    5. Waiting requests get cache hit
"""

import time
import uuid
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("smart_clinic")

# Lua script: delete key ONLY if the stored value matches ours.
# Prevents releasing a lock that was already expired and re-acquired.
_RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class StampedeProtection:
    """Prevents Cache Stampede using Distributed Mutex Locks."""

    LOCK_TIMEOUT_SECONDS = 30
    RETRY_DELAY_SECONDS = 0.05  # 50ms
    MAX_RETRIES = 100           # 50ms × 100 = 5s max wait

    def __init__(self, redis_client):
        self.redis = redis_client

    def _acquire_lock(self, key: str) -> tuple[bool, str]:
        lock_key = f"lock:{key}"
        lock_value = str(uuid.uuid4())
        try:
            acquired = self.redis.set(
                lock_key,
                lock_value,
                nx=True,
                ex=self.LOCK_TIMEOUT_SECONDS,
            ) is not None
            return acquired, lock_value
        except Exception as e:
            logger.error(f"Lock acquire failed for {key}: {e}")
            return False, ""

    def _release_lock(self, key: str, lock_value: str):
        lock_key = f"lock:{key}"
        try:
            self.redis.eval(_RELEASE_LOCK_LUA, 1, lock_key, lock_value)
        except Exception as e:
            logger.error(f"Lock release failed for {key}: {e}")

    def get_or_compute(
        self,
        cache_key: str,
        compute_func: Callable[[], Any],
        cache_instance,
        expire: int = 300,
    ) -> Any:
        """
        Return cached value or compute it with stampede protection.

        Only ONE caller computes on miss; the rest wait for the cache
        to be populated and then return the cached value.
        """
        # 1. Fast path — cache hit
        cached_val = cache_instance.get(cache_key)
        if cached_val is not None:
            return cached_val

        # 2. Try to acquire lock
        acquired, lock_value = self._acquire_lock(cache_key)

        if acquired:
            try:
                # Double-check after acquiring (another process may have set it)
                cached_val = cache_instance.get(cache_key)
                if cached_val is not None:
                    return cached_val

                # Compute
                result = compute_func()

                # Serialize for cache
                if hasattr(result, "model_dump"):
                    val_to_cache = result.model_dump()
                elif hasattr(result, "dict"):
                    val_to_cache = result.dict()
                else:
                    val_to_cache = result

                cache_instance.set(cache_key, val_to_cache, expire=expire)
                logger.info(f"Stampede: computed and cached {cache_key}")
                return result
            except Exception:
                raise
            finally:
                self._release_lock(cache_key, lock_value)

        # 3. Lock not acquired — poll cache until available
        for attempt in range(self.MAX_RETRIES):
            time.sleep(self.RETRY_DELAY_SECONDS)
            cached_val = cache_instance.get(cache_key)
            if cached_val is not None:
                logger.debug(
                    f"Stampede: got cached {cache_key} after "
                    f"{(attempt + 1) * self.RETRY_DELAY_SECONDS:.2f}s"
                )
                return cached_val

        # 4. Timeout fallback — compute + cache anyway
        logger.warning(f"Stampede: timeout waiting for {cache_key}, computing fallback")
        result = compute_func()
        try:
            val = result.model_dump() if hasattr(result, "model_dump") else result
            cache_instance.set(cache_key, val, expire=expire)
        except Exception:
            pass
        return result


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_protection: Optional[StampedeProtection] = None


def init_stampede_protection(redis_client) -> None:
    """Call once at startup after Redis is connected."""
    global _protection
    _protection = StampedeProtection(redis_client)
    logger.info("Cache Stampede Protection initialized")


def get_stampede_protection() -> Optional[StampedeProtection]:
    """Return the global StampedeProtection instance (or None)."""
    return _protection
