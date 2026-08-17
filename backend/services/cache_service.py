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
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.cache import cache

logger = logging.getLogger("smart_clinic")

_SKIP_TYPES = (Session, AsyncSession)
_SKIP_ATTRS = ("scope", "headers", "state")


def _is_serializable_arg(value) -> bool:
    if isinstance(value, _SKIP_TYPES):
        return False
    if any(hasattr(value, attr) for attr in _SKIP_ATTRS):
        return False
    if hasattr(value, "__tablename__"):
        return False
    return True


def _build_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    parts = [prefix]
    for arg in args:
        if _is_serializable_arg(arg):
            parts.append(str(arg))
    for key, value in sorted(kwargs.items()):
        if _is_serializable_arg(value):
            parts.append(f"{key}={value}")
    return ":".join(parts)


def cached(key_prefix: str, expire: int = 300):
    def decorator(func):
        import inspect

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache_key = _build_cache_key(key_prefix, args, kwargs)
                from backend.core.cache_stampede import get_stampede_protection
                protection = get_stampede_protection()
                if protection:
                    return await protection.get_or_compute_async(
                        cache_key=cache_key,
                        compute_func=lambda: func(*args, **kwargs),
                        cache_instance=cache,
                        expire=expire,
                    )
                cached_val = cache.get(cache_key)
                if cached_val is not None:
                    return cached_val
                result = await func(*args, **kwargs)
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
            return async_wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = _build_cache_key(key_prefix, args, kwargs)
                from backend.core.cache_stampede import get_stampede_protection
                protection = get_stampede_protection()
                if protection:
                    return protection.get_or_compute(
                        cache_key=cache_key,
                        compute_func=lambda: func(*args, **kwargs),
                        cache_instance=cache,
                        expire=expire,
                    )
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


def _delete_prefix(prefix: str) -> None:
    if cache.use_redis and cache.redis_client:
        for key in cache.redis_client.scan_iter(match=f"{prefix}*"):
            cache.redis_client.delete(key)
    else:
        keys_to_delete = [k for k in cache.local_cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del cache.local_cache[key]


def invalidate_dashboard_cache(tenant_id: int):
    """Invalidate both dashboard and finance caches for one tenant.

    Business-date and timezone are part of the cache identity, so prefix
    invalidation deliberately clears all local-day variants after financial
    writes or timezone changes.
    """
    try:
        _delete_prefix(f"dashboard_stats:{tenant_id}")
        _delete_prefix(f"finance_stats:{tenant_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate dashboard/finance cache for tenant {tenant_id}: {e}")
