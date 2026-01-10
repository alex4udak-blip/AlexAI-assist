"""
Fact Network - Objective truths about the user.
Implements Hindsight's Fact Network with temporal validity.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import validate_session_id
from src.db.models.memory import MemoryFact, MemoryLink

from .confidence_utils import calculate_reinforcement, calculate_weighted_average
from .embeddings import check_pgvector_available, embedding_service

# Import sanitization function to prevent prompt injection
from .memory_operations import sanitize_user_input

logger = logging.getLogger(__name__)


class FactNetwork:
    """
    Manages objective facts about the user.
    Features:
    - Temporal validity (valid_from, valid_to)
    - Confidence tracking
    - Heat-based retrieval (MemOS)
    - Vector similarity search
    """

    # Allowed fact types for validation
    ALLOWED_FACT_TYPES = frozenset({
        "fact", "preference", "habit", "goal", "demographic",
        "skill", "opinion", "world_fact", "persona_attribute", "persona_event",
    })

    # Allowed categories for validation
    ALLOWED_CATEGORIES = frozenset({
        "work", "personal", "health", "finance", "learning", "other",
    })

    # Allowed sources for validation
    ALLOWED_SOURCES = frozenset({
        "chat", "pattern", "agent", "manual", "inferred",
    })

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        # Validate session_id to prevent session forgery
        self.session_id = validate_session_id(session_id)

    async def add(
        self,
        content: str,
        fact_type: str = "fact",
        category: str | None = None,
        confidence: float = 1.0,
        source: str = "chat",
        source_id: UUID | None = None,
        is_persona_attribute: bool = False,
        is_persona_event: bool = False,
        event_time: datetime | None = None,
        keywords: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> MemoryFact:
        """
        Add a new fact to the network.

        Args:
            content: The fact content
            fact_type: Type of fact (preference, habit, goal, demographic, skill, world_fact)
            category: Category (work, personal, health, finance, learning)
            confidence: Initial confidence (0-1)
            source: Where this fact came from (chat, pattern, agent, manual, inferred)
            source_id: ID of source record
            is_persona_attribute: O-Mem persona attribute (Pa)
            is_persona_event: O-Mem persona event (Pf)
            event_time: When fact occurred in real world
            keywords: A-MEM keywords
            tags: A-MEM tags

        Returns:
            Created MemoryFact

        Raises:
            ValueError: If validation fails
        """
        # Validate required string fields
        if not content or not content.strip():
            raise ValueError("content is required and cannot be empty")

        content = content.strip()

        # Validate string length
        if len(content) > 5000:
            raise ValueError(f"content exceeds maximum length of 5000 characters (got {len(content)})")

        # Validate fact_type
        if fact_type not in self.ALLOWED_FACT_TYPES:
            raise ValueError(
                f"Invalid fact_type: {fact_type}. "
                f"Allowed values: {', '.join(sorted(self.ALLOWED_FACT_TYPES))}"
            )

        # Validate category if provided
        if category is not None and category not in self.ALLOWED_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Allowed values: {', '.join(sorted(self.ALLOWED_CATEGORIES))}"
            )

        # Validate source
        if source not in self.ALLOWED_SOURCES:
            raise ValueError(
                f"Invalid source: {source}. "
                f"Allowed values: {', '.join(sorted(self.ALLOWED_SOURCES))}"
            )

        # Validate confidence range
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be between 0 and 1 (got {confidence})")

        # Validate keywords list
        if keywords is not None:
            if not isinstance(keywords, list):
                raise ValueError("keywords must be a list")
            if len(keywords) > 50:
                raise ValueError(f"keywords list exceeds maximum of 50 items (got {len(keywords)})")
            for keyword in keywords:
                if not isinstance(keyword, str) or len(keyword) > 100:
                    raise ValueError("each keyword must be a string with max length 100")

        # Validate tags list
        if tags is not None:
            if not isinstance(tags, list):
                raise ValueError("tags must be a list")
            if len(tags) > 50:
                raise ValueError(f"tags list exceeds maximum of 50 items (got {len(tags)})")
            for tag in tags:
                if not isinstance(tag, str) or len(tag) > 100:
                    raise ValueError("each tag must be a string with max length 100")

        # Check for duplicates
        existing = await self._find_similar(content, threshold=0.9)
        if existing:
            # Update existing instead of creating duplicate
            await self._reinforce(existing[0]["id"], confidence)
            result = await self.db.execute(
                select(MemoryFact).where(MemoryFact.id == UUID(existing[0]["id"]))
            )
            return result.scalar_one()

        # Create new fact
        fact = MemoryFact(
            id=uuid4(),
            session_id=self.session_id,
            content=content,
            fact_type=fact_type,
            category=category,
            confidence=confidence,
            source=source,
            source_id=source_id,
            is_persona_attribute=is_persona_attribute,
            is_persona_event=is_persona_event,
            event_time=event_time,
            record_time=datetime.now(UTC).replace(tzinfo=None),
            valid_from=datetime.now(UTC).replace(tzinfo=None),
            keywords=keywords or [],
            tags=tags or [],
            heat_score=1.0,
        )

        self.db.add(fact)
        await self.db.flush()

        # Generate and store embedding (only if pgvector is available)
        if await check_pgvector_available(self.db):
            embedding = embedding_service.embed(content)
            if embedding:
                vector_str = embedding_service.to_pgvector_str(embedding)
                await self.db.execute(
                    text(
                        """
                        UPDATE memory_facts
                        SET embedding_vector = :vector::vector
                        WHERE id = :fact_id
                        """
                    ).bindparams(vector=vector_str, fact_id=str(fact.id))
                )

        logger.info(f"Added fact: {content[:50]}... (type={fact_type}, confidence={confidence})")
        return fact

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        fact_types: list[str] | None = None,
        categories: list[str] | None = None,
        include_invalid: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search facts by semantic similarity.

        Args:
            query: Search query
            limit: Maximum results
            min_confidence: Minimum confidence threshold
            fact_types: Filter by fact types
            categories: Filter by categories
            include_invalid: Include expired facts

        Returns:
            List of facts with similarity scores
        """
        # Check if pgvector is available
        if not await check_pgvector_available(self.db):
            # Fallback to text search when pgvector is not available
            return await self._text_search(query, limit)

        embedding = embedding_service.embed(query)
        if not embedding:
            # Fallback to text search
            return await self._text_search(query, limit)

        vector_str = embedding_service.to_pgvector_str(embedding)

        # Validate and sanitize inputs
        limit = max(1, min(100, int(limit)))
        min_confidence = max(0.0, min(1.0, float(min_confidence)))

        # Validate fact_types against whitelist
        valid_fact_types = None
        if fact_types:
            valid_fact_types = [t for t in fact_types if t in self.ALLOWED_FACT_TYPES]

        # Validate categories against whitelist
        valid_categories = None
        if categories:
            valid_categories = [c for c in categories if c in self.ALLOWED_CATEGORIES]

        # Build parameterized query
        params = {
            "session_id": self.session_id,
            "min_confidence": min_confidence,
            "vector": vector_str,
            "limit": limit,
        }

        # Build WHERE clause with proper parameterization
        where_parts = [
            "session_id = :session_id",
            "confidence >= :min_confidence",
            "embedding_vector IS NOT NULL",
        ]

        if not include_invalid:
            where_parts.append("(valid_to IS NULL OR valid_to > NOW())")

        if valid_fact_types:
            # Use ANY() with array parameter for safe IN clause
            where_parts.append("fact_type = ANY(:fact_types)")
            params["fact_types"] = valid_fact_types

        if valid_categories:
            # Use ANY() with array parameter for safe IN clause
            where_parts.append("category = ANY(:categories)")
            params["categories"] = valid_categories

        where_clause = " AND ".join(where_parts)

        # Vector similarity search with parameterized query
        result = await self.db.execute(
            text(
                f"""
                SELECT
                    id,
                    content,
                    fact_type,
                    category,
                    confidence,
                    heat_score,
                    valid_from,
                    valid_to,
                    1 - (embedding_vector <=> :vector::vector) as score
                FROM memory_facts
                WHERE {where_clause}
                ORDER BY embedding_vector <=> :vector::vector
                LIMIT :limit
                """
            ).bindparams(**params)
        )

        rows = result.fetchall()
        facts = []
        fact_ids = []
        for row in rows:
            fact_id = str(row[0])
            facts.append({
                "id": fact_id,
                "content": row[1],
                "fact_type": row[2],
                "category": row[3],
                "confidence": row[4],
                "heat_score": row[5],
                "valid_from": row[6].isoformat() if row[6] else None,
                "valid_to": row[7].isoformat() if row[7] else None,
                "score": float(row[8]) if row[8] else 0.0,
            })
            fact_ids.append(fact_id)

        # Batch update heat scores for all accessed facts
        if fact_ids:
            await self.db.execute(
                text(
                    """
                    UPDATE memory_facts
                    SET access_count = access_count + 1,
                        last_accessed = NOW(),
                        heat_score = LEAST(2.0, heat_score + 0.1)
                    WHERE id = ANY(:fact_ids)
                    """
                ).bindparams(fact_ids=fact_ids)
            )

        return facts

    async def _text_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fallback text search when embeddings unavailable."""
        # Sanitize query for LIKE pattern - escape special characters
        sanitized_query = (
            query.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        limit = max(1, min(100, int(limit)))

        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.content.ilike(f"%{sanitized_query}%"),
                    or_(
                        MemoryFact.valid_to.is_(None),
                        MemoryFact.valid_to > datetime.now(UTC).replace(tzinfo=None),
                    ),
                )
            )
            .order_by(MemoryFact.heat_score.desc())
            .limit(limit)
        )

        facts = []
        for fact in result.scalars().all():
            facts.append({
                "id": str(fact.id),
                "content": fact.content,
                "fact_type": fact.fact_type,
                "category": fact.category,
                "confidence": fact.confidence,
                "heat_score": fact.heat_score,
                "score": 0.5,  # Default score for text search
            })

        return facts

    async def _find_similar(
        self, content: str, threshold: float = 0.85
    ) -> list[dict[str, Any]]:
        """Find similar existing facts."""
        results = await self.search(content, limit=3)
        return [r for r in results if r.get("score", 0) >= threshold]

    async def _reinforce(self, fact_id: UUID, new_confidence: float) -> None:
        """Reinforce existing fact."""
        result = await self.db.execute(
            select(MemoryFact).where(MemoryFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if fact:
            # Use unified confidence calculation with weighted average
            weighted_confidence = calculate_weighted_average(
                fact.confidence, new_confidence, old_weight=0.6
            )
            # Then apply reinforcement for the merge
            fact.confidence = calculate_reinforcement(weighted_confidence, reinforcement_strength=0.15)
            fact.heat_score = min(2.0, fact.heat_score + 0.2)
            fact.access_count += 1
            fact.last_accessed = datetime.now(UTC).replace(tzinfo=None)

    async def _record_access(self, fact_id: UUID) -> None:
        """Record fact access for heat scoring."""
        await self.db.execute(
            text(
                """
                UPDATE memory_facts
                SET access_count = access_count + 1,
                    last_accessed = NOW(),
                    heat_score = LEAST(2.0, heat_score + 0.1)
                WHERE id = :fact_id
                """
            ).bindparams(fact_id=str(fact_id))
        )

    async def get_by_type(
        self,
        fact_type: str,
        limit: int = 20,
        min_confidence: float = 0.5,
    ) -> list[MemoryFact]:
        """Get facts by type."""
        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.fact_type == fact_type,
                    MemoryFact.confidence >= min_confidence,
                    or_(
                        MemoryFact.valid_to.is_(None),
                        MemoryFact.valid_to > datetime.now(UTC).replace(tzinfo=None),
                    ),
                )
            )
            .order_by(MemoryFact.confidence.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_persona_attributes(self) -> list[MemoryFact]:
        """Get O-Mem persona attributes (Pa)."""
        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.is_persona_attribute == True,  # noqa: E712
                    or_(
                        MemoryFact.valid_to.is_(None),
                        MemoryFact.valid_to > datetime.now(UTC).replace(tzinfo=None),
                    ),
                )
            )
            .order_by(MemoryFact.confidence.desc())
        )
        return list(result.scalars().all())

    async def get_persona_events(self, limit: int = 10) -> list[MemoryFact]:
        """Get O-Mem persona events (Pf)."""
        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.is_persona_event == True,  # noqa: E712
                )
            )
            .order_by(MemoryFact.event_time.desc().nullsfirst())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(
        self,
        fact_id: UUID,
        new_content: str | None = None,
        new_confidence: float | None = None,
    ) -> MemoryFact | None:
        """Update a fact."""
        result = await self.db.execute(
            select(MemoryFact).where(MemoryFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if not fact:
            return None

        if new_content:
            fact.content = new_content
            # Update embedding
            embedding = embedding_service.embed(new_content)
            if embedding:
                vector_str = embedding_service.to_pgvector_str(embedding)
                await self.db.execute(
                    text(
                        """
                        UPDATE memory_facts
                        SET embedding_vector = :vector::vector
                        WHERE id = :fact_id
                        """
                    ).bindparams(vector=vector_str, fact_id=str(fact_id))
                )

        if new_confidence is not None:
            fact.confidence = new_confidence

        fact.updated_at = datetime.now(UTC).replace(tzinfo=None)
        return fact

    async def invalidate(self, fact_id: UUID) -> bool:
        """
        Invalidate a fact (soft delete).
        Sets valid_to to now instead of deleting.
        """
        result = await self.db.execute(
            select(MemoryFact).where(MemoryFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if not fact:
            return False

        fact.valid_to = datetime.now(UTC).replace(tzinfo=None)
        logger.info(f"Invalidated fact: {fact.content[:50]}...")
        return True

    async def get_unlinked(self, limit: int = 20) -> list[MemoryFact]:
        """Get facts without A-MEM links."""
        # Get facts that aren't sources in any link
        linked_ids_query = select(MemoryLink.source_id).where(
            MemoryLink.source_type == "fact"
        )
        result = await self.db.execute(
            select(MemoryFact)
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.id.notin_(linked_ids_query),
                )
            )
            .order_by(MemoryFact.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_link(
        self,
        source_id: UUID,
        target_id: UUID,
        link_type: str = "related",
        strength: float = 1.0,
        reason: str | None = None,
    ) -> MemoryLink:
        """Create A-MEM link between facts."""
        link = MemoryLink(
            id=uuid4(),
            source_type="fact",
            source_id=source_id,
            target_type="fact",
            target_id=target_id,
            link_type=link_type,
            strength=strength,
            reason=reason,
        )
        self.db.add(link)
        return link

    async def count_by_category(self, category: str) -> int:
        """Count facts in a category."""
        result = await self.db.execute(
            select(func.count(MemoryFact.id))
            .where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.category == category,
                    or_(
                        MemoryFact.valid_to.is_(None),
                        MemoryFact.valid_to > datetime.now(UTC).replace(tzinfo=None),
                    ),
                )
            )
        )
        return result.scalar() or 0

    async def apply_decay(self, decay_factor: float = 0.95) -> int:
        """
        Apply decay to heat scores (MemOS).
        Returns number of facts decayed.
        """
        result = await self.db.execute(
            text(
                """
                UPDATE memory_facts
                SET heat_score = heat_score * :decay
                WHERE session_id = :session_id
                    AND heat_score > 0.1
                RETURNING id
                """
            ).bindparams(decay=decay_factor, session_id=self.session_id)
        )
        rows = result.fetchall()
        return len(rows)

    async def extract_from_recent_chats(self) -> list[MemoryFact]:
        """
        Extract facts from recent chat messages.
        Uses Claude to identify factual statements.
        """
        from src.core.claude import claude_client
        from src.db.models import ChatMessage

        # Get recent messages
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == self.session_id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(20)
        )
        messages = result.scalars().all()

        if not messages:
            return []

        # Build conversation text with sanitization to prevent prompt injection
        conversation = "\n".join(
            f"{m.role}: {sanitize_user_input(m.content, max_length=500)}"
            for m in reversed(messages)
        )

        # Ask Claude to extract facts
        prompt = f"""Extract factual information about the user from this conversation.
Focus on: preferences, habits, goals, demographics, skills, opinions.

Conversation:
{conversation}

Return a JSON array of facts. Each fact should have:
- content: the fact (1 sentence)
- fact_type: preference/habit/goal/demographic/skill/opinion
- category: work/personal/health/finance/learning/other
- confidence: 0-1 (how certain)

Return only valid JSON array. Return [] if no facts found.
Example: [{{"content": "User prefers dark mode", "fact_type": "preference", "category": "work", "confidence": 0.9}}]
"""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system="Extract facts. Return valid JSON array only.",
            )

            import json
            facts_data = json.loads(response)

            created_facts = []
            for fact_data in facts_data:
                if not fact_data.get("content"):
                    continue

                fact = await self.add(
                    content=fact_data["content"],
                    fact_type=fact_data.get("fact_type", "fact"),
                    category=fact_data.get("category"),
                    confidence=fact_data.get("confidence", 0.7),
                    source="chat",
                )
                created_facts.append(fact)

            return created_facts

        except Exception as e:
            logger.error(f"Error extracting facts from chat: {e}")
            return []
