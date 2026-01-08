"""Tests for retry logic and circuit breaker."""

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from src.core.retry import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    is_retryable_http_error,
    retry_with_backoff,
    with_circuit_breaker,
)


class TestRetryableErrors:
    """Test retryable error detection."""

    def test_timeout_is_retryable(self):
        """Test that timeout exceptions are retryable."""
        error = httpx.TimeoutException("Request timeout")
        assert is_retryable_http_error(error)

    def test_network_error_is_retryable(self):
        """Test that network errors are retryable."""
        error = httpx.NetworkError("Connection failed")
        assert is_retryable_http_error(error)

    def test_5xx_error_is_retryable(self):
        """Test that 5xx HTTP errors are retryable."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        error = httpx.HTTPStatusError("Service unavailable", request=MagicMock(), response=mock_response)
        assert is_retryable_http_error(error)

    def test_429_error_is_retryable(self):
        """Test that 429 rate limit errors are retryable."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("Too many requests", request=MagicMock(), response=mock_response)
        assert is_retryable_http_error(error)

    def test_4xx_error_not_retryable(self):
        """Test that most 4xx errors are not retryable."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
        assert not is_retryable_http_error(error)


class TestRetryWithBackoff:
    """Test retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_first_attempt(self):
        """Test that successful call doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        async def successful_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_call()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test that retry works after transient failures."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, min_wait=0, max_wait=1)
        async def flaky_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout")
            return "success"

        result = await flaky_call()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self):
        """Test that retry gives up after max attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, min_wait=0, max_wait=1)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_fails_immediately(self):
        """Test that non-retryable errors don't trigger retry."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        async def non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a retryable error")

        with pytest.raises(ValueError):
            await non_retryable_error()

        # Should only be called once (no retries)
        assert call_count == 1


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker()
        assert not cb.is_open("test_service")
        stats = cb.get_stats("test_service")
        assert stats["state"] == "CLOSED"

    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure("test_service")

        assert cb.is_open("test_service")
        stats = cb.get_stats("test_service")
        assert stats["state"] == "OPEN"

    def test_circuit_stays_closed_on_success(self):
        """Test that successes reset failure count."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure("test_service")
        cb.record_failure("test_service")
        cb.record_success("test_service")
        cb.record_failure("test_service")

        assert not cb.is_open("test_service")

    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions from OPEN to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Open the circuit
        cb.record_failure("test_service")
        cb.record_failure("test_service")
        assert cb.is_open("test_service")

        # Wait for recovery timeout
        asyncio.run(asyncio.sleep(1.1))

        # Should transition to HALF_OPEN
        assert not cb.is_open("test_service")
        stats = cb.get_stats("test_service")
        assert stats["state"] == "HALF_OPEN"

    def test_circuit_closes_after_half_open_successes(self):
        """Test circuit closes after success threshold in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, success_threshold=2)

        # Open the circuit
        cb.record_failure("test_service")
        cb.record_failure("test_service")

        # Wait for recovery
        asyncio.run(asyncio.sleep(1.1))

        # Record successes in HALF_OPEN state
        cb.record_success("test_service")
        stats = cb.get_stats("test_service")
        assert stats["state"] == "HALF_OPEN"

        cb.record_success("test_service")
        stats = cb.get_stats("test_service")
        assert stats["state"] == "CLOSED"

    def test_circuit_reopens_on_half_open_failure(self):
        """Test circuit reopens if failure occurs in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Open the circuit
        cb.record_failure("test_service")
        cb.record_failure("test_service")

        # Wait for recovery
        asyncio.run(asyncio.sleep(1.1))

        # Failure in HALF_OPEN should reopen
        cb.record_failure("test_service")
        assert cb.is_open("test_service")

    def test_reset_clears_state(self):
        """Test that reset clears circuit state."""
        cb = CircuitBreaker(failure_threshold=2)

        cb.record_failure("test_service")
        cb.record_failure("test_service")
        assert cb.is_open("test_service")

        cb.reset("test_service")
        assert not cb.is_open("test_service")
        stats = cb.get_stats("test_service")
        assert stats["state"] == "CLOSED"
        assert stats["failure_count"] == 0


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_successful_calls(self):
        """Test that circuit breaker allows successful calls."""
        cb = CircuitBreaker()

        @with_circuit_breaker("test_service", cb)
        async def successful_call():
            return "success"

        result = await successful_call()
        assert result == "success"
        assert not cb.is_open("test_service")

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        """Test that circuit breaker blocks calls when open."""
        cb = CircuitBreaker(failure_threshold=2)

        @with_circuit_breaker("test_service", cb)
        async def failing_call():
            raise httpx.TimeoutException("Timeout")

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(httpx.TimeoutException):
                await failing_call()

        # Circuit should now be open
        assert cb.is_open("test_service")

        # Next call should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            await failing_call()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failures(self):
        """Test that circuit breaker records retryable failures."""
        cb = CircuitBreaker(failure_threshold=3)

        @with_circuit_breaker("test_service", cb)
        async def failing_call():
            raise httpx.TimeoutException("Timeout")

        # First failure
        with pytest.raises(httpx.TimeoutException):
            await failing_call()

        stats = cb.get_stats("test_service")
        assert stats["failure_count"] == 1
        assert not cb.is_open("test_service")

    @pytest.mark.asyncio
    async def test_circuit_breaker_does_not_record_non_retryable(self):
        """Test that non-retryable errors don't affect circuit state."""
        cb = CircuitBreaker(failure_threshold=2)

        @with_circuit_breaker("test_service", cb)
        async def app_error():
            raise ValueError("Application error")

        # Non-retryable error should not affect circuit
        with pytest.raises(ValueError):
            await app_error()

        stats = cb.get_stats("test_service")
        assert stats["failure_count"] == 0
        assert not cb.is_open("test_service")


class TestIntegration:
    """Integration tests for retry + circuit breaker."""

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self):
        """Test retry and circuit breaker work together."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        call_count = 0

        @retry_with_backoff(max_attempts=2, min_wait=0, max_wait=1)
        @with_circuit_breaker("test_service", cb)
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise httpx.TimeoutException("Timeout")
            return "success"

        # First call: fails 2 times (retry), records 2 failures
        with pytest.raises(httpx.TimeoutException):
            await flaky_service()

        assert call_count == 2
        assert not cb.is_open("test_service")

        # Second call: fails 2 times (retry), records 2 more failures (total 4)
        # This should open the circuit after the first failure (total 3)
        call_count = 0

        @retry_with_backoff(max_attempts=2, min_wait=0, max_wait=1)
        @with_circuit_breaker("test_service", cb)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await always_fails()

        # Circuit should now be open
        assert cb.is_open("test_service")

        # Next call should be blocked immediately
        with pytest.raises(CircuitBreakerOpenError):
            await always_fails()
