"""Session tracking endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.db.models import Session
from src.services.session_tracker import SessionTracker

router = APIRouter()
session_tracker = SessionTracker()


class SessionResponse(BaseModel):
    """Session response schema."""

    id: UUID
    session_id: str
    device_id: str
    start_time: datetime
    end_time: datetime | None
    duration_minutes: float | None
    apps_used: list[str]
    events_count: int
    productivity_score: float | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    """Session summary statistics response."""

    total_sessions: int
    total_minutes: float
    avg_session_minutes: float
    avg_productivity_score: float
    most_used_apps: list[dict[str, Any]]
    active_sessions: int


class SessionPatternsResponse(BaseModel):
    """Session patterns analysis response."""

    patterns_found: bool
    peak_hours: list[dict[str, Any]] | None = None
    avg_session_duration_minutes: float | None = None
    avg_productivity_score: float | None = None
    total_sessions_analyzed: int | None = None
    days_analyzed: int | None = None


@router.post("/end-inactive")
async def end_inactive_sessions(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    End sessions that have been inactive for too long.

    This endpoint should be called periodically (e.g., via a cron job)
    to clean up stale sessions.
    """
    ended_session_ids = await session_tracker.end_inactive_sessions(db, device_id)

    return {
        "ended_sessions": len(ended_session_ids),
        "session_ids": ended_session_ids,
    }


@router.get("/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    device_id: str = Query(
        ...,
        max_length=255,
        description="Device ID",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of days to analyze",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> SessionSummaryResponse:
    """Get session summary statistics for a device."""
    summary = await session_tracker.get_session_summary(db, device_id, days)
    return SessionSummaryResponse(**summary)


@router.get("/patterns", response_model=SessionPatternsResponse)
async def get_session_patterns(
    device_id: str = Query(
        ...,
        max_length=255,
        description="Device ID",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of days to analyze",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> SessionPatternsResponse:
    """Detect patterns in user sessions."""
    patterns = await session_tracker.detect_session_patterns(db, device_id, days)
    return SessionPatternsResponse(**patterns)


@router.get("", response_model=list[SessionResponse])
async def get_sessions(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    active_only: bool = Query(
        default=False,
        description="Show only active sessions",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of sessions to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[Session]:
    """Query sessions with filters."""
    from sqlalchemy import desc, select

    query = select(Session).order_by(desc(Session.start_time)).limit(limit).offset(offset)

    if device_id:
        query = query.where(Session.device_id == device_id)

    if active_only:
        query = query.where(Session.end_time.is_(None))

    result = await db.execute(query)
    return list(result.scalars().all())
