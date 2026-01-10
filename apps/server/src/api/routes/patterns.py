"""Pattern endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
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
    status: str | None = Query(
        default=None,
        pattern="^(active|inactive|archived)$",
        description="Filter by pattern status",
    ),
    automatable: bool | None = Query(
        default=None,
        description="Filter by whether pattern is automatable",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of patterns to return",
    ),
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


class AppSequencePattern(BaseModel):
    """Detected app sequence pattern."""

    type: str = Field(..., description="Pattern type")
    sequence: list[str] = Field(..., description="App sequence")
    occurrences: int = Field(..., description="Number of occurrences")
    automatable: bool = Field(..., description="Whether pattern can be automated")


class TimePattern(BaseModel):
    """Detected time-based pattern."""

    type: str = Field(..., description="Pattern type")
    hour: int = Field(..., description="Hour of day (0-23)")
    app: str = Field(..., description="Application name")
    occurrences: int = Field(..., description="Number of occurrences")
    automatable: bool = Field(..., description="Whether pattern can be automated")


class ContextSwitches(BaseModel):
    """Context switching analysis."""

    total_switches: int = Field(..., description="Total number of context switches")
    switch_rate: float = Field(..., description="Switch rate per event")
    assessment: str = Field(..., description="Assessment (low, medium, high)")


class PatternDetectionResult(BaseModel):
    """Pattern detection result."""

    app_sequences: list[AppSequencePattern] = Field(
        default_factory=list,
        description="Detected app sequence patterns",
    )
    time_patterns: list[TimePattern] = Field(
        default_factory=list,
        description="Detected time-based patterns",
    )
    context_switches: ContextSwitches = Field(
        ...,
        description="Context switching analysis",
    )


@router.get("/detect", response_model=PatternDetectionResult)
async def detect_patterns(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    min_occurrences: int = Query(
        default=3,
        ge=1,
        le=100,
        description="Minimum number of occurrences to detect pattern",
    ),
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
