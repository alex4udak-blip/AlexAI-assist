"""Memory system models - Ultimate Memory Architecture 2026."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


# ===========================================
# NETWORK 1: FACT NETWORK
# ===========================================


class MemoryFact(Base):
    """Objective facts about the user (Hindsight Fact Network)."""

    __tablename__ = "memory_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False)  # preference, habit, goal, demographic, skill
    category: Mapped[str | None] = mapped_column(String(100))  # work, personal, health, finance, learning

    # O-Mem persona attributes
    is_persona_attribute: Mapped[bool] = mapped_column(Boolean, default=False)
    is_persona_event: Mapped[bool] = mapped_column(Boolean, default=False)

    # A-MEM Zettelkasten
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")
    context: Mapped[str | None] = mapped_column(Text)

    # Hindsight temporal
    valid_from: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    valid_to: Mapped[datetime | None] = mapped_column(nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(nullable=True)
    record_time: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Confidence & source
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # MemOS scheduling
    heat_score: Mapped[float] = mapped_column(Float, default=1.0)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(nullable=True)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.01)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_facts_session_type", "session_id", "fact_type"),
        Index("idx_facts_valid", "valid_from", "valid_to"),
        Index("idx_facts_heat", "heat_score"),
    )


# ===========================================
# NETWORK 2: EXPERIENCE NETWORK
# ===========================================


class MemoryExperience(Base):
    """What happened - agent runs, user actions, conversations (Hindsight Experience Network)."""

    __tablename__ = "memory_experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Content
    experience_type: Mapped[str | None] = mapped_column(String(50))  # agent_run, user_action, conversation
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # What happened
    action_taken: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(50))  # success, failure, partial
    outcome_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, server_default="'{}'")

    # Learning
    lesson_learned: Mapped[str | None] = mapped_column(Text)
    should_repeat: Mapped[bool | None] = mapped_column(Boolean)

    # Temporal
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # References
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    related_facts: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    related_entities: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # Procedural
    is_procedural: Mapped[bool] = mapped_column(Boolean, default=False)
    procedure_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ===========================================
# NETWORK 3: OBSERVATION NETWORK
# ===========================================


class MemoryEntity(Base):
    """Entities - apps, people, projects, concepts (Hindsight Observation Network)."""

    __tablename__ = "memory_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str | None] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # person, app, project, concept

    # Synthesized profile
    summary: Mapped[str | None] = mapped_column(Text)
    key_facts: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, server_default="'{}'")

    # Usage statistics
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Temporal
    first_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_updated: Mapped[datetime | None] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    outgoing_relationships: Mapped[list["MemoryRelationship"]] = relationship(
        "MemoryRelationship",
        foreign_keys="MemoryRelationship.source_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["MemoryRelationship"]] = relationship(
        "MemoryRelationship",
        foreign_keys="MemoryRelationship.target_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_entities_type", "entity_type"),
        Index("idx_entities_name", "canonical_name"),
    )


class MemoryRelationship(Base):
    """Relationships between entities (Temporal KG - Zep style)."""

    __tablename__ = "memory_relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Nodes
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memory_entities.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memory_entities.id", ondelete="CASCADE"), nullable=False
    )

    # Relationship
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Bi-temporal (Zep)
    valid_from: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    valid_to: Mapped[datetime | None] = mapped_column(nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(nullable=True)

    # Strength
    strength: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Evidence
    evidence: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Back-references
    source_entity: Mapped["MemoryEntity"] = relationship(
        "MemoryEntity", foreign_keys=[source_id], back_populates="outgoing_relationships"
    )
    target_entity: Mapped["MemoryEntity"] = relationship(
        "MemoryEntity", foreign_keys=[target_id], back_populates="incoming_relationships"
    )

    __table_args__ = (
        Index("idx_relationships_source", "source_id"),
        Index("idx_relationships_target", "target_id"),
        Index("idx_relationships_valid", "valid_from", "valid_to"),
    )


# ===========================================
# NETWORK 4: BELIEF NETWORK
# ===========================================


class MemoryBelief(Base):
    """Evolving opinions and inferences (Hindsight Belief Network)."""

    __tablename__ = "memory_beliefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Content
    belief: Mapped[str] = mapped_column(Text, nullable=False)
    belief_type: Mapped[str | None] = mapped_column(String(50))  # preference, opinion, inference, prediction

    # Confidence evolution
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    confidence_history: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, server_default="[]")

    # Evidence
    supporting_facts: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    contradicting_facts: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # Evolution
    formed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_reinforced: Mapped[datetime | None] = mapped_column(nullable=True)
    last_challenged: Mapped[datetime | None] = mapped_column(nullable=True)
    times_reinforced: Mapped[int] = mapped_column(Integer, default=0)
    times_challenged: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_beliefs_confidence", "confidence"),
        Index("idx_beliefs_status", "status"),
    )


# ===========================================
# O-MEM WORKING MEMORY
# ===========================================


class MemoryTopic(Base):
    """Topic-based working memory (O-Mem)."""

    __tablename__ = "memory_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Topic
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Messages
    message_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Temporal
    first_discussed: Mapped[datetime | None] = mapped_column(nullable=True)
    last_discussed: Mapped[datetime | None] = mapped_column(nullable=True)

    # Summary
    summary: Mapped[str | None] = mapped_column(Text)
    key_points: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


class MemoryKeywordIndex(Base):
    """Keyword-based episodic index (O-Mem)."""

    __tablename__ = "memory_keyword_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    message_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    fact_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ===========================================
# MemOS MEMCUBE
# ===========================================


class MemoryCube(Base):
    """Unified memory unit (MemOS)."""

    __tablename__ = "memory_cubes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Reference
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # MemOS metadata
    version: Mapped[int] = mapped_column(Integer, default=1)
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, server_default="'{}'")

    # Governance
    access_level: Mapped[str] = mapped_column(String(20), default="private")
    retention_policy: Mapped[str | None] = mapped_column(String(50))
    retention_until: Mapped[datetime | None] = mapped_column(nullable=True)

    # Scheduling
    heat_score: Mapped[float] = mapped_column(Float, default=1.0)
    last_scheduled: Mapped[datetime | None] = mapped_column(nullable=True)
    schedule_count: Mapped[int] = mapped_column(Integer, default=0)

    # Migration
    migrated_from: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    migrated_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


# ===========================================
# A-MEM LINKS
# ===========================================


class MemoryLink(Base):
    """Zettelkasten-style connections (A-MEM)."""

    __tablename__ = "memory_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source and target
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Link properties
    link_type: Mapped[str | None] = mapped_column(String(50))
    strength: Mapped[float] = mapped_column(Float, default=1.0)
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)

    # Reason
    reason: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ===========================================
# MEMORY-R1 OPERATIONS
# ===========================================


class MemoryOperation(Base):
    """Memory operations log (Memory-R1)."""

    __tablename__ = "memory_operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Operation
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    memory_type: Mapped[str | None] = mapped_column(String(50))
    memory_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Context
    trigger: Mapped[str | None] = mapped_column(String(50))
    trigger_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Decision
    reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)

    # Result
    success: Mapped[bool | None] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ===========================================
# EPISODES
# ===========================================


class MemoryEpisode(Base):
    """Episode summaries - daily/weekly (MemGPT style)."""

    __tablename__ = "memory_episodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Period
    episode_type: Mapped[str | None] = mapped_column(String(50))
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)

    # Content
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")
    highlights: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, server_default="[]")

    # Metrics
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, server_default="'{}'")

    # Extracted knowledge
    facts_extracted: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    beliefs_formed: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    entities_mentioned: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # Sources
    source_messages: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")
    source_events: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ===========================================
# PROCEDURAL MEMORY
# ===========================================


class MemoryProcedure(Base):
    """Learned procedures/skills (Mem-alpha style)."""

    __tablename__ = "memory_procedures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    procedure_type: Mapped[str | None] = mapped_column(String(50))

    # The procedure
    trigger_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, server_default="'{}'")
    steps: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, server_default="[]")
    expected_outcome: Mapped[str | None] = mapped_column(Text)

    # Learning stats
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_time_saved: Mapped[float] = mapped_column(Float, default=0)
    avg_success_rate: Mapped[float] = mapped_column(Float, default=0)

    # Evolution
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    improvement_notes: Mapped[str | None] = mapped_column(Text)

    # Agent link
    learned_from_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    experience_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default="'{}'")

    # Timestamps
    last_used: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


# ===========================================
# META-MEMORY
# ===========================================


class MemoryMeta(Base):
    """Self-knowledge about what we know."""

    __tablename__ = "memory_meta"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Domain
    domain: Mapped[str] = mapped_column(String(100), nullable=False)

    # What we know
    knowledge_summary: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.5)

    # Statistics
    facts_count: Mapped[int] = mapped_column(Integer, default=0)
    beliefs_count: Mapped[int] = mapped_column(Integer, default=0)
    experiences_count: Mapped[int] = mapped_column(Integer, default=0)

    # Knowledge gaps
    unknown_areas: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")
    questions_to_explore: Mapped[list[str] | None] = mapped_column(ARRAY(String), server_default="'{}'")

    # Timestamps
    last_updated: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
