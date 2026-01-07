"""Health check endpoints with comprehensive system checks."""

import asyncio
import logging
import time
from typing import Any

import psutil
import redis.asyncio as redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.core.config import settings
from src.db.session import engine

logger = logging.getLogger(__name__)

router = APIRouter()


async def check_database() -> dict[str, Any]:
    """Check database connectivity and response time.

    Returns:
        dict with status, latency_ms, and optional error
    """
    start = time.time()
    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(
                conn.execute(text("SELECT 1")),
                timeout=5.0,  # 5 second timeout
            )
        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
    except asyncio.TimeoutError:
        return {
            "status": "unhealthy",
            "error": "Database connection timeout (>5s)",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Database connection failed",
        }


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity and response time.

    Returns:
        dict with status, latency_ms, and optional error
    """
    start = time.time()
    redis_client = None
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await asyncio.wait_for(
            redis_client.ping(),
            timeout=5.0,  # 5 second timeout
        )
        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
    except asyncio.TimeoutError:
        return {
            "status": "degraded",
            "error": "Redis connection timeout (>5s)",
            "note": "Using in-memory fallback for rate limiting",
        }
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {
            "status": "degraded",
            "error": "Redis unavailable",
            "note": "Using in-memory fallback for rate limiting",
        }
    finally:
        if redis_client:
            await redis_client.aclose()


def check_memory() -> dict[str, Any]:
    """Check system memory usage.

    Returns:
        dict with status, usage details
    """
    try:
        memory = psutil.virtual_memory()
        percent_used = memory.percent

        # Consider unhealthy if >90% memory used
        if percent_used > 90:
            status_val = "unhealthy"
        elif percent_used > 80:
            status_val = "degraded"
        else:
            status_val = "healthy"

        return {
            "status": status_val,
            "percent_used": percent_used,
            "available_mb": round(memory.available / (1024 * 1024), 2),
            "total_mb": round(memory.total / (1024 * 1024), 2),
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        return {
            "status": "unknown",
            "error": "Failed to check memory",
        }


def check_disk() -> dict[str, Any]:
    """Check disk space usage.

    Returns:
        dict with status, usage details
    """
    try:
        disk = psutil.disk_usage("/")
        percent_used = disk.percent

        # Consider unhealthy if >90% disk used
        if percent_used > 90:
            status_val = "unhealthy"
        elif percent_used > 80:
            status_val = "degraded"
        else:
            status_val = "healthy"

        return {
            "status": status_val,
            "percent_used": percent_used,
            "available_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
        }
    except Exception as e:
        logger.error(f"Disk health check failed: {e}")
        return {
            "status": "unknown",
            "error": "Failed to check disk space",
        }


@router.get("/health")
async def health_check() -> JSONResponse:
    """Comprehensive health check with database, Redis, memory, and disk checks.

    Returns 200 if all critical services are healthy, 503 otherwise.
    Redis is considered optional (degraded state is acceptable).
    """
    start_time = time.time()

    # Run all checks concurrently for speed
    db_result, redis_result, memory_result, disk_result = await asyncio.gather(
        check_database(),
        check_redis(),
        asyncio.to_thread(check_memory),
        asyncio.to_thread(check_disk),
    )

    # Determine overall status
    # Redis is optional, so degraded Redis doesn't fail health check
    critical_checks = [db_result, memory_result, disk_result]

    if any(check["status"] == "unhealthy" for check in critical_checks):
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any(check["status"] == "degraded" for check in critical_checks):
        overall_status = "degraded"
        http_status = status.HTTP_200_OK  # Still operational
    else:
        overall_status = "healthy"
        http_status = status.HTTP_200_OK

    response_time_ms = round((time.time() - start_time) * 1000, 2)

    response_data = {
        "status": overall_status,
        "timestamp": time.time(),
        "response_time_ms": response_time_ms,
        "checks": {
            "database": db_result,
            "redis": redis_result,
            "memory": memory_result,
            "disk": disk_result,
        },
    }

    return JSONResponse(
        status_code=http_status,
        content=response_data,
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """Kubernetes-style readiness check.

    Returns 200 if service is ready to accept traffic (database is connected),
    503 otherwise. This is lighter than /health and focuses on critical dependencies.
    """
    try:
        # Quick database check with shorter timeout
        async with engine.connect() as conn:
            await asyncio.wait_for(
                conn.execute(text("SELECT 1")),
                timeout=3.0,
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "timestamp": time.time(),
            },
        )
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "Database connection timeout",
                "timestamp": time.time(),
            },
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "Database unavailable",
                "timestamp": time.time(),
            },
        )
