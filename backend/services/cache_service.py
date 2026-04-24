"""
Cache Service — @cached decorator with Stampede Protection.

Usage:
    @cached(key_prefix="dashboard_stats", expire=60)
    def get_dashboard_stats(request, db, current_user):
        ...

Cache key is built ONLY from serializable kwargs (tenant_id, doctor_id, etc.)
and explicitly skips non-serializable objects (Session, Request, User model).
"""

from functools import wraps
import logging
from sqlalchemy.orm import Session
from backend.core.cache import cache

logger = logging.getLogger("smart_clinic")

# Types that should never appear in a cache key
_SKIP_TYPES = (Session,)

# Attribute names that signal a non-serializable object
_SKIP_ATTRS = ("scope", "headers", "state")  # Request-like objects


def _is_serializable_arg(value) -> bool:
    """Return False for DB sessions, HTTP requests, ORM models, etc."""
    if isinstance(value, _SKIP_TYPES):
        return False
    if any(hasattr(value, attr) for attr in _SKIP_ATTRS):
        return False
    if hasattr(value, "__tablename__"):  # SQLAlchemy model
        return False
    return True


def _build_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """Build a stable, serializable cache key."""
    parts = [prefix]

    for arg in args:
        if _is_serializable_arg(arg):
            parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        if _is_serializable_arg(value):
            parts.append(f"{key}={value}")

    return ":".join(parts)


def cached(key_prefix: str, expire: int = 300):
    """
    Decorator to cache function results with Stampede Protection.

    - Builds a clean cache key (no Session/Request objects).
    - Uses StampedeProtection lock when Redis is available.
    - Falls back to simple get/set when Redis is not available.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _build_cache_key(key_prefix, args, kwargs)

            # Try stampede-protected path
            from backend.core.cache_stampede import get_stampede_protection
            protection = get_stampede_protection()

            if protection:
                return protection.get_or_compute(
                    cache_key=cache_key,
                    compute_func=lambda: func(*args, **kwargs),
                    cache_instance=cache,
                    expire=expire,
                )

            # Fallback: simple get/set (no stampede protection)
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            result = func(*args, **kwargs)

            if hasattr(result, "model_dump"):
                val_to_cache = result.model_dump()
            elif hasattr(result, "dict"):
                val_to_cache = result.dict()
            else:
                val_to_cache = result

            try:
                cache.set(cache_key, val_to_cache, expire=expire)
            except Exception as e:
                logger.error(f"Failed to cache {cache_key}: {e}")

            return result

        return wrapper

    return decorator


def invalidate_dashboard_cache(tenant_id: int):
    """Invalidate dashboard cache keys for a given tenant."""
    try:
        prefix = f"dashboard_stats:{tenant_id}"
        if cache.use_redis and cache.redis_client:
            # Scan and delete matching keys
            for key in cache.redis_client.scan_iter(match=f"{prefix}:*"):
                cache.redis_client.delete(key)
            # Also delete exact key if no doctor_id suffix
            cache.redis_client.delete(prefix)
        else:
            # Local memory: delete keys starting with prefix
            keys_to_delete = [k for k in cache.local_cache.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del cache.local_cache[k]
    except Exception as e:
        logger.error(f"Failed to invalidate dashboard cache for tenant {tenant_id}: {e}")
