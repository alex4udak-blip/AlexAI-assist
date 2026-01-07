"""Pattern endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.db.models import Pattern
from src.services.pattern_detector import PatternDetectorService

router = APIRouter()


class PatternResponse(BaseModel):
    """Pattern response schema."""

    id: UUID
    name: str
    description: str | None
    pattern_type: str
    trigger_conditions: dict[str, Any]
    sequence: list[dict[str, Any]]
    occurrences: int
    avg_duration_seconds: float | None
    automatable: bool
    complexity: str
    time_saved_minutes: float
    status: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[PatternResponse])
async def get_patterns(
    status: str | None = None,
    automatable: bool | None = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[Pattern]:
    """Get detected patterns."""
    service = PatternDetectorService(db)
    patterns = await service.get_patterns(
        status=status,
        automatable=automatable,
        limit=limit,
    )
    return patterns


@router.get("/detect")
async def detect_patterns(
    device_id: str | None = None,
    min_occurrences: int = Query(3, ge=1),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Run pattern detection on recent events."""
    service = PatternDetectorService(db)
    patterns = await service.detect_patterns(
        device_id=device_id,
        min_occurrences=min_occurrences,
    )
    return patterns


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Pattern:
    """Get a specific pattern."""
    service = PatternDetectorService(db)
    pattern = await service.get_pattern(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern
