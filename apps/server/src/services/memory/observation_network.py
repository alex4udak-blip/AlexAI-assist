"""
Observation Network - Entity summaries and Knowledge Graph.
Implements Hindsight's Observation Network with Zep-style temporal KG.
"""

import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.memory import MemoryEntity, MemoryRelationship
from .embeddings import embedding_service

logger = logging.getLogger(__name__)


class ObservationNetwork:
    """
    Manages entities and their relationships (Knowledge Graph).
    Features:
    - Entity extraction and profiling
    - Temporal relationships (Zep bi-temporal)
    - LLM-generated summaries
    - Relationship strength tracking
    """

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        self.session_id = session_id

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        summary: str | None = None,
        attributes: dict[str, Any] | None = None,
        key_facts: list[str] | None = None,
    ) -> MemoryEntity:
        """
        Add or update an entity.

        Args:
            name: Entity name
            entity_type: Type (person, app, project, concept, location, org)
            summary: LLM-generated summary
            attributes: Structured attributes
            key_facts: Key facts about entity

        Returns:
            Created/updated MemoryEntity
        """
        canonical = self._canonicalize(name)

        # Check if entity exists
        result = await self.db.execute(
            select(MemoryEntity).where(
                and_(
                    MemoryEntity.session_id == self.session_id,
                    MemoryEntity.canonical_name == canonical,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.mention_count += 1
            existing.last_seen = datetime.utcnow()
            if summary:
                existing.summary = summary
            if attributes:
                existing.attributes = {**(existing.attributes or {}), **attributes}
            if key_facts:
                existing.key_facts = list(set((existing.key_facts or []) + key_facts))
            return existing

        # Create new
        entity = MemoryEntity(
            id=uuid4(),
            session_id=self.session_id,
            name=name,
            canonical_name=canonical,
            entity_type=entity_type,
            summary=summary,
            attributes=attributes or {},
            key_facts=key_facts or [],
            mention_count=1,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        self.db.add(entity)
        await self.db.flush()

        # Generate and store embedding
        embed_text = f"{name} - {entity_type}. {summary or ''}"
        embedding = embedding_service.embed(embed_text)
        if embedding:
            vector_str = embedding_service.to_pgvector_str(embedding)
            await self.db.execute(
                text(
                    f"""
                    UPDATE memory_entities
                    SET embedding_vector = '{vector_str}'::vector
                    WHERE id = :entity_id
                    """
                ).bindparams(entity_id=str(entity.id))
            )

        logger.info(f"Added entity: {name} (type={entity_type})")
        return entity

    def _canonicalize(self, name: str) -> str:
        """Canonicalize entity name for deduplication."""
        # Lowercase, remove extra spaces
        canonical = name.lower().strip()
        canonical = re.sub(r"\s+", " ", canonical)
        return canonical

    async def get_entity(self, name: str) -> MemoryEntity | None:
        """Get entity by name."""
        canonical = self._canonicalize(name)
        result = await self.db.execute(
            select(MemoryEntity).where(
                and_(
                    MemoryEntity.session_id == self.session_id,
                    MemoryEntity.canonical_name == canonical,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_entity_by_id(self, entity_id: UUID) -> MemoryEntity | None:
        """Get entity by ID."""
        result = await self.db.execute(
            select(MemoryEntity).where(MemoryEntity.id == entity_id)
        )
        return result.scalar_one_or_none()

    # Allowed entity types for validation
    ALLOWED_ENTITY_TYPES = frozenset({
        "person", "app", "project", "concept", "location",
        "org", "tool", "website", "file", "event",
    })

    async def search_entities(
        self,
        query: str,
        limit: int = 10,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search entities by semantic similarity.

        Args:
            query: Search query
            limit: Maximum results
            entity_types: Filter by types

        Returns:
            List of entities with scores
        """
        embedding = embedding_service.embed(query)
        if not embedding:
            return await self._text_search_entities(query, limit, entity_types)

        vector_str = embedding_service.to_pgvector_str(embedding)

        # Validate and sanitize inputs
        limit = max(1, min(100, int(limit)))

        # Build parameterized query
        params = {
            "session_id": self.session_id,
            "limit": limit,
            "vector": vector_str,
        }

        # Build WHERE clause
        where_parts = [
            "session_id = :session_id",
            "embedding_vector IS NOT NULL",
        ]

        # Validate entity_types against whitelist
        if entity_types:
            valid_types = [t for t in entity_types if t in self.ALLOWED_ENTITY_TYPES]
            if valid_types:
                where_parts.append("entity_type = ANY(:entity_types)")
                params["entity_types"] = valid_types

        where_clause = " AND ".join(where_parts)

        result = await self.db.execute(
            text(
                f"""
                SELECT
                    id,
                    name,
                    entity_type,
                    summary,
                    key_facts,
                    mention_count,
                    1 - (embedding_vector <=> :vector::vector) as score
                FROM memory_entities
                WHERE {where_clause}
                ORDER BY embedding_vector <=> :vector::vector
                LIMIT :limit
                """
            ).bindparams(**params)
        )

        entities = []
        for row in result.fetchall():
            entities.append({
                "id": str(row[0]),
                "name": row[1],
                "entity_type": row[2],
                "summary": row[3],
                "key_facts": row[4] or [],
                "mention_count": row[5],
                "score": float(row[6]) if row[6] else 0.0,
            })

        return entities

    async def _text_search_entities(
        self,
        query: str,
        limit: int = 10,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fallback text search for entities."""
        # Sanitize query for LIKE pattern - escape special characters
        sanitized_query = (
            query.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        limit = max(1, min(100, int(limit)))

        filters = [
            MemoryEntity.session_id == self.session_id,
            or_(
                MemoryEntity.name.ilike(f"%{sanitized_query}%"),
                MemoryEntity.summary.ilike(f"%{sanitized_query}%"),
            ),
        ]

        # Validate entity_types against whitelist
        if entity_types:
            valid_types = [t for t in entity_types if t in self.ALLOWED_ENTITY_TYPES]
            if valid_types:
                filters.append(MemoryEntity.entity_type.in_(valid_types))

        result = await self.db.execute(
            select(MemoryEntity)
            .where(and_(*filters))
            .order_by(MemoryEntity.mention_count.desc())
            .limit(limit)
        )

        entities = []
        for entity in result.scalars().all():
            entities.append({
                "id": str(entity.id),
                "name": entity.name,
                "entity_type": entity.entity_type,
                "summary": entity.summary,
                "key_facts": entity.key_facts or [],
                "mention_count": entity.mention_count,
                "score": 0.5,
            })

        return entities

    async def add_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
        description: str | None = None,
        strength: float = 1.0,
        confidence: float = 1.0,
        event_time: datetime | None = None,
    ) -> MemoryRelationship:
        """
        Add relationship between entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Type (uses, prefers, works_on, knows, etc.)
            description: Relationship description
            strength: Relationship strength (0-1)
            confidence: Confidence score
            event_time: When relationship started

        Returns:
            Created MemoryRelationship
        """
        # Check if relationship exists
        result = await self.db.execute(
            select(MemoryRelationship).where(
                and_(
                    MemoryRelationship.source_id == source_id,
                    MemoryRelationship.target_id == target_id,
                    MemoryRelationship.relation_type == relation_type,
                    or_(
                        MemoryRelationship.valid_to.is_(None),
                        MemoryRelationship.valid_to > datetime.utcnow(),
                    ),
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Reinforce existing relationship
            existing.strength = min(1.0, existing.strength + 0.1)
            existing.confidence = (existing.confidence + confidence) / 2
            existing.updated_at = datetime.utcnow()
            return existing

        relationship = MemoryRelationship(
            id=uuid4(),
            session_id=self.session_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            description=description,
            strength=strength,
            confidence=confidence,
            event_time=event_time,
            valid_from=datetime.utcnow(),
        )
        self.db.add(relationship)

        logger.info(f"Added relationship: {source_id} --{relation_type}--> {target_id}")
        return relationship

    async def get_entity_relationships(
        self,
        entity_id: UUID,
        include_incoming: bool = True,
        include_outgoing: bool = True,
    ) -> list[dict[str, Any]]:
        """Get all relationships for an entity."""
        relationships = []

        if include_outgoing:
            result = await self.db.execute(
                select(MemoryRelationship, MemoryEntity)
                .join(MemoryEntity, MemoryRelationship.target_id == MemoryEntity.id)
                .where(
                    and_(
                        MemoryRelationship.source_id == entity_id,
                        or_(
                            MemoryRelationship.valid_to.is_(None),
                            MemoryRelationship.valid_to > datetime.utcnow(),
                        ),
                    )
                )
            )
            for rel, target in result.fetchall():
                relationships.append({
                    "id": str(rel.id),
                    "direction": "outgoing",
                    "relation_type": rel.relation_type,
                    "target_name": target.name,
                    "target_type": target.entity_type,
                    "target_id": str(target.id),
                    "strength": rel.strength,
                    "confidence": rel.confidence,
                })

        if include_incoming:
            result = await self.db.execute(
                select(MemoryRelationship, MemoryEntity)
                .join(MemoryEntity, MemoryRelationship.source_id == MemoryEntity.id)
                .where(
                    and_(
                        MemoryRelationship.target_id == entity_id,
                        or_(
                            MemoryRelationship.valid_to.is_(None),
                            MemoryRelationship.valid_to > datetime.utcnow(),
                        ),
                    )
                )
            )
            for rel, source in result.fetchall():
                relationships.append({
                    "id": str(rel.id),
                    "direction": "incoming",
                    "relation_type": rel.relation_type,
                    "source_name": source.name,
                    "source_type": source.entity_type,
                    "source_id": str(source.id),
                    "strength": rel.strength,
                    "confidence": rel.confidence,
                })

        return relationships

    async def extract_entities(self, text: str) -> list[str]:
        """
        Extract entity names from text.
        Uses simple heuristics and known entities.
        """
        entities = []

        # Check for known entities
        result = await self.db.execute(
            select(MemoryEntity.name)
            .where(MemoryEntity.session_id == self.session_id)
        )
        known_names = [row[0].lower() for row in result.fetchall()]

        text_lower = text.lower()
        for name in known_names:
            if name in text_lower:
                entities.append(name)

        # Extract capitalized words (potential entities)
        words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        entities.extend([w.lower() for w in words if len(w) > 2])

        return list(set(entities))

    async def extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        # Remove common words and extract significant terms
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "through",
            "during", "before", "after", "above", "below", "between", "under",
            "again", "further", "then", "once", "here", "there", "when",
            "where", "why", "how", "all", "each", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "just", "and", "but",
            "if", "or", "because", "until", "while", "this", "that",
            "these", "those", "what", "which", "who", "whom", "it", "i",
            "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
        }

        words = re.findall(r"\b[a-z]+\b", text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 3]

        # Get top keywords by frequency
        from collections import Counter
        counts = Counter(keywords)
        return [word for word, _ in counts.most_common(10)]

    async def get_entity_context(
        self,
        entity_names: list[str],
    ) -> list[dict[str, Any]]:
        """Get context for multiple entities."""
        context = []

        for name in entity_names[:5]:  # Limit to 5 entities
            entity = await self.get_entity(name)
            if entity:
                relationships = await self.get_entity_relationships(entity.id)
                context.append({
                    "name": entity.name,
                    "type": entity.entity_type,
                    "summary": entity.summary,
                    "key_facts": entity.key_facts or [],
                    "relationships": relationships[:5],
                })

        return context

    async def update_entity_summaries(self) -> int:
        """
        Update LLM-generated summaries for entities.
        Returns number of entities updated.
        """
        from src.core.claude import claude_client

        # Get entities without summaries or old summaries
        result = await self.db.execute(
            select(MemoryEntity)
            .where(
                and_(
                    MemoryEntity.session_id == self.session_id,
                    or_(
                        MemoryEntity.summary.is_(None),
                        MemoryEntity.last_updated.is_(None),
                    ),
                )
            )
            .order_by(MemoryEntity.mention_count.desc())
            .limit(10)
        )
        entities = result.scalars().all()

        updated = 0
        for entity in entities:
            try:
                # Get relationships for context
                relationships = await self.get_entity_relationships(entity.id)
                rel_text = ", ".join(
                    f"{r['relation_type']} {r.get('target_name', r.get('source_name', ''))}"
                    for r in relationships[:5]
                )

                prompt = f"""Create a brief summary (1-2 sentences) for this entity:
Name: {entity.name}
Type: {entity.entity_type}
Key facts: {', '.join(entity.key_facts or [])}
Relationships: {rel_text}
Mention count: {entity.mention_count}

Return ONLY the summary, no prefix."""

                summary = await claude_client.complete(
                    prompt=prompt,
                    system="Generate concise entity summaries.",
                )

                entity.summary = summary.strip()
                entity.last_updated = datetime.utcnow()
                updated += 1

            except Exception as e:
                logger.error(f"Error updating entity summary: {e}")

        return updated

    async def get_top_entities(
        self,
        limit: int = 10,
        entity_type: str | None = None,
    ) -> list[MemoryEntity]:
        """Get most mentioned entities."""
        filters = [MemoryEntity.session_id == self.session_id]

        if entity_type:
            filters.append(MemoryEntity.entity_type == entity_type)

        result = await self.db.execute(
            select(MemoryEntity)
            .where(and_(*filters))
            .order_by(MemoryEntity.mention_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
