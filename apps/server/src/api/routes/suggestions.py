"""Suggestion endpoints."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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

    title: str
    description: str | None = None
    pattern_id: UUID | None = None
    agent_type: str
    agent_config: dict[str, Any]
    confidence: float = 0.5
    impact: str = "medium"
    time_saved_minutes: float = 0


@router.get("", response_model=list[SuggestionResponse])
async def get_suggestions(
    status: str | None = Query(None),
    impact: str | None = None,
    limit: int = Query(50, le=100),
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
