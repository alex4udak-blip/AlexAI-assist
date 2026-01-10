"""API Key Authentication Middleware.

Simple API key based authentication for single-user mode.
All API requests must include a valid API key in the X-API-Key header.
"""

from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.logging import get_logger, log_security_event

logger = get_logger(__name__)

# Paths that don't require authentication
EXEMPT_PATHS = {
    "/",
    "/ping",
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Path prefixes that don't require authentication
EXEMPT_PREFIXES = (
    "/health",
)


def is_path_exempt(path: str) -> bool:
    """Check if a path is exempt from authentication."""
    if path in EXEMPT_PATHS:
        return True
    for prefix in EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def validate_api_key(api_key: str | None) -> bool:
    """Validate the provided API key against the configured key."""
    if not settings.api_key:
        # No API key configured - auth disabled (development mode)
        return True

    if not api_key:
        return False

    # Constant-time comparison to prevent timing attacks
    import hmac
    return hmac.compare_digest(api_key, settings.api_key)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key on all requests."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for exempt paths
        if is_path_exempt(request.url.path):
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        # Validate API key
        if not validate_api_key(api_key):
            log_security_event(
                logger,
                "API authentication failed",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                    "has_api_key": api_key is not None,
                },
                level="WARNING",
            )
            # Include CORS headers in error response
            origin = request.headers.get("origin", "")
            cors_headers = {
                "WWW-Authenticate": "ApiKey",
                "Access-Control-Allow-Origin": origin if origin else "*",
                "Access-Control-Allow-Credentials": "true",
            }
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
                headers=cors_headers,
            )

        return await call_next(request)


def require_api_key(api_key: str | None = None) -> None:
    """Dependency to require API key authentication.

    Use this as a FastAPI dependency for routes that need explicit auth check.

    Usage:
        @router.get("/protected")
        async def protected_route(
            _auth: None = Depends(require_api_key_header),
        ):
            ...
    """
    if not validate_api_key(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def validate_websocket_auth(websocket: Any) -> bool:
    """Validate WebSocket connection authentication.

    Checks for API key in:
    1. Query parameter: ?api_key=xxx
    2. Subprotocol: Sec-WebSocket-Protocol header

    Returns True if authenticated, False otherwise.
    """
    if not settings.api_key:
        # No API key configured - auth disabled
        return True

    # Check query parameter
    api_key = websocket.query_params.get("api_key")
    if api_key and validate_api_key(api_key):
        return True

    # Check headers (for clients that support it)
    api_key = websocket.headers.get("X-API-Key")
    if api_key and validate_api_key(api_key):
        return True

    return False
