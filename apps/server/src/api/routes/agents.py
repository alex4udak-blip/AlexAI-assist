"""Agent endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.services.agent_executor import agent_executor
from src.services.agent_manager import AgentManagerService

router = APIRouter()


class AgentCreate(BaseModel):
    """Agent creation schema."""

    name: str
    description: str | None = None
    agent_type: str
    trigger_config: dict[str, Any]
    actions: list[dict[str, Any]]
    settings: dict[str, Any] | None = None
    code: str | None = None


class AgentUpdate(BaseModel):
    """Agent update schema."""

    name: str | None = None
    description: str | None = None
    trigger_config: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None
    settings: dict[str, Any] | None = None
    code: str | None = None
    status: str | None = None


class AgentResponse(BaseModel):
    """Agent response schema."""

    id: UUID
    name: str
    description: str | None
    agent_type: str
    trigger_config: dict[str, Any]
    actions: list[dict[str, Any]]
    settings: dict[str, Any]
    code: str | None
    status: str
    last_run_at: datetime | None
    last_error: str | None
    run_count: int
    success_count: int
    error_count: int
    total_time_saved_seconds: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentLogResponse(BaseModel):
    """Agent log response schema."""

    id: UUID
    agent_id: UUID
    level: str
    message: str
    data: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[AgentResponse])
async def get_agents(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentResponse]:
    """Get all agents."""
    service = AgentManagerService(db)
    return await service.get_agents(
        status=status,
        agent_type=agent_type,
        limit=limit,
    )


@router.post("", response_model=AgentResponse)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Create a new agent."""
    service = AgentManagerService(db)
    return await service.create_agent(
        name=data.name,
        description=data.description,
        agent_type=data.agent_type,
        trigger_config=data.trigger_config,
        actions=data.actions,
        settings=data.settings,
        code=data.code,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Get a specific agent."""
    service = AgentManagerService(db)
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Update an agent."""
    service = AgentManagerService(db)
    agent = await service.update_agent(
        agent_id,
        **data.model_dump(exclude_unset=True),
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete an agent."""
    service = AgentManagerService(db)
    success = await service.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted"}


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: UUID,
    context: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Manually run an agent."""
    service = AgentManagerService(db)
    agent = await service.get_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await agent_executor.execute(agent, context)

    # Record the run
    await service.record_run(
        agent_id=agent_id,
        success=result["success"],
        error=result.get("error"),
    )

    # Log the execution
    await service.add_log(
        agent_id=agent_id,
        level="info" if result["success"] else "error",
        message=f"Manual run {'succeeded' if result['success'] else 'failed'}",
        data=result,
    )

    return result


@router.post("/{agent_id}/enable", response_model=AgentResponse)
async def enable_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Enable an agent."""
    service = AgentManagerService(db)
    agent = await service.enable_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/disable", response_model=AgentResponse)
async def disable_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Disable an agent."""
    service = AgentManagerService(db)
    agent = await service.disable_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/logs", response_model=list[AgentLogResponse])
async def get_agent_logs(
    agent_id: UUID,
    level: str | None = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentLogResponse]:
    """Get logs for an agent."""
    service = AgentManagerService(db)
    return await service.get_logs(
        agent_id=agent_id,
        level=level,
        limit=limit,
    )
