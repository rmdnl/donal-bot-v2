"""Circuit breaker: proteksi API/order failure dengan auto-recovery."""
import time, logging
logger = logging.getLogger("circuit_breaker")

class CircuitBreaker:
    def __init__(self, max_failures=5, cooldown_seconds=60, name="api"):
        self.max_failures = max_failures
        self.cooldown = cooldown_seconds
        self.name = name
        self._failures = 0
        self._open_until = 0.0

    def record_success(self):
        self._failures = 0

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.max_failures:
            self._open_until = time.monotonic() + self.cooldown
            logger.warning(f"circuit_open name={self.name} cooldown={self.cooldown}s")

    def allow(self):
        if self._open_until and time.monotonic() < self._open_until:
            return False
        if self._open_until:
            self._open_until = 0.0
            self._failures = 0
            logger.info(f"circuit_closed name={self.name}")
        return True
