"""
Simple in-memory cache for frequently accessed data.
Use for data that doesn't change often (procedures, labs, etc.)
"""

from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import hashlib
import json

_cache: Dict[str, Dict[str, Any]] = {}


def get_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(key_data.encode()).hexdigest()


def cache_response(ttl_seconds: int = 60):
    """
    Decorator to cache function responses.

    Usage:
        @cache_response(ttl_seconds=300)  # Cache for 5 minutes
        def get_procedures(db: Session, tenant_id: int):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            cache_key = f"{func.__name__}:{get_cache_key(*args[1:], **kwargs)}"  # Skip db session

            # Check cache
            if cache_key in _cache:
                cached = _cache[cache_key]
                if datetime.utcnow() < cached["expires"]:
                    return cached["data"]
                else:
                    # Expired, remove
                    del _cache[cache_key]

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = {
                "data": result,
                "expires": datetime.utcnow() + timedelta(seconds=ttl_seconds),
            }
            return result

        return wrapper

    return decorator


def invalidate_cache(prefix: Optional[str] = None):
    """
    Invalidate cache entries.

    Args:
        prefix: If provided, only invalidate keys starting with this prefix.
                If None, invalidate ALL cache entries.
    """
    global _cache
    if prefix is None:
        _cache = {}
    else:
        keys_to_delete = [k for k in _cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del _cache[k]


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for debugging."""
    now = datetime.utcnow()
    valid_entries = sum(1 for v in _cache.values() if now < v["expires"])
    expired_entries = len(_cache) - valid_entries

    return {
        "total_entries": len(_cache),
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "keys": list(_cache.keys())[:10],  # Show first 10 keys only
    }
