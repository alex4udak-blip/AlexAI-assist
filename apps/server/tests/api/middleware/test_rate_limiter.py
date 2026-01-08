"""Tests for rate limiting middleware."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.middleware.rate_limiter import (
    RateLimitConfig,
    RateLimiter,
    RateLimiterMiddleware,
)


@pytest.fixture
def rate_limiter() -> RateLimiter:
    """Create rate limiter with in-memory backend."""
    return RateLimiter(redis_client=None)


@pytest.fixture
def app_with_rate_limiter(rate_limiter: RateLimiter) -> FastAPI:
    """Create FastAPI app with rate limiter."""
    app = FastAPI()
    app.add_middleware(RateLimiterMiddleware, rate_limiter=rate_limiter)

    @app.get("/api/v1/test")
    async def test_endpoint() -> dict[str, str]:
        return {"message": "success"}

    @app.get("/auth/login")
    async def auth_endpoint() -> dict[str, str]:
        return {"message": "authenticated"}

    @app.get("/health")
    async def health_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return app


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.mark.asyncio
    async def test_in_memory_allows_within_limit(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test that requests within limit are allowed."""
        key = "test_client"
        limit = 5
        window = 60

        # Make requests within limit
        for i in range(limit):
            is_allowed, info = await rate_limiter.is_allowed(key, limit, window)
            assert is_allowed is True
            assert info["limit"] == limit
            assert info["remaining"] == limit - i - 1

    @pytest.mark.asyncio
    async def test_in_memory_blocks_over_limit(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test that requests over limit are blocked."""
        key = "test_client"
        limit = 3
        window = 60

        # Use up the limit
        for _ in range(limit):
            is_allowed, _ = await rate_limiter.is_allowed(key, limit, window)
            assert is_allowed is True

        # Next request should be blocked
        is_allowed, info = await rate_limiter.is_allowed(key, limit, window)
        assert is_allowed is False
        assert info["remaining"] == 0

    @pytest.mark.asyncio
    async def test_in_memory_sliding_window(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test sliding window algorithm."""
        key = "test_client"
        limit = 2
        window = 1  # 1 second window

        # Make 2 requests (use up limit)
        for _ in range(limit):
            is_allowed, _ = await rate_limiter.is_allowed(key, limit, window)
            assert is_allowed is True

        # Should be blocked
        is_allowed, _ = await rate_limiter.is_allowed(key, limit, window)
        assert is_allowed is False

        # Wait for window to pass
        await asyncio.sleep(1.1)

        # Should be allowed again
        is_allowed, _ = await rate_limiter.is_allowed(key, limit, window)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_different_keys_independent(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test that different keys have independent limits."""
        limit = 2
        window = 60

        # Use up limit for key1
        for _ in range(limit):
            is_allowed, _ = await rate_limiter.is_allowed("key1", limit, window)
            assert is_allowed is True

        # key1 should be blocked
        is_allowed, _ = await rate_limiter.is_allowed("key1", limit, window)
        assert is_allowed is False

        # key2 should still be allowed
        is_allowed, _ = await rate_limiter.is_allowed("key2", limit, window)
        assert is_allowed is True


class TestRateLimiterMiddleware:
    """Test RateLimiterMiddleware class."""

    def test_api_endpoint_rate_limiting(
        self,
        app_with_rate_limiter: FastAPI,
    ) -> None:
        """Test rate limiting on API endpoints."""
        client = TestClient(app_with_rate_limiter)

        # Make requests up to the limit
        for i in range(RateLimitConfig.API_LIMIT):
            response = client.get("/api/v1/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert response.headers["X-RateLimit-Limit"] == str(RateLimitConfig.API_LIMIT)

        # Next request should be rate limited
        response = client.get("/api/v1/test")
        assert response.status_code == 429
        assert response.json()["detail"] == "Too many requests. Please try again later."
        assert "retry_after" in response.json()

    def test_auth_endpoint_stricter_limit(
        self,
        app_with_rate_limiter: FastAPI,
    ) -> None:
        """Test that auth endpoints have stricter limits."""
        client = TestClient(app_with_rate_limiter)

        # Auth limit should be lower than API limit
        assert RateLimitConfig.AUTH_LIMIT < RateLimitConfig.API_LIMIT

        # Make requests up to auth limit
        for _ in range(RateLimitConfig.AUTH_LIMIT):
            response = client.get("/auth/login")
            assert response.status_code == 200

        # Next request should be rate limited
        response = client.get("/auth/login")
        assert response.status_code == 429

    def test_exempt_paths_not_rate_limited(
        self,
        app_with_rate_limiter: FastAPI,
    ) -> None:
        """Test that exempt paths are not rate limited."""
        client = TestClient(app_with_rate_limiter)

        # Make many requests to health endpoint
        for _ in range(200):  # Far more than any limit
            response = client.get("/health")
            assert response.status_code == 200
            # Should not have rate limit headers
            assert "X-RateLimit-Limit" not in response.headers

    def test_rate_limit_headers_present(
        self,
        app_with_rate_limiter: FastAPI,
    ) -> None:
        """Test that rate limit headers are present."""
        client = TestClient(app_with_rate_limiter)

        response = client.get("/api/v1/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Check header values are reasonable
        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        reset = int(response.headers["X-RateLimit-Reset"])

        assert limit > 0
        assert remaining >= 0
        assert remaining < limit
        assert reset > time.time()

    def test_client_identifier_extraction(self) -> None:
        """Test client identifier extraction from headers."""
        app = FastAPI()
        rate_limiter = RateLimiter(redis_client=None)
        middleware = RateLimiterMiddleware(app, rate_limiter)

        # Test X-Forwarded-For
        request = MagicMock(spec=Request)
        request.headers.get = MagicMock(side_effect=lambda h: "1.2.3.4" if h == "X-Forwarded-For" else None)
        assert middleware._get_client_identifier(request) == "1.2.3.4"

        # Test X-Real-IP
        request = MagicMock(spec=Request)
        request.headers.get = MagicMock(side_effect=lambda h: "5.6.7.8" if h == "X-Real-IP" else None)
        assert middleware._get_client_identifier(request) == "5.6.7.8"

        # Test fallback to client.host
        request = MagicMock(spec=Request)
        request.headers.get = MagicMock(return_value=None)
        request.client = MagicMock()
        request.client.host = "9.10.11.12"
        assert middleware._get_client_identifier(request) == "9.10.11.12"

    def test_different_endpoints_different_limits(
        self,
        app_with_rate_limiter: FastAPI,
    ) -> None:
        """Test that different endpoint types have different limits."""
        app = FastAPI()
        rate_limiter = RateLimiter(redis_client=None)
        middleware = RateLimiterMiddleware(app, rate_limiter)

        # Test API endpoint
        api_limit, api_window = middleware._get_rate_limit_params("/api/v1/test")
        assert api_limit == RateLimitConfig.API_LIMIT
        assert api_window == RateLimitConfig.API_WINDOW

        # Test auth endpoint
        auth_limit, auth_window = middleware._get_rate_limit_params("/auth/login")
        assert auth_limit == RateLimitConfig.AUTH_LIMIT
        assert auth_window == RateLimitConfig.AUTH_WINDOW

        # Test websocket endpoint
        ws_limit, ws_window = middleware._get_rate_limit_params("/ws")
        assert ws_limit == RateLimitConfig.WEBSOCKET_LIMIT
        assert ws_window == RateLimitConfig.WEBSOCKET_WINDOW

        # Test default
        default_limit, default_window = middleware._get_rate_limit_params("/other")
        assert default_limit == RateLimitConfig.DEFAULT_LIMIT
        assert default_window == RateLimitConfig.DEFAULT_WINDOW


@pytest.mark.asyncio
async def test_redis_fallback_on_error() -> None:
    """Test that Redis errors fall back to in-memory."""
    # Create mock Redis client that raises errors
    mock_redis = AsyncMock()
    mock_redis.pipeline.side_effect = Exception("Redis error")

    rate_limiter = RateLimiter(redis_client=mock_redis)

    # Should fall back to in-memory and work
    is_allowed, info = await rate_limiter.is_allowed("test", 10, 60)
    assert is_allowed is True
    assert info["limit"] == 10
