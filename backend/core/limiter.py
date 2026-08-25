import os
from slowapi import Limiter
from backend.core.client_ip import get_real_client_ip

# Determine if rate limiting is enabled
_enabled_str = os.getenv("RATE_LIMITING_ENABLED", "true").lower()
RATE_LIMITING_ENABLED = _enabled_str in ("true", "1", "yes")

# Global limiter instance
limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=["100/minute"],
    enabled=RATE_LIMITING_ENABLED,
)
