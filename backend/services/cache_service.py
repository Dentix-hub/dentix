from functools import wraps
import json
import logging
from backend.core.cache import cache

logger = logging.getLogger("smart_clinic")

def cached(key_prefix: str, expire: int = 300):
    """
    Decorator to cache function results.
    Key structure: {key_prefix}:{arg1}:{arg2}...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Build Cache Key
            # Simple key generation based on args. 
            # Note: Complex objects in args might break this str() conversion 
            # or make keys inconsistent. Use carefully for simple GET endpoints.
            cache_key = f"{key_prefix}"
            if args:
                cache_key += ":" + ":".join(str(a) for a in args)
            if kwargs:
                # Sort kwargs to ensure stable key
                cache_key += ":" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

            # 2. Try Fetch from Cache
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                # logger.info(f"CACHE HIT: {cache_key}")
                return cached_val

            # 3. Compute (Cache Miss)
            # logger.info(f"CACHE MISS: {cache_key}")
            result = func(*args, **kwargs)

            # 4. Store in Cache (if result is serializable)
            # Pydantic models need .dict() or .json() before caching usually,
            # but if the result is a dict/list (FastAPI often returns dicts), it works directly.
            # If result is Pydantic model, we might need a custom encoder.
            try:
                # Basic check: if it's a Pydantic model, convert to dict
                if hasattr(result, "dict"):
                    val_to_cache = result.dict()
                else:
                    val_to_cache = result
                
                cache.set(cache_key, val_to_cache, expire=expire)
            except Exception as e:
                logger.error(f"Failed to cache result for {cache_key}: {e}")

            return result
        return wrapper
    return decorator
