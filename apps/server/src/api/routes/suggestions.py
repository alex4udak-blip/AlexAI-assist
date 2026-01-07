"""Suggestion endpoints."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.db.models import Suggestion
from src.services.agent_manager import AgentManagerService

router = APIRouter()


class SuggestionResponse(BaseModel):
    """Suggestion response schema."""

    id: UUID
    title: str
    description: str | None
    pattern_id: UUID | None
    agent_type: str
    agent_config: dict[str, Any]
    confidence: float
    impact: str
    time_saved_minutes: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionCreate(BaseModel):
    """Suggestion creation schema."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Suggestion title",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Suggestion description",
    )
    pattern_id: UUID | None = Field(
        default=None,
        description="Associated pattern ID",
    )
    agent_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of agent to create",
    )
    agent_config: dict[str, Any] = Field(
        ...,
        description="Agent configuration",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score",
    )
    impact: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="Expected impact",
    )
    time_saved_minutes: float = Field(
        default=0,
        ge=0,
        description="Estimated time saved in minutes",
    )


@router.get("", response_model=list[SuggestionResponse])
async def get_suggestions(
    status: str | None = Query(
        default=None,
        pattern="^(pending|accepted|dismissed)$",
        description="Filter by status",
    ),
    impact: str | None = Query(
        default=None,
        pattern="^(low|medium|high)$",
        description="Filter by impact level",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of suggestions to return",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[Suggestion]:
    """Get automation suggestions."""
    query = (
        select(Suggestion)
        .order_by(Suggestion.confidence.desc())
        .limit(limit)
    )

    if status:
        query = query.where(Suggestion.status == status)
    if impact:
        query = query.where(Suggestion.impact == impact)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=SuggestionResponse)
async def create_suggestion(
    data: SuggestionCreate,
    db: AsyncSession = Depends(get_db_session),
) -> Suggestion:
    """Create a new suggestion."""
    suggestion = Suggestion(
        title=data.title,
        description=data.description,
        pattern_id=data.pattern_id,
        agent_type=data.agent_type,
        agent_config=data.agent_config,
        confidence=data.confidence,
        impact=data.impact,
        time_saved_minutes=data.time_saved_minutes,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.post("/{suggestion_id}/accept")
async def accept_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Accept a suggestion and create an agent."""
    service = AgentManagerService(db)
    agent = await service.create_from_suggestion(suggestion_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    return {
        "message": "Suggestion accepted",
        "agent_id": str(agent.id),
    }


@router.post("/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Dismiss a suggestion."""
    result = await db.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    suggestion.status = "dismissed"
    suggestion.dismissed_at = datetime.now(UTC)
    await db.commit()

    return {"message": "Suggestion dismissed"}
