"""Request logging middleware with request ID tracking."""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logging import (
    clear_request_id,
    get_logger,
    log_error,
    set_request_id,
)

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with request ID tracking."""

    def __init__(
        self,
        app: ASGIApp,
        log_body: bool = False,
    ) -> None:
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application
            log_body: Whether to log request/response bodies (default: False for security)
        """
        super().__init__(app)
        self.log_body = log_body

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and log details with request ID."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # Extract client info
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""

        # Start timing
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"Request started: {method} {path}",
            extra={
                "event_type": "request_started",
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_ip": client_host,
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {method} {path} - {response.status_code}",
                extra={
                    "event_type": "request_completed",
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": client_host,
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            log_error(
                logger,
                f"Request failed: {method} {path}",
                error=e,
                extra={
                    "event_type": "request_failed",
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": client_host,
                },
            )

            # Re-raise to let FastAPI handle it
            raise

        finally:
            # Clear request ID from context
            clear_request_id()


def get_request_id_from_request(request: Request) -> str | None:
    """
    Get request ID from request headers.

    Args:
        request: FastAPI request object

    Returns:
        Request ID if present, None otherwise
    """
    return request.headers.get("X-Request-ID")
