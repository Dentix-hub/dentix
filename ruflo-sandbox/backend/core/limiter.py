from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance
# Use remote address (IP) as default key
# Default global limit: 100 requests per minute (reduced for stress protection)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
