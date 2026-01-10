"""
Memory Scheduler - MemOS style heat scoring and scheduling.
Implements MemOS's MemScheduler for memory prioritization.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import validate_session_id
from src.db.models.memory import MemoryCube, MemoryFact

from .confidence_utils import calculate_time_decay

logger = logging.getLogger(__name__)


class MemScheduler:
    """
    MemOS-style memory scheduler.
    Features:
    - Heat scoring (recency + frequency)
    - Next-scene prediction
    - Memory lifecycle management
    - Decay and archival
    """

    # Decay rates per day (used for time-based exponential decay)
    # These correspond to different half-lives in the exponential decay formula
    DECAY_RATE_FAST = 0.1  # For low-importance memories (short-term, ~1 week half-life)
    DECAY_RATE_NORMAL = 0.05  # For normal memories (medium-term, ~2 weeks half-life)
    DECAY_RATE_SLOW = 0.01  # For important memories (long-term, ~4 weeks half-life)

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        # Validate session_id to prevent session forgery
        self.session_id = validate_session_id(session_id)

    def get_decay_rate_for_type(self, memory_type: str, importance: float = 1.0) -> float:
        """
        Get the appropriate decay rate for a memory type and importance.

        Args:
            memory_type: Type of memory (fact, belief, experience, entity)
            importance: Importance score (0.0 to 2.0)

        Returns:
            Decay rate per day
        """
        # Beliefs decay slowest (long-term knowledge)
        if memory_type == "belief":
            return self.DECAY_RATE_SLOW

        # Facts decay based on importance
        elif memory_type == "fact":
            if importance >= 1.5:
                return self.DECAY_RATE_SLOW
            elif importance >= 0.8:
                return self.DECAY_RATE_NORMAL
            else:
                return self.DECAY_RATE_FAST

        # Experiences decay normally
        elif memory_type == "experience":
            return self.DECAY_RATE_NORMAL

        # Entities decay slowly (represent persistent knowledge)
        elif memory_type == "entity":
            return self.DECAY_RATE_SLOW

        # Default to normal decay
        return self.DECAY_RATE_NORMAL

    async def calculate_heat_score(
        self,
        access_count: int,
        last_accessed: datetime | None,
        created_at: datetime,
        importance: float = 1.0,
    ) -> float:
        """
        Calculate heat score for a memory.
        Higher scores = more likely to be retrieved.

        Formula: (frequency * recency * importance)
        - frequency: log(access_count + 1)
        - recency: decay based on time since last access
        - importance: user-defined or inferred
        """
        import math

        # Frequency component
        frequency = math.log(access_count + 1) / 5.0  # Normalized

        # Recency component
        if last_accessed:
            hours_since_access = (datetime.now(UTC).replace(tzinfo=None) - last_accessed).total_seconds() / 3600
        else:
            hours_since_access = (datetime.now(UTC).replace(tzinfo=None) - created_at).total_seconds() / 3600

        # Exponential decay
        recency = math.exp(-hours_since_access / 168)  # Week half-life

        # Combined score
        heat = (frequency * 0.3 + recency * 0.5 + importance * 0.2)
        return min(2.0, max(0.0, heat))

    async def update_heat_scores(
        self,
        operations: list[dict[str, Any]],
    ) -> None:
        """
        Update heat scores based on recent operations.
        Applies time-based decay first, then adds boost for current access.
        """
        # Group operations by table for batch processing
        updates_by_table: dict[str, list[str]] = {}

        for op in operations:
            memory_id = op.get("memory_id")
            memory_type = op.get("memory_type")

            if not memory_id:
                continue

            # Update heat score in the appropriate table
            table = self._get_table_for_type(memory_type)
            # Extra safety: verify table is in whitelist
            if table and table in self.ALLOWED_TABLES:
                if table not in updates_by_table:
                    updates_by_table[table] = []
                updates_by_table[table].append(str(memory_id))

        # Batch update each table
        for table, memory_ids in updates_by_table.items():
            if memory_ids:
                # Apply decay based on time since last access, then boost
                await self.db.execute(
                    text(
                        f"""
                        UPDATE {table}
                        SET heat_score = LEAST(2.0, GREATEST(0.0,
                            -- Apply exponential decay based on time since last access
                            CASE
                                WHEN last_accessed IS NOT NULL THEN
                                    heat_score * EXP(-EXTRACT(EPOCH FROM (NOW() - last_accessed)) / (168.0 * 3600.0))
                                WHEN created_at IS NOT NULL THEN
                                    heat_score * EXP(-EXTRACT(EPOCH FROM (NOW() - created_at)) / (168.0 * 3600.0))
                                ELSE
                                    heat_score
                            END
                            -- Add boost for current access
                            + 0.2
                        )),
                        access_count = COALESCE(access_count, 0) + 1,
                        last_accessed = NOW()
                        WHERE id = ANY(:memory_ids)
                        """
                    ).bindparams(memory_ids=memory_ids)
                )

    # Whitelist of allowed memory types and their corresponding tables
    TYPE_TO_TABLE: dict[str, str] = {
        "fact": "memory_facts",
        "experience": "memory_experiences",
        "entity": "memory_entities",
        "belief": "memory_beliefs",
    }

    # Frozen set for fast lookup
    ALLOWED_TABLES = frozenset(TYPE_TO_TABLE.values())

    def _get_table_for_type(self, memory_type: str | None) -> str | None:
        """Get table name for memory type from whitelist."""
        if memory_type is None:
            return None
        return self.TYPE_TO_TABLE.get(memory_type)

    async def predict_and_preload(self, query: str) -> list[dict[str, Any]]:
        """
        Predict and preload relevant memories for the next interaction.
        Returns memories that should be included in context.
        """
        # Get high-heat facts
        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.heat_score >= 0.5,
                )
            )
            .order_by(MemoryFact.heat_score.desc())
            .limit(5)
        )
        hot_facts = result.scalars().all()

        preloaded: list[dict[str, Any]] = []
        for fact in hot_facts:
            preloaded.append({
                "type": "fact",
                "id": str(fact.id),
                "content": fact.content,
                "heat_score": fact.heat_score,
            })

        # Mark as scheduled
        for item in preloaded:
            await self._mark_scheduled(str(item["type"]), UUID(str(item["id"])))

        return preloaded

    async def _mark_scheduled(self, memory_type: str, memory_id: UUID) -> None:
        """Mark a memory as scheduled for retrieval."""
        # Update or create MemCube
        result = await self.db.execute(
            select(MemoryCube).where(
                and_(
                    MemoryCube.memory_type == memory_type,
                    MemoryCube.memory_id == memory_id,
                )
            )
        )
        cube = result.scalar_one_or_none()

        if cube:
            cube.schedule_count += 1
            cube.last_scheduled = datetime.now(UTC).replace(tzinfo=None)
        else:
            cube = MemoryCube(
                id=uuid4(),
                session_id=self.session_id,
                memory_type=memory_type,
                memory_id=memory_id,
                schedule_count=1,
                last_scheduled=datetime.now(UTC).replace(tzinfo=None),
            )
            self.db.add(cube)

    async def apply_decay(self) -> dict[str, int]:
        """
        Apply time-based decay to all memories.
        Returns counts of decayed memories per type.

        Uses exponential decay based on time since last access.
        Different memory types use different decay rates from class constants.

        Note: This uses SQL for batch operations for performance.
        For individual calculations, use calculate_time_decay from confidence_utils.
        """
        decay_counts = {}

        # Decay facts - uses decay_rate column from database (per-memory rate)
        # Apply exponential decay: heat_score * exp(-time_hours / 168)
        result = await self.db.execute(
            text(
                """
                UPDATE memory_facts
                SET heat_score = GREATEST(0.0,
                    heat_score * EXP(
                        -EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed, created_at)))
                        / (168.0 * 3600.0)
                    )
                )
                WHERE session_id = :session_id
                    AND heat_score > 0.0
                    AND (last_accessed < NOW() - INTERVAL '1 hour' OR last_accessed IS NULL)
                RETURNING id
                """
            ).bindparams(session_id=self.session_id)
        )
        decay_counts["facts"] = len(result.fetchall())

        # Decay beliefs - slower decay rate
        # Only decay beliefs not recently reinforced (older than 7 days)
        # Use DECAY_RATE_SLOW constant value
        result = await self.db.execute(
            text(
                """
                UPDATE memory_beliefs
                SET confidence = GREATEST(0.1,
                    confidence * EXP(
                        -EXTRACT(EPOCH FROM (NOW() - COALESCE(last_reinforced, formed_at)))
                        / (672.0 * 3600.0)
                    )
                )
                WHERE session_id = :session_id
                    AND status = 'active'
                    AND confidence > 0.1
                    AND COALESCE(last_reinforced, formed_at) < NOW() - INTERVAL '7 days'
                RETURNING id
                """
            ).bindparams(session_id=self.session_id)
        )
        decay_counts["beliefs"] = len(result.fetchall())

        logger.info(f"Applied decay: {decay_counts}")
        return decay_counts

    async def calculate_memory_decay(
        self,
        memory_type: str,
        memory_id: UUID,
    ) -> float | None:
        """
        Calculate decay for a specific memory using unified confidence calculation.
        Returns the new confidence/heat value, or None if memory not found.

        This method demonstrates using the unified confidence_utils for individual calculations.
        Use apply_decay() for batch operations instead.
        """
        if memory_type == "fact":
            from src.db.models.memory import MemoryFact
            fact_result = await self.db.execute(
                select(MemoryFact).where(MemoryFact.id == memory_id)
            )
            fact: MemoryFact | None = fact_result.scalar_one_or_none()
            if not fact or not fact.last_accessed:
                return None

            # Use unified time decay calculation
            new_confidence = calculate_time_decay(
                current_confidence=fact.confidence,
                last_reinforced=fact.last_accessed,
                now=datetime.now(UTC).replace(tzinfo=None),
                decay_rate=self.DECAY_RATE_NORMAL,
                min_confidence=0.1,
            )
            return new_confidence

        elif memory_type == "belief":
            from src.db.models.memory import MemoryBelief
            belief_result = await self.db.execute(
                select(MemoryBelief).where(MemoryBelief.id == memory_id)
            )
            belief: MemoryBelief | None = belief_result.scalar_one_or_none()
            if not belief or not belief.last_reinforced:
                return None

            # Use unified time decay calculation
            new_confidence = calculate_time_decay(
                current_confidence=belief.confidence,
                last_reinforced=belief.last_reinforced,
                now=datetime.now(UTC).replace(tzinfo=None),
                decay_rate=self.DECAY_RATE_SLOW,  # Beliefs decay slower
                min_confidence=0.1,
            )
            return new_confidence

        return None

    async def get_hot_memories(
        self,
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get memories with highest heat scores."""
        if memory_type == "fact" or memory_type is None:
            result = await self.db.execute(
                select(MemoryFact)
                .where(
                    and_(
                        MemoryFact.session_id == self.session_id,
                        MemoryFact.heat_score > 0.0,
                    )
                )
                .order_by(MemoryFact.heat_score.desc())
                .limit(limit)
            )

            memories = []
            for fact in result.scalars().all():
                memories.append({
                    "type": "fact",
                    "id": str(fact.id),
                    "content": fact.content,
                    "heat_score": fact.heat_score,
                    "access_count": fact.access_count,
                    "last_accessed": fact.last_accessed.isoformat() if fact.last_accessed else None,
                })

            return memories

        return []

    async def get_cold_memories(
        self,
        threshold: float = 0.1,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get memories that may need archival."""
        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.heat_score < threshold,
                )
            )
            .order_by(MemoryFact.heat_score.asc())
            .limit(limit)
        )

        memories = []
        for fact in result.scalars().all():
            memories.append({
                "type": "fact",
                "id": str(fact.id),
                "content": fact.content,
                "heat_score": fact.heat_score,
                "created_at": fact.created_at.isoformat() if fact.created_at else None,
            })

        return memories

    async def archive_cold_memories(
        self,
        threshold: float = 0.05,
        max_archive: int = 20,
    ) -> int:
        """
        Archive cold memories.
        Sets retention_policy to 'archived' in MemCube.
        Returns number of archived memories.
        """
        cold = await self.get_cold_memories(threshold, max_archive)

        if not cold:
            return 0

        # Extract memory IDs for bulk fetch
        memory_ids = [UUID(mem["id"]) for mem in cold]

        # Bulk fetch existing MemCubes
        result = await self.db.execute(
            select(MemoryCube).where(
                and_(
                    MemoryCube.memory_type == cold[0]["type"],  # All are 'fact' type
                    MemoryCube.memory_id.in_(memory_ids),
                )
            )
        )
        existing_cubes = result.scalars().all()

        # Create a map of existing cubes by memory_id
        cubes_by_id = {cube.memory_id: cube for cube in existing_cubes}

        archived = 0
        for mem in cold:
            mem_id = UUID(mem["id"])
            cube = cubes_by_id.get(mem_id)

            if cube:
                cube.retention_policy = "archived"
                cube.updated_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                cube = MemoryCube(
                    id=uuid4(),
                    session_id=self.session_id,
                    memory_type=mem["type"],
                    memory_id=mem_id,
                    retention_policy="archived",
                    heat_score=mem["heat_score"],
                )
                self.db.add(cube)

            archived += 1

        logger.info(f"Archived {archived} cold memories")
        return archived

    async def boost_memory(
        self,
        memory_type: str,
        memory_id: UUID,
        boost_amount: float = 0.3,
    ) -> None:
        """Manually boost a memory's heat score."""
        table = self._get_table_for_type(memory_type)
        # Extra safety: verify table is in whitelist (should always pass)
        if table and table in self.ALLOWED_TABLES:
            # Validate boost_amount
            boost_amount = max(0.0, min(1.0, float(boost_amount)))
            await self.db.execute(
                text(
                    f"""
                    UPDATE {table}
                    SET heat_score = LEAST(2.0, heat_score + :boost),
                        last_accessed = NOW()
                    WHERE id = :memory_id
                    """
                ).bindparams(boost=boost_amount, memory_id=str(memory_id))
            )

    async def get_scheduling_stats(self) -> dict[str, Any]:
        """Get memory scheduling statistics."""
        # Count by heat level
        hot_count = await self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM memory_facts
                WHERE session_id = :session_id AND heat_score >= 0.5
                """
            ).bindparams(session_id=self.session_id)
        )

        warm_count = await self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM memory_facts
                WHERE session_id = :session_id
                    AND heat_score >= 0.1 AND heat_score < 0.5
                """
            ).bindparams(session_id=self.session_id)
        )

        cold_count = await self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM memory_facts
                WHERE session_id = :session_id AND heat_score < 0.1
                """
            ).bindparams(session_id=self.session_id)
        )

        # Recent schedules
        scheduled_count = await self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM memory_cubes
                WHERE session_id = :session_id
                    AND last_scheduled > NOW() - INTERVAL '1 day'
                """
            ).bindparams(session_id=self.session_id)
        )

        return {
            "hot_memories": hot_count.scalar() or 0,
            "warm_memories": warm_count.scalar() or 0,
            "cold_memories": cold_count.scalar() or 0,
            "recently_scheduled": scheduled_count.scalar() or 0,
        }
