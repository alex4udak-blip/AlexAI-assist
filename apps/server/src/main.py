"""Observer API Server - Main Entry Point"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from src.db.session import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Observer API Server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")
    logger.info(f"CORS origins: {settings.allowed_origins}")

    # Start background scheduler
    from src.core.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    # Shutdown
    logger.info("Shutting down Observer API Server...")
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
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for basic connectivity check."""
    logger.info("Root endpoint called")
    return {"status": "ok", "service": "observer-api"}


@app.get("/test-db")
async def test_db() -> dict[str, str]:
    """Test database connection (internal use only)."""
    from sqlalchemy import text

    from src.db.session import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return {"status": "ok", "db": "connected"}
    except Exception as e:
        # Log full error but don't expose details to client
        logger.error(f"DB connection error: {e}")
        return {"status": "error", "detail": "Database connection failed"}


# Import shared WebSocket connections
from src.core.websocket import active_connections


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket connected. Total connections: {len(active_connections)}")

    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()
            logger.info(f"WebSocket received: {data}")
            # Echo back for now
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)
