from collections import deque
import hashlib
import logging
import os
import threading
import time

from slowapi import Limiter
from backend.core.client_ip import get_real_client_ip
from backend.core.config import get_rate_limit_mode

logger = logging.getLogger(__name__)

RATE_LIMIT_MODE = get_rate_limit_mode()
RATE_LIMITING_ENABLED = RATE_LIMIT_MODE == "enforce"

# Global limiter instance
limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=["100/minute"],
    enabled=RATE_LIMITING_ENABLED,
)

_OBSERVE_WINDOW_SECONDS = 60.0
_OBSERVE_MAX_KEYS = 10_000
_observe_lock = threading.Lock()
_observe_requests: dict[str, deque[float]] = {}


def _observe_limit() -> int:
    try:
        return max(1, min(int(os.getenv("RATE_LIMIT_OBSERVE_LIMIT", "100")), 100_000))
    except ValueError:
        logger.error("Invalid RATE_LIMIT_OBSERVE_LIMIT; using 100")
        return 100


def clear_rate_limit_observations() -> None:
    """Clear process-local observation state (primarily for deterministic tests)."""
    with _observe_lock:
        _observe_requests.clear()


def _evict_stale_observation_keys(cutoff: float) -> int:
    """Remove expired per-client windows so normal IP churn cannot exhaust capacity."""
    stale_keys: list[str] = []
    for key, requests in _observe_requests.items():
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if not requests:
            stale_keys.append(key)
    for key in stale_keys:
        _observe_requests.pop(key, None)
    return len(stale_keys)


def record_rate_limit_observation(request, *, now: float | None = None) -> bool:
    """Record a non-blocking global-rate observation without retaining raw IPs."""
    if get_rate_limit_mode() != "observe":
        return False

    timestamp = time.monotonic() if now is None else now
    client_hash = hashlib.sha256(get_real_client_ip(request).encode()).hexdigest()[:16]
    limit = _observe_limit()
    with _observe_lock:
        requests = _observe_requests.get(client_hash)
        if requests is None:
            if len(_observe_requests) >= _OBSERVE_MAX_KEYS:
                _evict_stale_observation_keys(timestamp - _OBSERVE_WINDOW_SECONDS)
                if len(_observe_requests) >= _OBSERVE_MAX_KEYS:
                    logger.warning("Rate-limit observation key capacity reached")
                    return False
            requests = deque()
            _observe_requests[client_hash] = requests
        cutoff = timestamp - _OBSERVE_WINDOW_SECONDS
        while requests and requests[0] <= cutoff:
            requests.popleft()
        requests.append(timestamp)
        would_block = len(requests) > limit
        first_excess = len(requests) == limit + 1

    if first_excess:
        logger.warning(
            "Rate-limit observe threshold exceeded",
            extra={"client_hash": client_hash, "window_seconds": 60, "limit": limit},
        )
    return would_block
