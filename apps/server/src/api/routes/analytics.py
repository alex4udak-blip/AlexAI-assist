"""Analytics endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.services.analyzer import AnalyzerService

router = APIRouter()


@router.get("/summary")
async def get_summary(
    device_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get activity summary statistics."""
    service = AnalyzerService(db)
    return await service.get_summary(
        device_id=device_id,
        start_date=start,
        end_date=end,
    )


@router.get("/categories")
async def get_categories(
    device_id: str | None = None,
    days: int = Query(7, le=90),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get time spent by category."""
    service = AnalyzerService(db)
    return await service.get_category_breakdown(
        device_id=device_id,
        days=days,
    )


@router.get("/apps")
async def get_app_usage(
    device_id: str | None = None,
    days: int = Query(7, le=90),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get app usage statistics."""
    service = AnalyzerService(db)
    return await service.get_app_usage(
        device_id=device_id,
        days=days,
        limit=limit,
    )


@router.get("/productivity")
async def get_productivity(
    device_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get productivity score."""
    service = AnalyzerService(db)
    return await service.get_productivity_score(device_id=device_id)


@router.get("/trends")
async def get_trends(
    device_id: str | None = None,
    days: int = Query(30, le=90),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get activity trends over time."""
    service = AnalyzerService(db)
    return await service.get_trends(
        device_id=device_id,
        days=days,
    )
