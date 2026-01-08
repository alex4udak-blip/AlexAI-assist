"""Observer API Server - Main Entry Point"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import RateLimiterMiddleware, RequestLoggingMiddleware
from src.api.middleware.rate_limiter import RateLimiter
from src.api.routes import (
    agents,
    analytics,
    chat,
    events,
    health,
    memory,
    patterns,
    suggestions,
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

    # Try to upgrade rate limiter to Redis (optional)
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
        await redis_client.ping()
        _rate_limiter.redis_client = redis_client
        logger.info("Rate limiter upgraded to Redis backend")
    except Exception as e:
        logger.warning(f"Redis not available, using in-memory rate limiting: {e}")

    # Start background scheduler
    from src.core.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

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

# CORS middleware - handles all CORS including preflight OPTIONS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Rate limiter middleware (uses in-memory, upgrades to Redis in lifespan)
app.add_middleware(RateLimiterMiddleware, rate_limiter=_rate_limiter)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(patterns.router, prefix="/api/v1/patterns", tags=["Patterns"])
app.include_router(suggestions.router, prefix="/api/v1/suggestions", tags=["Suggestions"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])


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
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for basic connectivity check."""
    return {"status": "ok", "service": "observer-api"}


@app.get("/test-db")
async def test_db() -> dict[str, str]:
    """Test database connection (internal use only)."""
    from sqlalchemy import text

    from src.db.session import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return {"status": "ok", "db": "connected"}
    except Exception as e:
        # Log full error but don't expose details to client
        log_error(
            logger,
            "Database connection test failed",
            error=e,
            extra={"event_type": "db_error"},
        )
        return {"status": "error", "detail": "Database connection failed"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
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
