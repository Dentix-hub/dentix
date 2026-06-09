import functools
from typing import Callable, Any
from fastapi import Request, HTTPException
from backend.core.cache import cache

def idempotent(expire: int = 60) -> Callable:
    """
    Decorator for FastAPI endpoints to ensure idempotency.
    It expects a FastAPI Request object in the arguments.
    It reads the 'Idempotency-Key' header. If present, it checks the cache.
    If the key exists, it returns a 409 Conflict (or could return the cached response).
    If the key does not exist, it executes the endpoint and caches a placeholder.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Find the request object
            request: Request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # If no request object found, skip idempotency check
                return func(*args, **kwargs)

            idempotency_key = request.headers.get("Idempotency-Key")
            if not idempotency_key:
                # If no key provided, allow request
                return func(*args, **kwargs)

            # Namespace the key with tenant if available, or user ID
            tenant_id = getattr(request.state, "tenant_id", "global")
            full_key = f"idempotency:{tenant_id}:{idempotency_key}"

            # Check if key exists
            if cache.get(full_key):
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate request detected. An operation with this Idempotency-Key is already being processed or completed."
                )

            # Mark key as processing
            cache.set(full_key, "processing", expire=expire)

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # On failure, we might want to remove the key to allow retry
                cache.delete(full_key)
                raise e
                
        return wrapper
    return decorator
