"""Analytics endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.services.ai_router import get_ai_router
from src.services.analyzer import AnalyzerService

router = APIRouter()


class SummaryResponse(BaseModel):
    """Summary statistics response."""

    total_events: int = Field(
        ...,
        description="Total number of events",
    )
    top_apps: list[tuple[str, int]] = Field(
        default_factory=list,
        description="Top applications by usage",
    )
    categories: dict[str, Any] = Field(
        default_factory=dict,
        description="Category breakdown",
    )


class CategoryBreakdown(BaseModel):
    """Category breakdown response."""

    category: str = Field(
        ...,
        description="Category name",
    )
    time_minutes: float = Field(
        ...,
        description="Time spent in minutes",
    )
    percentage: float = Field(
        ...,
        description="Percentage of total time",
    )


class AppUsage(BaseModel):
    """App usage statistics."""

    app_name: str = Field(
        ...,
        description="Application name",
    )
    time_minutes: float = Field(
        ...,
        description="Time spent in minutes",
    )
    event_count: int = Field(
        ...,
        description="Number of events",
    )


class ProductivityScore(BaseModel):
    """Productivity score response."""

    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Productivity score (0-100)",
    )
    productive_minutes: float = Field(
        ...,
        description="Time spent on productive activities",
    )
    neutral_minutes: float = Field(
        ...,
        description="Time spent on neutral activities",
    )
    distracting_minutes: float = Field(
        ...,
        description="Time spent on distracting activities",
    )


class TrendData(BaseModel):
    """Trend data point."""

    date: str = Field(
        ...,
        description="Date in ISO format",
    )
    value: float = Field(
        ...,
        description="Value for the date",
    )
    category: str | None = Field(
        default=None,
        description="Category if applicable",
    )


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    start: datetime | None = Query(
        default=None,
        description="Start datetime for filtering",
    ),
    end: datetime | None = Query(
        default=None,
        description="End datetime for filtering",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get activity summary statistics."""
    service = AnalyzerService(db)
    return await service.get_summary(
        device_id=device_id,
        start_date=start,
        end_date=end,
    )


@router.get("/categories", response_model=list[CategoryBreakdown])
async def get_categories(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of days to analyze",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get time spent by category."""
    service = AnalyzerService(db)
    return await service.get_category_breakdown(
        device_id=device_id,
        days=days,
    )


@router.get("/apps", response_model=list[AppUsage])
async def get_app_usage(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of days to analyze",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of apps to return",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get app usage statistics."""
    service = AnalyzerService(db)
    return await service.get_app_usage(
        device_id=device_id,
        days=days,
        limit=limit,
    )


@router.get("/productivity", response_model=ProductivityScore)
async def get_productivity(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of days to analyze",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get productivity score."""
    service = AnalyzerService(db)
    return await service.get_productivity_score(device_id=device_id, days=days)


@router.get("/trends", response_model=list[TrendData])
async def get_trends(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of days to analyze",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get activity trends over time."""
    service = AnalyzerService(db)
    return await service.get_trends(
        device_id=device_id,
        days=days,
    )


class AIUsageStats(BaseModel):
    """AI usage statistics response."""

    daily_usage: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Daily usage breakdown",
    )
    total_cost: float = Field(
        ...,
        description="Total cost across all days",
    )
    total_requests: int = Field(
        ...,
        description="Total number of requests",
    )
    model_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        description="Usage by model",
    )
    budget_status: dict[str, Any] = Field(
        default_factory=dict,
        description="Budget usage status",
    )


@router.get("/ai-usage", response_model=AIUsageStats)
async def get_ai_usage(
    days: int = Query(
        default=7,
        ge=1,
        le=30,
        description="Number of days to retrieve",
    ),
) -> dict[str, Any]:
    """Get AI usage statistics and budget status."""
    ai_router = get_ai_router()
    return ai_router.get_usage_stats(days=days)
