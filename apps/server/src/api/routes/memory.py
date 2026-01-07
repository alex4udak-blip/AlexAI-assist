"""Memory API endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.services.memory import MemoryManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ===========================================
# SCHEMAS
# ===========================================


class AddFactRequest(BaseModel):
    """Request to add a fact."""

    content: str = Field(..., min_length=3, max_length=1000)
    fact_type: str = Field(default="fact")
    category: str | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class AddBeliefRequest(BaseModel):
    """Request to add a belief."""

    belief: str = Field(..., min_length=3, max_length=1000)
    belief_type: str = Field(default="inference")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class AddEntityRequest(BaseModel):
    """Request to add an entity."""

    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(default="concept")
    summary: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """Search request."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)


class MemoryContextResponse(BaseModel):
    """Memory context response."""

    persona: dict[str, Any] = Field(default_factory=dict)
    relevant_facts: list[dict[str, Any]] = Field(default_factory=list)
    beliefs: list[dict[str, Any]] = Field(default_factory=list)
    recent_experiences: list[dict[str, Any]] = Field(default_factory=list)
    entity_context: list[dict[str, Any]] = Field(default_factory=list)


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""

    facts: int = 0
    experiences: int = 0
    entities: int = 0
    active_beliefs: int = 0
    topics: int = 0
    scheduling: dict[str, Any] = Field(default_factory=dict)


# ===========================================
# CONTEXT ENDPOINTS
# ===========================================


@router.get("/context", response_model=MemoryContextResponse)
async def get_memory_context(
    query: str = Query(..., min_length=1, description="Query to get context for"),
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> MemoryContextResponse:
    """Get memory context for a query."""
    manager = MemoryManager(db, session_id)
    context = await manager.build_context_for_query(query)

    return MemoryContextResponse(
        persona=context.get("persona", {}),
        relevant_facts=context.get("relevant_facts", []),
        beliefs=context.get("beliefs", []),
        recent_experiences=context.get("recent_experiences", []),
        entity_context=context.get("entity_context", []),
    )


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> MemoryStatsResponse:
    """Get memory statistics."""
    manager = MemoryManager(db, session_id)
    stats = await manager.get_memory_stats()
    return MemoryStatsResponse(**stats)


# ===========================================
# FACT ENDPOINTS
# ===========================================


@router.post("/facts")
async def add_fact(
    data: AddFactRequest,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Add a new fact to memory."""
    manager = MemoryManager(db, session_id)
    fact = await manager.facts.add(
        content=data.content,
        fact_type=data.fact_type,
        category=data.category,
        confidence=data.confidence,
        source="manual",
    )
    await db.commit()

    return {
        "id": str(fact.id),
        "content": fact.content,
        "fact_type": fact.fact_type,
        "confidence": fact.confidence,
    }


@router.get("/facts")
async def list_facts(
    session_id: str = Query(default="default"),
    fact_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List facts from memory."""
    manager = MemoryManager(db, session_id)

    if fact_type:
        facts = await manager.facts.get_by_type(fact_type, limit=limit)
        return [
            {
                "id": str(f.id),
                "content": f.content,
                "fact_type": f.fact_type,
                "category": f.category,
                "confidence": f.confidence,
                "heat_score": f.heat_score,
            }
            for f in facts
        ]

    # Search with empty query returns all
    return await manager.facts.search("", limit=limit)


@router.post("/facts/search")
async def search_facts(
    data: SearchRequest,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Search facts by semantic similarity."""
    manager = MemoryManager(db, session_id)
    return await manager.facts.search(data.query, limit=data.limit)


@router.delete("/facts/{fact_id}")
async def invalidate_fact(
    fact_id: UUID,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Invalidate a fact (soft delete)."""
    manager = MemoryManager(db, session_id)
    success = await manager.facts.invalidate(fact_id)
    await db.commit()

    if not success:
        raise HTTPException(status_code=404, detail="Fact not found")

    return {"message": "Fact invalidated"}


# ===========================================
# BELIEF ENDPOINTS
# ===========================================


@router.post("/beliefs")
async def add_belief(
    data: AddBeliefRequest,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Add a new belief."""
    manager = MemoryManager(db, session_id)
    belief = await manager.beliefs.form(
        belief=data.belief,
        belief_type=data.belief_type,
        initial_confidence=data.confidence,
    )
    await db.commit()

    return {
        "id": str(belief.id),
        "belief": belief.belief,
        "belief_type": belief.belief_type,
        "confidence": belief.confidence,
    }


@router.get("/beliefs")
async def list_beliefs(
    session_id: str = Query(default="default"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List active beliefs."""
    manager = MemoryManager(db, session_id)
    return await manager.beliefs.get_active(min_confidence=min_confidence, limit=limit)


@router.post("/beliefs/{belief_id}/reinforce")
async def reinforce_belief(
    belief_id: UUID,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reinforce a belief."""
    manager = MemoryManager(db, session_id)
    belief = await manager.beliefs.reinforce(belief_id)
    await db.commit()

    if not belief:
        raise HTTPException(status_code=404, detail="Belief not found")

    return {
        "id": str(belief.id),
        "belief": belief.belief,
        "confidence": belief.confidence,
        "times_reinforced": belief.times_reinforced,
    }


@router.post("/beliefs/{belief_id}/challenge")
async def challenge_belief(
    belief_id: UUID,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Challenge a belief."""
    manager = MemoryManager(db, session_id)
    belief = await manager.beliefs.challenge(belief_id)
    await db.commit()

    if not belief:
        raise HTTPException(status_code=404, detail="Belief not found")

    return {
        "id": str(belief.id),
        "belief": belief.belief,
        "confidence": belief.confidence,
        "status": belief.status,
    }


# ===========================================
# ENTITY ENDPOINTS
# ===========================================


@router.post("/entities")
async def add_entity(
    data: AddEntityRequest,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Add or update an entity."""
    manager = MemoryManager(db, session_id)
    entity = await manager.observations.add_entity(
        name=data.name,
        entity_type=data.entity_type,
        summary=data.summary,
        attributes=data.attributes,
    )
    await db.commit()

    return {
        "id": str(entity.id),
        "name": entity.name,
        "entity_type": entity.entity_type,
        "mention_count": entity.mention_count,
    }


@router.get("/entities")
async def list_entities(
    session_id: str = Query(default="default"),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List top entities."""
    manager = MemoryManager(db, session_id)
    entities = await manager.observations.get_top_entities(limit=limit, entity_type=entity_type)

    return [
        {
            "id": str(e.id),
            "name": e.name,
            "entity_type": e.entity_type,
            "summary": e.summary,
            "mention_count": e.mention_count,
        }
        for e in entities
    ]


@router.post("/entities/search")
async def search_entities(
    data: SearchRequest,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Search entities."""
    manager = MemoryManager(db, session_id)
    return await manager.observations.search_entities(data.query, limit=data.limit)


@router.get("/entities/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: UUID,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get relationships for an entity."""
    manager = MemoryManager(db, session_id)
    return await manager.observations.get_entity_relationships(entity_id)


# ===========================================
# EXPERIENCE ENDPOINTS
# ===========================================


@router.get("/experiences")
async def list_experiences(
    session_id: str = Query(default="default"),
    experience_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List recent experiences."""
    manager = MemoryManager(db, session_id)
    types = [experience_type] if experience_type else None
    return await manager.experiences.get_recent(limit=limit, experience_types=types)


@router.post("/experiences/search")
async def search_experiences(
    data: SearchRequest,
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Search experiences."""
    manager = MemoryManager(db, session_id)
    return await manager.experiences.search(data.query, limit=data.limit)


# ===========================================
# PERSONA ENDPOINTS
# ===========================================


@router.get("/persona")
async def get_persona(
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get user persona profile."""
    manager = MemoryManager(db, session_id)
    return await manager.persona.get_active_profile()


@router.get("/topics")
async def list_topics(
    session_id: str = Query(default="default"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List recent discussion topics."""
    manager = MemoryManager(db, session_id)
    topics = await manager.persona.get_recent_topics(limit=limit)

    return [
        {
            "id": str(t.id),
            "topic": t.topic,
            "message_count": t.message_count,
            "last_discussed": t.last_discussed.isoformat() if t.last_discussed else None,
        }
        for t in topics
    ]


@router.get("/keywords")
async def list_keywords(
    session_id: str = Query(default="default"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List top keywords."""
    manager = MemoryManager(db, session_id)
    return await manager.persona.get_top_keywords(limit=limit)


# ===========================================
# MANAGEMENT ENDPOINTS
# ===========================================


@router.post("/consolidate")
async def trigger_consolidation(
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Trigger memory consolidation."""
    manager = MemoryManager(db, session_id)
    stats = await manager.consolidate()
    return {"message": "Consolidation complete", "stats": stats}


@router.delete("/clear")
async def clear_memory(
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Clear all memory for session."""
    manager = MemoryManager(db, session_id)
    await manager.clear_session()
    return {"message": f"Memory cleared for session {session_id}"}


@router.get("/operations")
async def list_operations(
    session_id: str = Query(default="default"),
    operation_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List recent memory operations."""
    manager = MemoryManager(db, session_id)
    return await manager.operator.get_recent_operations(
        limit=limit,
        operation_type=operation_type,
    )


@router.get("/scheduling/stats")
async def get_scheduling_stats(
    session_id: str = Query(default="default"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get memory scheduling statistics."""
    manager = MemoryManager(db, session_id)
    return await manager.scheduler.get_scheduling_stats()


@router.get("/hot")
async def get_hot_memories(
    session_id: str = Query(default="default"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get memories with highest heat scores."""
    manager = MemoryManager(db, session_id)
    return await manager.scheduler.get_hot_memories(limit=limit)
