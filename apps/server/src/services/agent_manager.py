"""Agent management service."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Agent, AgentLog, Suggestion


class AgentManagerService:
    """Service for managing automation agents."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_agent(
        self,
        name: str,
        agent_type: str,
        trigger_config: dict[str, Any],
        actions: list[dict[str, Any]],
        description: str | None = None,
        settings: dict[str, Any] | None = None,
        code: str | None = None,
        suggestion_id: UUID | None = None,
    ) -> Agent:
        """Create a new agent."""
        agent = Agent(
            name=name,
            description=description,
            agent_type=agent_type,
            trigger_config=trigger_config,
            actions=actions,
            settings=settings or {},
            code=code,
            suggestion_id=suggestion_id,
            status="draft",
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def get_agents(
        self,
        status: str | None = None,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[Agent]:
        """Get all agents with optional filters."""
        query = select(Agent).order_by(Agent.created_at.desc()).limit(limit)

        if status:
            query = query.where(Agent.status == status)
        if agent_type:
            query = query.where(Agent.agent_type == agent_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_agent(self, agent_id: UUID) -> Agent | None:
        """Get a specific agent by ID."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def update_agent(
        self,
        agent_id: UUID,
        **kwargs: Any,
    ) -> Agent | None:
        """Update an agent."""
        agent = await self.get_agent(agent_id)
        if not agent:
            return None

        for key, value in kwargs.items():
            if hasattr(agent, key) and value is not None:
                setattr(agent, key, value)

        agent.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete an agent."""
        agent = await self.get_agent(agent_id)
        if not agent:
            return False

        await self.db.delete(agent)
        await self.db.commit()
        return True

    async def enable_agent(self, agent_id: UUID) -> Agent | None:
        """Enable an agent."""
        return await self.update_agent(agent_id, status="active")

    async def disable_agent(self, agent_id: UUID) -> Agent | None:
        """Disable an agent."""
        return await self.update_agent(agent_id, status="disabled")

    async def record_run(
        self,
        agent_id: UUID,
        success: bool,
        error: str | None = None,
        time_saved_seconds: float = 0,
    ) -> None:
        """Record an agent run."""
        agent = await self.get_agent(agent_id)
        if not agent:
            return

        agent.run_count += 1
        agent.last_run_at = datetime.now(UTC)

        if success:
            agent.success_count += 1
            agent.total_time_saved_seconds += time_saved_seconds
        else:
            agent.error_count += 1
            agent.last_error = error

        await self.db.commit()

    async def add_log(
        self,
        agent_id: UUID,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> AgentLog:
        """Add a log entry for an agent."""
        log = AgentLog(
            agent_id=agent_id,
            level=level,
            message=message,
            data=data,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_logs(
        self,
        agent_id: UUID,
        level: str | None = None,
        limit: int = 100,
    ) -> list[AgentLog]:
        """Get logs for an agent."""
        query = (
            select(AgentLog)
            .where(AgentLog.agent_id == agent_id)
            .order_by(AgentLog.created_at.desc())
            .limit(limit)
        )

        if level:
            query = query.where(AgentLog.level == level)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_from_suggestion(
        self,
        suggestion_id: UUID,
    ) -> Agent | None:
        """Create an agent from a suggestion."""
        result = await self.db.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            return None

        agent = await self.create_agent(
            name=suggestion.title,
            description=suggestion.description,
            agent_type=suggestion.agent_type,
            trigger_config=suggestion.agent_config.get("trigger", {}),
            actions=suggestion.agent_config.get("actions", []),
            suggestion_id=suggestion.id,
        )

        suggestion.status = "accepted"
        suggestion.accepted_at = datetime.now(UTC)
        await self.db.commit()

        return agent
