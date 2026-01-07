"""Observer API Server - Main Entry Point"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    agents,
    analytics,
    chat,
    events,
    health,
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
    yield
    # Shutdown
    logger.info("Shutting down Observer API Server...")
    await engine.dispose()


app = FastAPI(
    title="Observer API",
    description="Personal AI Meta-Agent System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(patterns.router, prefix="/api/v1/patterns", tags=["Patterns"])
app.include_router(suggestions.router, prefix="/api/v1/suggestions", tags=["Suggestions"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for basic connectivity check."""
    return {"status": "ok", "service": "observer-api"}
