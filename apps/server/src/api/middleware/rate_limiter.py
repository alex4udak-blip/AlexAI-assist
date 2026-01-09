"""Rate limiting middleware using sliding window algorithm with Redis."""

import logging
import time
from collections.abc import Callable

import redis.asyncio as redis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limit configuration for different endpoint types."""

    # Requests per window (in seconds)
    AUTH_LIMIT = 5  # 5 requests per 60 seconds for auth endpoints
    AUTH_WINDOW = 60

    API_LIMIT = 100  # 100 requests per 60 seconds for API endpoints
    API_WINDOW = 60

    WEBSOCKET_LIMIT = 10  # 10 requests per 60 seconds for websocket connections
    WEBSOCKET_WINDOW = 60

    DEFAULT_LIMIT = 60  # 60 requests per 60 seconds for other endpoints
    DEFAULT_WINDOW = 60


class RateLimiter:
    """Rate limiter using sliding window algorithm with Redis."""

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        """Initialize rate limiter.

        Args:
            redis_client: Redis client for distributed rate limiting.
                         If None, uses in-memory fallback.
        """
        self.redis_client = redis_client
        # In-memory fallback (not distributed, per-instance only)
        self._memory_store: dict[str, list[float]] = {}

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, dict[str, int]]:
        """Check if request is allowed using sliding window algorithm.

        Args:
            key: Unique identifier (e.g., IP address or session ID)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            rate_limit_info contains: limit, remaining, reset
        """
        current_time = time.time()
        window_start = current_time - window

        if self.redis_client:
            try:
                return await self._check_redis(key, limit, window, current_time, window_start)
            except Exception as e:
                logger.warning(f"Redis rate limiter error, falling back to memory: {e}")
                return await self._check_memory(key, limit, window, current_time, window_start)
        else:
            return await self._check_memory(key, limit, window, current_time, window_start)

    async def _check_redis(
        self,
        key: str,
        limit: int,
        window: int,
        current_time: float,
        window_start: float,
    ) -> tuple[bool, dict[str, int]]:
        """Redis-based sliding window check."""
        redis_key = f"rate_limit:{key}"

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()  # type: ignore

        # Remove old entries outside the window
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count requests in current window
        pipe.zcard(redis_key)

        # Add current request timestamp
        pipe.zadd(redis_key, {str(current_time): current_time})

        # Set expiration to window + buffer
        pipe.expire(redis_key, window + 10)

        results = await pipe.execute()
        count = results[1]  # Result from zcard

        remaining = max(0, limit - count - 1)
        reset = int(current_time + window)

        rate_limit_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
        }

        is_allowed = count < limit
        return is_allowed, rate_limit_info

    async def _check_memory(
        self,
        key: str,
        limit: int,
        window: int,
        current_time: float,
        window_start: float,
    ) -> tuple[bool, dict[str, int]]:
        """In-memory fallback sliding window check."""
        # Initialize key if not exists
        if key not in self._memory_store:
            self._memory_store[key] = []

        # Remove old timestamps outside window
        self._memory_store[key] = [
            ts for ts in self._memory_store[key]
            if ts > window_start
        ]

        count = len(self._memory_store[key])
        remaining = max(0, limit - count - 1)
        reset = int(current_time + window)

        rate_limit_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
        }

        is_allowed = count < limit

        if is_allowed:
            self._memory_store[key].append(current_time)

        return is_allowed, rate_limit_info


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, rate_limiter: RateLimiter) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier (IP or session).

        Args:
            request: FastAPI request

        Returns:
            Unique client identifier
        """
        # Try to get real IP from headers (for proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rate_limit_params(self, path: str) -> tuple[int, int]:
        """Get rate limit parameters based on endpoint type.

        Args:
            path: Request path

        Returns:
            Tuple of (limit, window)
        """
        # Auth endpoints (login, register, password reset, etc.)
        if "/auth" in path or "/login" in path or "/register" in path:
            return RateLimitConfig.AUTH_LIMIT, RateLimitConfig.AUTH_WINDOW

        # WebSocket endpoints
        if path.startswith("/ws"):
            return RateLimitConfig.WEBSOCKET_LIMIT, RateLimitConfig.WEBSOCKET_WINDOW

        # API endpoints
        if path.startswith("/api/"):
            return RateLimitConfig.API_LIMIT, RateLimitConfig.API_WINDOW

        # Default for other endpoints
        return RateLimitConfig.DEFAULT_LIMIT, RateLimitConfig.DEFAULT_WINDOW

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting.

        Args:
            path: Request path

        Returns:
            True if exempt
        """
        exempt_paths = [
            "/",
            "/health",
            "/ready",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        return path in exempt_paths

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        path = request.url.path

        # Skip rate limiting for exempt paths
        if self._is_exempt(path):
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Get rate limit params for this endpoint type
        limit, window = self._get_rate_limit_params(path)

        # Build rate limit key
        rate_limit_key = f"{client_id}:{path}"

        # Check rate limit
        is_allowed, rate_info = await self.rate_limiter.is_allowed(
            rate_limit_key,
            limit,
            window,
        )

        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_info["limit"]),
            "X-RateLimit-Remaining": str(rate_info["remaining"]),
            "X-RateLimit-Reset": str(rate_info["reset"]),
        }

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {path}. "
                f"Limit: {limit}/{window}s"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": rate_info["reset"] - int(time.time()),
                },
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response
