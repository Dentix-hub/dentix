"""
Rate Limiter
Manages usage quotas per tenant/user.
"""

import time
from typing import Dict
from collections import defaultdict
from ..config import QUOTA_LIMITS


class RateLimiter:
    """
    In-memory rate limiter using sliding window log.
    For production, this should use Redis.
    """

    def __init__(self):
        # Maps tenant_id -> list of timestamps
        self._requests: Dict[int, List[float]] = defaultdict(list)
        # Maps tenant_id -> plan_type
        self._plans: Dict[int, str] = defaultdict(lambda: "basic")

    def check_limit(self, tenant_id: int) -> bool:
        """
        Check if tenant has exceeded daily quota.
        Returns True if allowed, False if blocked.
        """
        now = time.time()
        window = 86400  # 24 hours

        # Cleanup old requests
        self._requests[tenant_id] = [
            t for t in self._requests[tenant_id] if now - t < window
        ]

        # Get limit
        plan = self._plans.get(tenant_id, "basic")
        limit = QUOTA_LIMITS.get(plan, 50)

        if len(self._requests[tenant_id]) >= limit:
            return False

        return True

    def record_usage(self, tenant_id: int):
        """Record a successful request."""
        self._requests[tenant_id].append(time.time())

    def set_tenant_plan(self, tenant_id: int, plan: str):
        """Update tenant plan for limit checking."""
        self._plans[tenant_id] = plan


# Global instance
rate_limiter = RateLimiter()
