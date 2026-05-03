"""
Advanced Rate Limiting for Smart Clinic.

Provides multiple rate limiting strategies:
- Fixed Window
- Sliding Window
- Token Bucket
- Adaptive (based on system load)

Usage:
    from backend.core.rate_limiter import rate_limiter

    @app.get("/api/endpoint")
    @rate_limiter.limit("10/minute")
    async def endpoint():
        pass
"""

from fastapi import Request, HTTPException
from functools import wraps
from collections import defaultdict
from typing import Callable, Optional, Dict, Tuple
import threading
import time
import re
import logging

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
        self.retry_after = retry_after


class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple strategies.

    Supports in-memory storage (for single instance) or can be extended
    for Redis-based distributed rate limiting.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._fixed_window: Dict[
            str, Tuple[int, float]
        ] = {}  # key -> (count, window_start)
        self._sliding_window: Dict[str, list] = defaultdict(list)  # key -> [timestamps]
        self._token_buckets: Dict[
            str, Tuple[float, float]
        ] = {}  # key -> (tokens, last_update)

    @staticmethod
    def _parse_rate(rate_string: str) -> Tuple[int, int]:
        """Parse rate string like '10/minute' into (count, seconds)."""
        match = re.match(r"(\d+)/(second|minute|hour|day)", rate_string)
        if not match:
            raise ValueError(f"Invalid rate format: {rate_string}")

        count = int(match.group(1))
        unit = match.group(2)

        unit_seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

        return count, unit_seconds[unit]

    @staticmethod
    def _get_key(request: Request, key_func: Optional[Callable] = None) -> str:
        """Get rate limit key from request."""
        if key_func:
            return key_func(request)

        # Default: use IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def fixed_window(self, rate_string: str, key_func: Optional[Callable] = None):
        """
        Fixed window rate limiting decorator.

        Simple and efficient, but can have burst issues at window boundaries.
        """
        max_requests, window_seconds = self._parse_rate(rate_string)

        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                key = self._get_key(request, key_func)
                now = time.time()

                with self._lock:
                    if key in self._fixed_window:
                        count, window_start = self._fixed_window[key]

                        if now - window_start > window_seconds:
                            # New window
                            self._fixed_window[key] = (1, now)
                        elif count >= max_requests:
                            retry_after = int(window_seconds - (now - window_start))
                            raise RateLimitExceeded(retry_after)
                        else:
                            self._fixed_window[key] = (count + 1, window_start)
                    else:
                        self._fixed_window[key] = (1, now)

                return await func(request, *args, **kwargs)

            return wrapper

        return decorator

    def sliding_window(self, rate_string: str, key_func: Optional[Callable] = None):
        """
        Sliding window rate limiting decorator.

        More accurate than fixed window, tracks individual requests.
        """
        max_requests, window_seconds = self._parse_rate(rate_string)

        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                key = self._get_key(request, key_func)
                now = time.time()
                window_start = now - window_seconds

                with self._lock:
                    # Remove old entries
                    self._sliding_window[key] = [
                        ts for ts in self._sliding_window[key] if ts > window_start
                    ]

                    if len(self._sliding_window[key]) >= max_requests:
                        # Calculate when oldest request expires
                        oldest = min(self._sliding_window[key])
                        retry_after = int(oldest + window_seconds - now) + 1
                        raise RateLimitExceeded(retry_after)

                    self._sliding_window[key].append(now)

                return await func(request, *args, **kwargs)

            return wrapper

        return decorator

    def token_bucket(
        self,
        capacity: int,
        refill_rate: float,  # tokens per second
        key_func: Optional[Callable] = None,
    ):
        """
        Token bucket rate limiting decorator.

        Allows bursts up to capacity, then limits to refill rate.
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                key = self._get_key(request, key_func)
                now = time.time()

                with self._lock:
                    if key in self._token_buckets:
                        tokens, last_update = self._token_buckets[key]
                        # Refill tokens
                        elapsed = now - last_update
                        tokens = min(capacity, tokens + elapsed * refill_rate)
                    else:
                        tokens = capacity

                    if tokens < 1:
                        wait_time = (1 - tokens) / refill_rate
                        raise RateLimitExceeded(int(wait_time) + 1)

                    tokens -= 1
                    self._token_buckets[key] = (tokens, now)

                return await func(request, *args, **kwargs)

            return wrapper

        return decorator

    def limit(self, rate_string: str, key_func: Optional[Callable] = None):
        """
        Default rate limiting (uses sliding window).

        Usage:
            @rate_limiter.limit("10/minute")
            async def endpoint():
                pass
        """
        return self.sliding_window(rate_string, key_func)


# Singleton instance
rate_limiter = AdvancedRateLimiter()


# ============================================
# KEY FUNCTIONS
# ============================================


def by_user(request: Request) -> str:
    """Rate limit by authenticated user."""
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    return f"ip:{request.client.host}"


def by_tenant(request: Request) -> str:
    """Rate limit by tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return f"tenant:{tenant_id}"
    return f"ip:{request.client.host}"


def by_endpoint(request: Request) -> str:
    """Rate limit by endpoint path."""
    return f"endpoint:{request.url.path}:{request.client.host}"
