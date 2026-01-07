"""
Ultimate Memory System 2026
Based on: Hindsight (4-network) + O-Mem (persona) + MemOS (scheduling) + Memory-R1 (RL ops)

Revision ID: 003
Revises: 002
Create Date: 2026-01-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

# Global flag for pgvector availability (set during migration)
_pgvector_available = False


def try_enable_pgvector() -> bool:
    """
    Try to enable pgvector extension. Returns True if successful.

    Uses SAVEPOINT to avoid breaking the transaction if CREATE EXTENSION fails.
    """
    global _pgvector_available
    conn = op.get_bind()

    try:
        # First check if extension is already installed (safe query)
        result = conn.execute(
            sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        if result.fetchone() is not None:
            logger.info("pgvector extension already installed")
            _pgvector_available = True
            return True
    except Exception as e:
        logger.warning(f"Could not check pg_extension: {e}")

    # Try to create extension using SAVEPOINT to avoid breaking transaction
    try:
        conn.execute(sa.text("SAVEPOINT pgvector_check"))
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(sa.text("RELEASE SAVEPOINT pgvector_check"))
        logger.info("pgvector extension enabled successfully")
        _pgvector_available = True
        return True
    except Exception as e:
        # Rollback to savepoint to restore transaction state
        try:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT pgvector_check"))
        except Exception:
            pass  # Savepoint might not exist

        logger.warning(
            f"pgvector extension not available (this is OK - vector search will be disabled): {e}"
        )
        _pgvector_available = False
        return False


def add_vector_column_if_available(table_name: str, column_name: str = "embedding_vector", dimensions: int = 1536) -> None:
    """Add vector column to table if pgvector is available."""
    if not _pgvector_available:
        logger.info(f"Skipping vector column for {table_name} (pgvector not available)")
        return

    try:
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} vector({dimensions})")
    except Exception as e:
        logger.warning(f"Could not add vector column to {table_name}: {e}")


def create_vector_index_if_available(index_name: str, table_name: str, column_name: str = "embedding_vector") -> None:
    """Create vector index if pgvector is available."""
    if not _pgvector_available:
        logger.info(f"Skipping vector index {index_name} (pgvector not available)")
        return

    try:
        op.execute(
            f"""
            CREATE INDEX {index_name}
            ON {table_name} USING ivfflat ({column_name} vector_cosine_ops)
            WITH (lists = 50)
            """
        )
    except Exception as e:
        logger.warning(f"Could not create vector index {index_name}: {e}")


def table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    try:
        conn = op.get_bind()
        result = conn.execute(
            sa.text(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}'")
        )
        return result.fetchone() is not None
    except Exception:
        return False


def safe_create_table(table_name: str, *columns, **kwargs) -> None:
    """Create table only if it doesn't exist (idempotent)."""
    if table_exists(table_name):
        logger.info(f"Table {table_name} already exists, skipping creation")
        return
    try:
        op.create_table(table_name, *columns, **kwargs)
        logger.info(f"Created table {table_name}")
    except Exception as e:
        # Table might have been created by concurrent process
        if "already exists" in str(e).lower():
            logger.info(f"Table {table_name} already exists (concurrent creation)")
        else:
            raise


def safe_create_index(index_name: str, table_name: str, columns: list[str]) -> None:
    """Create index only if it doesn't exist (idempotent)."""
    try:
        op.create_index(index_name, table_name, columns)
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"Index {index_name} already exists, skipping")
        else:
            logger.warning(f"Could not create index {index_name}: {e}")


def upgrade() -> None:
    # Try to enable pgvector extension (will gracefully fail on Railway/managed PostgreSQL)
    try_enable_pgvector()

    if not _pgvector_available:
        logger.info("Continuing migration without pgvector. Vector search will use text fallback.")

    # ===========================================
    # NETWORK 1: FACT NETWORK (Objective truths)
    # ===========================================
    safe_create_table(
        "memory_facts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Content
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("fact_type", sa.String(50), nullable=False),  # preference, habit, goal, demographic, skill, world_fact
        sa.Column("category", sa.String(100)),  # work, personal, health, finance, learning
        # O-Mem style persona attributes
        sa.Column("is_persona_attribute", sa.Boolean, default=False),  # Pa in O-Mem
        sa.Column("is_persona_event", sa.Boolean, default=False),  # Pf in O-Mem
        # A-MEM Zettelkasten metadata
        sa.Column("keywords", ARRAY(sa.String), server_default=sa.text("'{}'")),
        sa.Column("tags", ARRAY(sa.String), server_default=sa.text("'{}'")),
        sa.Column("context", sa.Text),  # LLM-generated context
        # Hindsight temporal model
        sa.Column("valid_from", sa.DateTime, default=datetime.utcnow),
        sa.Column("valid_to", sa.DateTime, nullable=True),  # null = still valid
        sa.Column("event_time", sa.DateTime),  # when fact occurred in real world
        sa.Column("record_time", sa.DateTime, default=datetime.utcnow),  # when we learned it
        # Hindsight confidence & source
        sa.Column("confidence", sa.Float, default=1.0),  # 0-1
        sa.Column("source", sa.String(50)),  # chat, pattern, agent, manual, inferred
        sa.Column("source_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),  # supporting facts
        # MemOS scheduling metadata
        sa.Column("heat_score", sa.Float, default=1.0),  # for retrieval priority
        sa.Column("access_count", sa.Integer, default=0),
        sa.Column("last_accessed", sa.DateTime),
        sa.Column("decay_rate", sa.Float, default=0.01),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime, onupdate=datetime.utcnow),
    )

    # Add vector column for similarity search (1536-dim for OpenAI text-embedding-3-small) - optional
    add_vector_column_if_available("memory_facts")
    create_vector_index_if_available("idx_facts_embedding", "memory_facts")

    # ===========================================
    # NETWORK 2: EXPERIENCE NETWORK (What happened)
    # ===========================================
    safe_create_table(
        "memory_experiences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Content
        sa.Column("experience_type", sa.String(50)),  # agent_run, user_action, conversation, pattern_detected
        sa.Column("description", sa.Text, nullable=False),
        # What happened
        sa.Column("action_taken", sa.Text),
        sa.Column("outcome", sa.String(50)),  # success, failure, partial, unknown
        sa.Column("outcome_details", JSONB, server_default=sa.text("'{}'")),
        # Learning
        sa.Column("lesson_learned", sa.Text),  # what we learned from this
        sa.Column("should_repeat", sa.Boolean),  # should we do this again?
        # Temporal
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("duration_seconds", sa.Integer),
        # References
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("related_facts", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("related_entities", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        # Procedural learning (Mem-alpha style)
        sa.Column("is_procedural", sa.Boolean, default=False),
        sa.Column("procedure_id", UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # Add vector column - optional
    add_vector_column_if_available("memory_experiences")
    create_vector_index_if_available("idx_experiences_embedding", "memory_experiences")

    # ===========================================
    # NETWORK 3: OBSERVATION NETWORK (Entity summaries + KG)
    # ===========================================

    # Entities (apps, people, projects, concepts)
    safe_create_table(
        "memory_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Identity
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("canonical_name", sa.String(255)),  # normalized name
        sa.Column("entity_type", sa.String(50), nullable=False),  # person, app, project, concept, location, org
        # Synthesized profile (Hindsight observation network)
        sa.Column("summary", sa.Text),  # LLM-generated summary
        sa.Column("key_facts", ARRAY(sa.String), server_default=sa.text("'{}'")),
        sa.Column("attributes", JSONB, server_default=sa.text("'{}'")),
        # Usage statistics
        sa.Column("mention_count", sa.Integer, default=1),
        sa.Column("interaction_count", sa.Integer, default=0),
        sa.Column("total_duration_seconds", sa.Integer, default=0),  # for apps
        # Temporal
        sa.Column("first_seen", sa.DateTime, default=datetime.utcnow),
        sa.Column("last_seen", sa.DateTime, default=datetime.utcnow),
        sa.Column("last_updated", sa.DateTime),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # Add vector column - optional
    add_vector_column_if_available("memory_entities")
    create_vector_index_if_available("idx_entities_embedding", "memory_entities")

    # Relationships (Temporal KG - Zep/Graphiti style)
    safe_create_table(
        "memory_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Nodes
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("memory_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), sa.ForeignKey("memory_entities.id", ondelete="CASCADE"), nullable=False),
        # Relationship
        sa.Column("relation_type", sa.String(100), nullable=False),  # uses, prefers, works_on, knows
        sa.Column("description", sa.Text),
        # Bi-temporal model (Zep)
        sa.Column("valid_from", sa.DateTime, default=datetime.utcnow),
        sa.Column("valid_to", sa.DateTime, nullable=True),
        sa.Column("event_time", sa.DateTime),  # when relationship started in real world
        # Strength
        sa.Column("strength", sa.Float, default=1.0),
        sa.Column("confidence", sa.Float, default=1.0),
        # Evidence
        sa.Column("evidence", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # ===========================================
    # NETWORK 4: BELIEF NETWORK (Evolving opinions)
    # ===========================================
    safe_create_table(
        "memory_beliefs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Content
        sa.Column("belief", sa.Text, nullable=False),  # "User prefers minimal UI"
        sa.Column("belief_type", sa.String(50)),  # preference, opinion, inference, prediction
        # Hindsight confidence evolution
        sa.Column("confidence", sa.Float, default=0.5),  # starts uncertain
        sa.Column("confidence_history", JSONB, server_default=sa.text("'[]'")),  # [{timestamp, value, reason}]
        # Supporting/contradicting evidence
        sa.Column("supporting_facts", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("contradicting_facts", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        # Evolution
        sa.Column("formed_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("last_reinforced", sa.DateTime),
        sa.Column("last_challenged", sa.DateTime),
        sa.Column("times_reinforced", sa.Integer, default=0),
        sa.Column("times_challenged", sa.Integer, default=0),
        # Status
        sa.Column("status", sa.String(20), default="active"),  # active, superseded, rejected
        sa.Column("superseded_by", UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # ===========================================
    # O-MEM WORKING MEMORY (Topic-based)
    # ===========================================
    safe_create_table(
        "memory_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Topic
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        # Messages in this topic
        sa.Column("message_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("message_count", sa.Integer, default=0),
        # Temporal
        sa.Column("first_discussed", sa.DateTime),
        sa.Column("last_discussed", sa.DateTime),
        # Summary
        sa.Column("summary", sa.Text),
        sa.Column("key_points", ARRAY(sa.String), server_default=sa.text("'{}'")),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # O-MEM EPISODIC INDEX (Keyword-based)
    safe_create_table(
        "memory_keyword_index",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("keyword", sa.String(100), nullable=False),
        sa.Column("message_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("fact_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("occurrence_count", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # ===========================================
    # MemOS MEMCUBE (Unified memory unit)
    # ===========================================
    safe_create_table(
        "memory_cubes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Reference to actual memory
        sa.Column("memory_type", sa.String(50), nullable=False),  # fact, experience, entity, belief
        sa.Column("memory_id", UUID(as_uuid=True), nullable=False),
        # MemOS metadata
        sa.Column("version", sa.Integer, default=1),
        sa.Column("provenance", JSONB, server_default=sa.text("'{}'")),  # {source, timestamp, confidence}
        # Governance
        sa.Column("access_level", sa.String(20), default="private"),
        sa.Column("retention_policy", sa.String(50)),  # keep_forever, decay, archive_after
        sa.Column("retention_until", sa.DateTime),
        # Scheduling (MemOS heat scoring)
        sa.Column("heat_score", sa.Float, default=1.0),
        sa.Column("last_scheduled", sa.DateTime),
        sa.Column("schedule_count", sa.Integer, default=0),
        # Migration
        sa.Column("migrated_from", UUID(as_uuid=True), nullable=True),
        sa.Column("migrated_to", UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # ===========================================
    # A-MEM LINKS (Zettelkasten connections)
    # ===========================================
    safe_create_table(
        "memory_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # Source and target
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        # Link properties
        sa.Column("link_type", sa.String(50)),  # related, supports, contradicts, evolved_from, derived_from
        sa.Column("strength", sa.Float, default=1.0),
        sa.Column("bidirectional", sa.Boolean, default=True),
        # Auto-generated by LLM
        sa.Column("reason", sa.Text),  # why linked
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # ===========================================
    # MEMORY-R1 OPERATIONS LOG
    # ===========================================
    safe_create_table(
        "memory_operations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Operation
        sa.Column("operation", sa.String(20), nullable=False),  # ADD, UPDATE, DELETE, NOOP
        sa.Column("memory_type", sa.String(50)),
        sa.Column("memory_id", UUID(as_uuid=True), nullable=True),
        # Context
        sa.Column("trigger", sa.String(50)),  # chat_message, pattern, agent_run, scheduled
        sa.Column("trigger_id", UUID(as_uuid=True), nullable=True),
        # Decision
        sa.Column("reason", sa.Text),  # why this operation
        sa.Column("confidence", sa.Float),
        # Result
        sa.Column("success", sa.Boolean),
        sa.Column("error", sa.Text),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # ===========================================
    # EPISODE SUMMARIES (Daily/Weekly)
    # ===========================================
    safe_create_table(
        "memory_episodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Period
        sa.Column("episode_type", sa.String(50)),  # chat_session, work_block, day, week, month
        sa.Column("period_start", sa.DateTime, nullable=False),
        sa.Column("period_end", sa.DateTime, nullable=False),
        # Content
        sa.Column("title", sa.String(255)),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("key_points", ARRAY(sa.String), server_default=sa.text("'{}'")),
        sa.Column("highlights", JSONB, server_default=sa.text("'[]'")),
        # Metrics
        sa.Column("metrics", JSONB, server_default=sa.text("'{}'")),
        # Extracted knowledge
        sa.Column("facts_extracted", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("beliefs_formed", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("entities_mentioned", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        # Sources
        sa.Column("source_messages", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        sa.Column("source_events", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # Add vector column - optional
    add_vector_column_if_available("memory_episodes")

    # ===========================================
    # PROCEDURAL MEMORY (Learned skills)
    # ===========================================
    safe_create_table(
        "memory_procedures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Identity
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("procedure_type", sa.String(50)),  # automation, workflow, optimization
        # The procedure
        sa.Column("trigger_conditions", JSONB, server_default=sa.text("'{}'")),
        sa.Column("steps", JSONB, server_default=sa.text("'[]'")),
        sa.Column("expected_outcome", sa.Text),
        # Learning from execution (Mem-alpha style)
        sa.Column("success_count", sa.Integer, default=0),
        sa.Column("failure_count", sa.Integer, default=0),
        sa.Column("avg_time_saved", sa.Float, default=0),
        sa.Column("avg_success_rate", sa.Float, default=0),
        # Evolution
        sa.Column("version", sa.Integer, default=1),
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("improvement_notes", sa.Text),
        # Agent link
        sa.Column("learned_from_agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("experience_ids", ARRAY(UUID(as_uuid=True)), server_default=sa.text("'{}'")),
        # Timestamps
        sa.Column("last_used", sa.DateTime),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # ===========================================
    # META-MEMORY (Self-knowledge)
    # ===========================================
    safe_create_table(
        "memory_meta",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Domain
        sa.Column("domain", sa.String(100), nullable=False),
        # What we know
        sa.Column("knowledge_summary", sa.Text),
        sa.Column("confidence_score", sa.Float, default=0.5),
        sa.Column("coverage_score", sa.Float, default=0.5),
        # Statistics
        sa.Column("facts_count", sa.Integer, default=0),
        sa.Column("beliefs_count", sa.Integer, default=0),
        sa.Column("experiences_count", sa.Integer, default=0),
        # Knowledge gaps
        sa.Column("unknown_areas", ARRAY(sa.String), server_default=sa.text("'{}'")),
        sa.Column("questions_to_explore", ARRAY(sa.String), server_default=sa.text("'{}'")),
        # Timestamps
        sa.Column("last_updated", sa.DateTime),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # ===========================================
    # ADDITIONAL INDEXES
    # ===========================================

    # memory_facts indexes
    safe_create_index("idx_facts_session_type", "memory_facts", ["session_id", "fact_type"])
    safe_create_index("idx_facts_valid", "memory_facts", ["valid_from", "valid_to"])
    safe_create_index("idx_facts_heat", "memory_facts", ["heat_score"])
    safe_create_index("idx_facts_source_id", "memory_facts", ["source_id"])
    safe_create_index("idx_facts_last_accessed", "memory_facts", ["last_accessed"])
    safe_create_index("idx_facts_created_at", "memory_facts", ["created_at"])
    safe_create_index("idx_facts_updated_at", "memory_facts", ["updated_at"])

    # memory_experiences indexes
    safe_create_index("idx_experiences_agent_id", "memory_experiences", ["agent_id"])
    safe_create_index("idx_experiences_procedure_id", "memory_experiences", ["procedure_id"])
    safe_create_index("idx_experiences_occurred_at", "memory_experiences", ["occurred_at"])
    safe_create_index("idx_experiences_created_at", "memory_experiences", ["created_at"])
    safe_create_index("idx_experiences_session_type", "memory_experiences", ["session_id", "experience_type"])

    # memory_entities indexes
    safe_create_index("idx_entities_type", "memory_entities", ["entity_type"])
    safe_create_index("idx_entities_name", "memory_entities", ["canonical_name"])
    safe_create_index("idx_entities_last_seen", "memory_entities", ["last_seen"])
    safe_create_index("idx_entities_last_updated", "memory_entities", ["last_updated"])
    safe_create_index("idx_entities_created_at", "memory_entities", ["created_at"])
    safe_create_index("idx_entities_session_type", "memory_entities", ["session_id", "entity_type"])

    # memory_relationships indexes
    safe_create_index("idx_relationships_source", "memory_relationships", ["source_id"])
    safe_create_index("idx_relationships_target", "memory_relationships", ["target_id"])
    safe_create_index("idx_relationships_valid", "memory_relationships", ["valid_from", "valid_to"])
    safe_create_index("idx_relationships_created_at", "memory_relationships", ["created_at"])
    safe_create_index("idx_relationships_updated_at", "memory_relationships", ["updated_at"])
    safe_create_index("idx_relationships_session_type", "memory_relationships", ["session_id", "relation_type"])

    # memory_beliefs indexes
    safe_create_index("idx_beliefs_confidence", "memory_beliefs", ["confidence"])
    safe_create_index("idx_beliefs_status", "memory_beliefs", ["status"])
    safe_create_index("idx_beliefs_superseded_by", "memory_beliefs", ["superseded_by"])
    safe_create_index("idx_beliefs_created_at", "memory_beliefs", ["created_at"])
    safe_create_index("idx_beliefs_updated_at", "memory_beliefs", ["updated_at"])
    safe_create_index("idx_beliefs_session_status", "memory_beliefs", ["session_id", "status"])

    # memory_topics indexes
    safe_create_index("idx_topics_topic", "memory_topics", ["topic"])
    safe_create_index("idx_topics_created_at", "memory_topics", ["created_at"])
    safe_create_index("idx_topics_updated_at", "memory_topics", ["updated_at"])
    safe_create_index("idx_topics_last_discussed", "memory_topics", ["last_discussed"])

    # memory_keyword_index indexes
    safe_create_index("idx_keyword_keyword", "memory_keyword_index", ["keyword"])
    safe_create_index("idx_keyword_created_at", "memory_keyword_index", ["created_at"])
    safe_create_index("idx_keyword_session_keyword", "memory_keyword_index", ["session_id", "keyword"])

    # memory_cubes indexes (critical for lookups)
    safe_create_index("idx_cubes_heat", "memory_cubes", ["heat_score"])
    safe_create_index("idx_cubes_memory_lookup", "memory_cubes", ["memory_type", "memory_id"])
    safe_create_index("idx_cubes_memory_id", "memory_cubes", ["memory_id"])
    safe_create_index("idx_cubes_migrated_from", "memory_cubes", ["migrated_from"])
    safe_create_index("idx_cubes_migrated_to", "memory_cubes", ["migrated_to"])
    safe_create_index("idx_cubes_created_at", "memory_cubes", ["created_at"])
    safe_create_index("idx_cubes_updated_at", "memory_cubes", ["updated_at"])
    safe_create_index("idx_cubes_session_type", "memory_cubes", ["session_id", "memory_type"])

    # memory_links indexes
    safe_create_index("idx_links_source", "memory_links", ["source_type", "source_id"])
    safe_create_index("idx_links_target", "memory_links", ["target_type", "target_id"])
    safe_create_index("idx_links_created_at", "memory_links", ["created_at"])

    # memory_operations indexes
    safe_create_index("idx_operations_memory_id", "memory_operations", ["memory_id"])
    safe_create_index("idx_operations_trigger_id", "memory_operations", ["trigger_id"])
    safe_create_index("idx_operations_created_at", "memory_operations", ["created_at"])
    safe_create_index("idx_operations_session_op", "memory_operations", ["session_id", "operation"])

    # memory_episodes indexes
    safe_create_index("idx_episodes_created_at", "memory_episodes", ["created_at"])
    safe_create_index("idx_episodes_period_start", "memory_episodes", ["period_start"])
    safe_create_index("idx_episodes_period_end", "memory_episodes", ["period_end"])
    safe_create_index("idx_episodes_session_type", "memory_episodes", ["session_id", "episode_type"])

    # memory_procedures indexes
    safe_create_index("idx_procedures_parent_id", "memory_procedures", ["parent_id"])
    safe_create_index("idx_procedures_agent_id", "memory_procedures", ["learned_from_agent_id"])
    safe_create_index("idx_procedures_last_used", "memory_procedures", ["last_used"])
    safe_create_index("idx_procedures_created_at", "memory_procedures", ["created_at"])
    safe_create_index("idx_procedures_updated_at", "memory_procedures", ["updated_at"])
    safe_create_index("idx_procedures_session_type", "memory_procedures", ["session_id", "procedure_type"])

    # memory_meta indexes
    safe_create_index("idx_meta_domain", "memory_meta", ["domain"])
    safe_create_index("idx_meta_last_updated", "memory_meta", ["last_updated"])
    safe_create_index("idx_meta_created_at", "memory_meta", ["created_at"])
    safe_create_index("idx_meta_session_domain", "memory_meta", ["session_id", "domain"])


def downgrade() -> None:
    tables = [
        "memory_meta",
        "memory_procedures",
        "memory_episodes",
        "memory_operations",
        "memory_links",
        "memory_cubes",
        "memory_keyword_index",
        "memory_topics",
        "memory_beliefs",
        "memory_relationships",
        "memory_entities",
        "memory_experiences",
        "memory_facts",
    ]
    for table in tables:
        op.drop_table(table)

    # Drop pgvector extension only if it exists
    try:
        op.execute("DROP EXTENSION IF EXISTS vector")
    except Exception as e:
        logger.warning(f"Could not drop vector extension: {e}")
