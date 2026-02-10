"""
Circuit Breaker Pattern for External API Calls
Prevents cascading failures when the AI provider (Groq) is down.
"""

import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, fast reject
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.opened_at = 0

    def record_success(self):
        """Call this on successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failures = 0
            logger.info("Circuit Breaker recovered (CLOSED)")
        elif self.state == CircuitState.CLOSED:
            # Decay failures to zero over time
            self.failures = 0

    def record_failure(self):
        """Call this on exception."""
        self.failures += 1
        self.last_failure_time = time.time()

        if (
            self.state == CircuitState.CLOSED
            and self.failures >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            logger.warning(f"Circuit Breaker OPENED due to {self.failures} failures")

    def allow_request(self) -> bool:
        """Check if request should proceed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            now = time.time()
            if now - self.opened_at > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit Breaker check (HALF_OPEN)")
                return True  # Allow one test request
            return False

        if self.state == CircuitState.HALF_OPEN:
            # In half-open, we strictly allow only if not currently processing another test
            # For simplicity here, we assume sequential or loose concurrency
            return True

        return True


# Singleton instance
ai_circuit_breaker = CircuitBreaker()
