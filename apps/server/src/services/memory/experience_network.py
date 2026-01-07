"""
Experience Network - What happened (agent runs, user actions, conversations).
Implements Hindsight's Experience Network with procedural learning.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.memory import MemoryExperience, MemoryProcedure
from .embeddings import embedding_service

logger = logging.getLogger(__name__)


class ExperienceNetwork:
    """
    Manages experiences - what the agent/user has done.
    Features:
    - Agent execution tracking
    - User action recording
    - Lesson learning
    - Procedural extraction (Mem-alpha)
    """

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        self.session_id = session_id

    async def add(
        self,
        description: str,
        experience_type: str = "conversation",
        action_taken: str | None = None,
        outcome: str = "success",
        outcome_details: dict[str, Any] | None = None,
        lesson_learned: str | None = None,
        should_repeat: bool | None = None,
        agent_id: UUID | None = None,
        duration_seconds: int | None = None,
        occurred_at: datetime | None = None,
    ) -> MemoryExperience:
        """
        Add a new experience.

        Args:
            description: What happened
            experience_type: Type (agent_run, user_action, conversation, pattern_detected)
            action_taken: What action was performed
            outcome: Result (success, failure, partial, unknown)
            outcome_details: Additional details
            lesson_learned: What we learned
            should_repeat: Should this be repeated?
            agent_id: Associated agent
            duration_seconds: How long it took
            occurred_at: When it happened

        Returns:
            Created MemoryExperience
        """
        experience = MemoryExperience(
            id=uuid4(),
            session_id=self.session_id,
            experience_type=experience_type,
            description=description,
            action_taken=action_taken,
            outcome=outcome,
            outcome_details=outcome_details or {},
            lesson_learned=lesson_learned,
            should_repeat=should_repeat,
            agent_id=agent_id,
            duration_seconds=duration_seconds,
            occurred_at=occurred_at or datetime.utcnow(),
        )

        self.db.add(experience)
        await self.db.flush()

        # Generate and store embedding
        embedding = embedding_service.embed(description)
        if embedding:
            vector_str = embedding_service.to_pgvector_str(embedding)
            await self.db.execute(
                text(
                    f"""
                    UPDATE memory_experiences
                    SET embedding_vector = '{vector_str}'::vector
                    WHERE id = :exp_id
                    """
                ).bindparams(exp_id=str(experience.id))
            )

        logger.info(f"Added experience: {description[:50]}... (type={experience_type})")
        return experience

    async def get_recent(
        self,
        limit: int = 10,
        experience_types: list[str] | None = None,
        outcomes: list[str] | None = None,
        hours: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get recent experiences.

        Args:
            limit: Maximum results
            experience_types: Filter by types
            outcomes: Filter by outcomes
            hours: Limit to last N hours

        Returns:
            List of experiences
        """
        filters = [MemoryExperience.session_id == self.session_id]

        if experience_types:
            filters.append(MemoryExperience.experience_type.in_(experience_types))

        if outcomes:
            filters.append(MemoryExperience.outcome.in_(outcomes))

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            filters.append(MemoryExperience.occurred_at >= cutoff)

        result = await self.db.execute(
            select(MemoryExperience)
            .where(and_(*filters))
            .order_by(MemoryExperience.occurred_at.desc())
            .limit(limit)
        )

        experiences = []
        for exp in result.scalars().all():
            experiences.append({
                "id": str(exp.id),
                "description": exp.description,
                "experience_type": exp.experience_type,
                "action_taken": exp.action_taken,
                "outcome": exp.outcome,
                "outcome_details": exp.outcome_details,
                "lesson_learned": exp.lesson_learned,
                "should_repeat": exp.should_repeat,
                "occurred_at": exp.occurred_at.isoformat(),
                "duration_seconds": exp.duration_seconds,
            })

        return experiences

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search experiences by semantic similarity.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of experiences with scores
        """
        embedding = embedding_service.embed(query)
        if not embedding:
            return await self._text_search(query, limit)

        vector_str = embedding_service.to_pgvector_str(embedding)

        result = await self.db.execute(
            text(
                f"""
                SELECT
                    id,
                    description,
                    experience_type,
                    outcome,
                    lesson_learned,
                    occurred_at,
                    1 - (embedding_vector <=> '{vector_str}'::vector) as score
                FROM memory_experiences
                WHERE session_id = :session_id
                    AND embedding_vector IS NOT NULL
                ORDER BY embedding_vector <=> '{vector_str}'::vector
                LIMIT :limit
                """
            ).bindparams(session_id=self.session_id, limit=limit)
        )

        experiences = []
        for row in result.fetchall():
            experiences.append({
                "id": str(row[0]),
                "description": row[1],
                "experience_type": row[2],
                "outcome": row[3],
                "lesson_learned": row[4],
                "occurred_at": row[5].isoformat() if row[5] else None,
                "score": float(row[6]) if row[6] else 0.0,
            })

        return experiences

    async def _text_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fallback text search."""
        result = await self.db.execute(
            select(MemoryExperience)
            .where(
                and_(
                    MemoryExperience.session_id == self.session_id,
                    MemoryExperience.description.ilike(f"%{query}%"),
                )
            )
            .order_by(MemoryExperience.occurred_at.desc())
            .limit(limit)
        )

        experiences = []
        for exp in result.scalars().all():
            experiences.append({
                "id": str(exp.id),
                "description": exp.description,
                "experience_type": exp.experience_type,
                "outcome": exp.outcome,
                "occurred_at": exp.occurred_at.isoformat(),
                "score": 0.5,
            })

        return experiences

    async def get_agent_experiences(
        self,
        agent_id: UUID,
        limit: int = 20,
    ) -> list[MemoryExperience]:
        """Get experiences for a specific agent."""
        result = await self.db.execute(
            select(MemoryExperience)
            .where(
                and_(
                    MemoryExperience.session_id == self.session_id,
                    MemoryExperience.agent_id == agent_id,
                )
            )
            .order_by(MemoryExperience.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_success_rate(
        self,
        experience_type: str | None = None,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Calculate success rate for experiences."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        filters = [
            MemoryExperience.session_id == self.session_id,
            MemoryExperience.occurred_at >= cutoff,
        ]

        if experience_type:
            filters.append(MemoryExperience.experience_type == experience_type)

        result = await self.db.execute(
            select(
                MemoryExperience.outcome,
                func.count(MemoryExperience.id),
            )
            .where(and_(*filters))
            .group_by(MemoryExperience.outcome)
        )

        outcomes = {row[0]: row[1] for row in result.fetchall()}
        total = sum(outcomes.values())

        if total == 0:
            return {"success_rate": 0.0, "total": 0, "outcomes": {}}

        success = outcomes.get("success", 0)
        return {
            "success_rate": success / total,
            "total": total,
            "outcomes": outcomes,
        }

    async def get_lessons(self, limit: int = 10) -> list[str]:
        """Get learned lessons from experiences."""
        result = await self.db.execute(
            select(MemoryExperience.lesson_learned)
            .where(
                and_(
                    MemoryExperience.session_id == self.session_id,
                    MemoryExperience.lesson_learned.isnot(None),
                )
            )
            .order_by(MemoryExperience.occurred_at.desc())
            .limit(limit)
        )

        return [row[0] for row in result.fetchall() if row[0]]

    async def extract_procedures(self) -> list[MemoryProcedure]:
        """
        Extract procedures from repeated successful experiences.
        Implements Mem-alpha style procedural learning.
        """
        # Find repeated patterns in successful experiences
        result = await self.db.execute(
            text(
                """
                SELECT
                    experience_type,
                    action_taken,
                    COUNT(*) as count,
                    AVG(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as success_rate,
                    AVG(duration_seconds) as avg_duration
                FROM memory_experiences
                WHERE session_id = :session_id
                    AND action_taken IS NOT NULL
                    AND outcome IS NOT NULL
                GROUP BY experience_type, action_taken
                HAVING COUNT(*) >= 3
                    AND AVG(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) >= 0.7
                ORDER BY count DESC
                LIMIT 10
                """
            ).bindparams(session_id=self.session_id)
        )

        procedures = []
        for row in result.fetchall():
            exp_type, action, count, success_rate, avg_duration = row

            # Check if procedure already exists
            existing = await self.db.execute(
                select(MemoryProcedure).where(
                    and_(
                        MemoryProcedure.session_id == self.session_id,
                        MemoryProcedure.name == action[:100],
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Create procedure
            procedure = MemoryProcedure(
                id=uuid4(),
                session_id=self.session_id,
                name=action[:100] if action else f"Procedure from {exp_type}",
                description=f"Learned from {count} successful {exp_type} experiences",
                procedure_type=exp_type,
                success_count=int(count * success_rate) if success_rate else 0,
                failure_count=int(count * (1 - success_rate)) if success_rate else 0,
                avg_success_rate=float(success_rate) if success_rate else 0.0,
                avg_time_saved=float(avg_duration) if avg_duration else 0.0,
            )
            self.db.add(procedure)
            procedures.append(procedure)

            logger.info(f"Extracted procedure: {procedure.name}")

        return procedures

    async def mark_procedural(
        self,
        experience_id: UUID,
        procedure_id: UUID,
    ) -> None:
        """Mark experience as part of a procedure."""
        result = await self.db.execute(
            select(MemoryExperience).where(MemoryExperience.id == experience_id)
        )
        exp = result.scalar_one_or_none()
        if exp:
            exp.is_procedural = True
            exp.procedure_id = procedure_id

    async def count_by_type(self, hours: int = 24) -> dict[str, int]:
        """Count experiences by type."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(
                MemoryExperience.experience_type,
                func.count(MemoryExperience.id),
            )
            .where(
                and_(
                    MemoryExperience.session_id == self.session_id,
                    MemoryExperience.occurred_at >= cutoff,
                )
            )
            .group_by(MemoryExperience.experience_type)
        )

        return {row[0]: row[1] for row in result.fetchall() if row[0]}
