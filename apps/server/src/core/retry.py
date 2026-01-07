"""Retry logic and circuit breaker for external service calls."""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, TypeVar

from httpx import ConnectError, HTTPStatusError, NetworkError, TimeoutException
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Type variable for generic decorator
T = TypeVar("T")


# Transient errors that should be retried
RETRYABLE_EXCEPTIONS = (
    TimeoutException,
    ConnectError,
    NetworkError,
    HTTPStatusError,
)


def is_retryable_http_error(exception: BaseException) -> bool:
    """Check if HTTP error is retryable (5xx or specific 4xx errors)."""
    if isinstance(exception, HTTPStatusError):
        status_code = exception.response.status_code
        # Retry on 5xx server errors
        if 500 <= status_code < 600:
            return True
        # Retry on specific 4xx errors
        if status_code in (408, 429):  # Request Timeout, Too Many Requests
            return True
        return False
    return isinstance(exception, RETRYABLE_EXCEPTIONS)


def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        Decorated function with retry logic
    """
    return retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {retry_state.fn.__name__} after {retry_state.outcome.exception()}"
            f" (attempt {retry_state.attempt_number}/{max_attempts})"
        ),
    )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    States:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Transitions:
    - CLOSED -> OPEN: After failure_threshold failures
    - OPEN -> HALF_OPEN: After recovery_timeout
    - HALF_OPEN -> CLOSED: After success_threshold successes
    - HALF_OPEN -> OPEN: On any failure
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Number of successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        # State tracking per service (key = service name)
        self._failure_counts: dict[str, int] = defaultdict(int)
        self._success_counts: dict[str, int] = defaultdict(int)
        self._last_failure_time: dict[str, datetime] = {}
        self._state: dict[str, str] = defaultdict(lambda: "CLOSED")

    def _get_state(self, service: str) -> str:
        """Get current state for a service."""
        state = self._state[service]

        # Transition from OPEN to HALF_OPEN after recovery timeout
        if state == "OPEN":
            last_failure = self._last_failure_time.get(service)
            if last_failure:
                time_since_failure = datetime.now(UTC) - last_failure
                if time_since_failure >= timedelta(seconds=self.recovery_timeout):
                    self._state[service] = "HALF_OPEN"
                    self._success_counts[service] = 0
                    logger.info(f"Circuit breaker for {service}: OPEN -> HALF_OPEN")
                    return "HALF_OPEN"

        return state

    def is_open(self, service: str) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._get_state(service) == "OPEN"

    def record_success(self, service: str) -> None:
        """Record successful request."""
        state = self._get_state(service)

        if state == "HALF_OPEN":
            self._success_counts[service] += 1
            if self._success_counts[service] >= self.success_threshold:
                self._state[service] = "CLOSED"
                self._failure_counts[service] = 0
                self._success_counts[service] = 0
                logger.info(f"Circuit breaker for {service}: HALF_OPEN -> CLOSED")
        elif state == "CLOSED":
            # Reset failure count on success
            self._failure_counts[service] = 0

    def record_failure(self, service: str) -> None:
        """Record failed request."""
        state = self._get_state(service)

        if state == "HALF_OPEN":
            # Immediately go back to OPEN on any failure
            self._state[service] = "OPEN"
            self._last_failure_time[service] = datetime.now(UTC)
            logger.warning(f"Circuit breaker for {service}: HALF_OPEN -> OPEN")
        elif state == "CLOSED":
            self._failure_counts[service] += 1
            if self._failure_counts[service] >= self.failure_threshold:
                self._state[service] = "OPEN"
                self._last_failure_time[service] = datetime.now(UTC)
                logger.error(
                    f"Circuit breaker for {service}: CLOSED -> OPEN "
                    f"(failures: {self._failure_counts[service]})"
                )

    def reset(self, service: str) -> None:
        """Reset circuit breaker for a service."""
        self._state[service] = "CLOSED"
        self._failure_counts[service] = 0
        self._success_counts[service] = 0
        if service in self._last_failure_time:
            del self._last_failure_time[service]
        logger.info(f"Circuit breaker for {service}: RESET")

    def get_stats(self, service: str) -> dict[str, Any]:
        """Get current stats for a service."""
        return {
            "state": self._get_state(service),
            "failure_count": self._failure_counts[service],
            "success_count": self._success_counts[service],
            "last_failure_time": (
                self._last_failure_time[service].isoformat()
                if service in self._last_failure_time
                else None
            ),
        }


# Global circuit breaker instance
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2,
)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


def with_circuit_breaker(
    service_name: str,
    breaker: CircuitBreaker | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add circuit breaker protection.

    Args:
        service_name: Name of the service (for tracking state)
        breaker: Circuit breaker instance (uses global if None)

    Returns:
        Decorated function with circuit breaker
    """
    cb = breaker or circuit_breaker

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Check if circuit is open
            if cb.is_open(service_name):
                error_msg = f"Circuit breaker open for {service_name}"
                logger.error(error_msg)
                raise CircuitBreakerOpenError(error_msg)

            try:
                result = await func(*args, **kwargs)
                cb.record_success(service_name)
                return result
            except Exception as e:
                # Only record failure for transient errors
                if is_retryable_http_error(e):
                    cb.record_failure(service_name)
                raise

        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # Check if circuit is open
            if cb.is_open(service_name):
                error_msg = f"Circuit breaker open for {service_name}"
                logger.error(error_msg)
                raise CircuitBreakerOpenError(error_msg)

            try:
                result = func(*args, **kwargs)
                cb.record_success(service_name)
                return result
            except Exception as e:
                # Only record failure for transient errors
                if is_retryable_http_error(e):
                    cb.record_failure(service_name)
                raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator
