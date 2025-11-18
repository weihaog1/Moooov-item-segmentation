"""Circuit breaker pattern for service resilience."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation - requests flow through
    OPEN = "open"  # Service failing - reject requests immediately
    HALF_OPEN = "half_open"  # Testing recovery - allow limited requests


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    Monitors service health and "opens the circuit" when failure threshold
    is reached, preventing further requests until the service recovers.

    States:
        CLOSED: Normal operation, all requests go through
        OPEN: Service is failing, reject all requests immediately
        HALF_OPEN: Testing if service recovered, allow one request

    Example:
        breaker = CircuitBreaker(threshold=5, timeout=60)

        if breaker.is_open():
            raise CircuitOpenError("Service unavailable")

        try:
            result = await make_request()
            breaker.record_success()
            return result
        except Exception:
            breaker.record_failure()
            raise
    """

    def __init__(self, threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            threshold: Number of consecutive failures before opening circuit
            timeout: Seconds to wait before testing recovery (OPEN → HALF_OPEN)
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def is_open(self) -> bool:
        """
        Check if circuit is open (rejecting requests).

        Returns:
            True if circuit is open, False otherwise
        """
        if self.state == CircuitState.OPEN:
            # Check if enough time has passed to test recovery
            if self.last_failure_time:
                elapsed = datetime.now() - self.last_failure_time
                if elapsed > timedelta(seconds=self.timeout):
                    # Transition to HALF_OPEN to test recovery
                    self.state = CircuitState.HALF_OPEN
                    return False

            return True

        return False

    def record_success(self) -> None:
        """
        Record successful request.

        Resets failure count and closes circuit if it was open.
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """
        Record failed request.

        Increments failure count and opens circuit if threshold is reached.
        """
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.threshold:
            self.state = CircuitState.OPEN
            print(
                f"Circuit breaker OPENED after {self.failure_count} consecutive failures"
            )

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""

    pass
