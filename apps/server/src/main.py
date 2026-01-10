"""Observer API Server - Main Entry Point"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import AuthMiddleware, RateLimiterMiddleware, RequestLoggingMiddleware, validate_websocket_auth
from src.api.middleware.rate_limiter import RateLimiter
from src.api.routes import (
    agents,
    analytics,
    automation,
    chat,
    events,
    health,
    memory,
    patterns,
    sessions,
    suggestions,
)
from src.api.routes import (
    settings as settings_router,
)
from src.core.config import settings
from src.core.logging import get_logger, log_error, setup_logging
from src.core.websocket import active_connections
from src.db.session import engine

# Configure structured logging
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    json_logs=settings.environment == "production",
)
logger = get_logger(__name__)

# Create rate limiter at module level (starts with in-memory, upgrades to Redis in lifespan)
_rate_limiter = RateLimiter(None)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info(
        "Starting Observer API Server",
        extra={
            "event_type": "startup",
            "environment": settings.environment,
            "debug": settings.debug,
        },
    )
    logger.info(f"CORS origins: {settings.allowed_origins}")

    # Run database migrations automatically (in thread to avoid asyncio.run conflict)
    try:
        import asyncio
        import pathlib

        from alembic.config import Config

        from alembic import command  # type: ignore[attr-defined]

        logger.info("Starting database migrations...")

        def run_migrations() -> None:
            base_dir = pathlib.Path(__file__).parent.parent
            alembic_cfg = Config(str(base_dir / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(base_dir / "alembic"))
            command.upgrade(alembic_cfg, "head")

        # Add 60 second timeout for migrations
        await asyncio.wait_for(asyncio.to_thread(run_migrations), timeout=60.0)
        logger.info("Database migrations completed successfully")
    except asyncio.TimeoutError:
        logger.error("Database migrations timed out after 60 seconds - continuing without migrations")
    except Exception as e:
        logger.warning(f"Could not run migrations (may already be up to date): {e}")

    # Try to upgrade rate limiter to Redis (optional, with timeout)
    try:
        import asyncio

        import redis.asyncio as redis
        logger.info("Attempting Redis connection...")
        redis_client = redis.from_url(  # type: ignore[no-untyped-call]
            settings.redis_url,
            encoding="utf-8",
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Timeout ping to avoid hanging forever
        await asyncio.wait_for(redis_client.ping(), timeout=5.0)
        _rate_limiter.redis_client = redis_client
        logger.info("Rate limiter upgraded to Redis backend")
    except TimeoutError:
        logger.warning("Redis connection timed out, using in-memory rate limiting")
    except Exception as e:
        logger.warning(f"Redis not available, using in-memory rate limiting: {e}")

    # Start background scheduler
    from src.core.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    logger.info("=== SERVER STARTUP COMPLETE - READY TO ACCEPT REQUESTS ===")
    yield

    # Shutdown
    logger.info(
        "Shutting down Observer API Server",
        extra={"event_type": "shutdown"},
    )
    stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="Observer API",
    description="Personal AI Meta-Agent System",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware are processed in REVERSE order of addition
# Last added = first to process requests

# API Key authentication middleware (processes 3rd)
app.add_middleware(AuthMiddleware)

# Request logging middleware (processes 4th)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiter middleware (processes 5th)
app.add_middleware(RateLimiterMiddleware, rate_limiter=_rate_limiter)

# CORS middleware - MUST be last to add so it processes FIRST
# This ensures CORS headers are added to ALL responses including errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(patterns.router, prefix="/api/v1/patterns", tags=["Patterns"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(suggestions.router, prefix="/api/v1/suggestions", tags=["Suggestions"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(automation.router, prefix="/api/v1/automation", tags=["Automation"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP exception handler with CORS headers."""
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=cors_headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with full error logging."""
    log_error(
        logger,
        "Unhandled exception",
        error=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown",
        },
    )
    # Include CORS headers in error response
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=cors_headers,
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for basic connectivity check."""
    return {"status": "ok", "service": "observer-api"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    # Validate authentication before accepting
    if not await validate_websocket_auth(websocket):
        await websocket.close(code=4001, reason="Unauthorized")
        logger.warning(
            "WebSocket connection rejected: unauthorized",
            extra={"event_type": "websocket_auth_failed"},
        )
        return

    await websocket.accept()
    active_connections.add(websocket)
    logger.info(
        "WebSocket connected",
        extra={
            "event_type": "websocket_connected",
            "total_connections": len(active_connections),
        },
    )

    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()
            logger.debug(
                "WebSocket message received",
                extra={"event_type": "websocket_message", "data_length": len(data)},
            )
            # Echo back for now
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info(
            "WebSocket disconnected",
            extra={
                "event_type": "websocket_disconnected",
                "total_connections": len(active_connections),
            },
        )
    except Exception as e:
        log_error(
            logger,
            "WebSocket error",
            error=e,
            extra={"event_type": "websocket_error"},
        )
        active_connections.discard(websocket)
