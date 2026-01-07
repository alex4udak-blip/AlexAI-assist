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

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ===========================================
    # NETWORK 1: FACT NETWORK (Objective truths)
    # ===========================================
    op.create_table(
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
        sa.Column("keywords", ARRAY(sa.String), server_default="{}"),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
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
        sa.Column("evidence_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),  # supporting facts
        # MemOS scheduling metadata
        sa.Column("heat_score", sa.Float, default=1.0),  # for retrieval priority
        sa.Column("access_count", sa.Integer, default=0),
        sa.Column("last_accessed", sa.DateTime),
        sa.Column("decay_rate", sa.Float, default=0.01),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime, onupdate=datetime.utcnow),
    )

    # Add vector column for similarity search (384-dim for MiniLM)
    op.execute(
        "ALTER TABLE memory_facts ADD COLUMN embedding_vector vector(384)"
    )
    op.execute(
        """
        CREATE INDEX idx_facts_embedding
        ON memory_facts USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # ===========================================
    # NETWORK 2: EXPERIENCE NETWORK (What happened)
    # ===========================================
    op.create_table(
        "memory_experiences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Content
        sa.Column("experience_type", sa.String(50)),  # agent_run, user_action, conversation, pattern_detected
        sa.Column("description", sa.Text, nullable=False),
        # What happened
        sa.Column("action_taken", sa.Text),
        sa.Column("outcome", sa.String(50)),  # success, failure, partial, unknown
        sa.Column("outcome_details", JSONB, server_default="{}"),
        # Learning
        sa.Column("lesson_learned", sa.Text),  # what we learned from this
        sa.Column("should_repeat", sa.Boolean),  # should we do this again?
        # Temporal
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("duration_seconds", sa.Integer),
        # References
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("related_facts", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("related_entities", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        # Procedural learning (Mem-alpha style)
        sa.Column("is_procedural", sa.Boolean, default=False),
        sa.Column("procedure_id", UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # Add vector column
    op.execute(
        "ALTER TABLE memory_experiences ADD COLUMN embedding_vector vector(384)"
    )
    op.execute(
        """
        CREATE INDEX idx_experiences_embedding
        ON memory_experiences USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # ===========================================
    # NETWORK 3: OBSERVATION NETWORK (Entity summaries + KG)
    # ===========================================

    # Entities (apps, people, projects, concepts)
    op.create_table(
        "memory_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Identity
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("canonical_name", sa.String(255)),  # normalized name
        sa.Column("entity_type", sa.String(50), nullable=False),  # person, app, project, concept, location, org
        # Synthesized profile (Hindsight observation network)
        sa.Column("summary", sa.Text),  # LLM-generated summary
        sa.Column("key_facts", ARRAY(sa.String), server_default="{}"),
        sa.Column("attributes", JSONB, server_default="{}"),
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

    # Add vector column
    op.execute(
        "ALTER TABLE memory_entities ADD COLUMN embedding_vector vector(384)"
    )
    op.execute(
        """
        CREATE INDEX idx_entities_embedding
        ON memory_entities USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # Relationships (Temporal KG - Zep/Graphiti style)
    op.create_table(
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
        sa.Column("evidence", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # ===========================================
    # NETWORK 4: BELIEF NETWORK (Evolving opinions)
    # ===========================================
    op.create_table(
        "memory_beliefs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Content
        sa.Column("belief", sa.Text, nullable=False),  # "User prefers minimal UI"
        sa.Column("belief_type", sa.String(50)),  # preference, opinion, inference, prediction
        # Hindsight confidence evolution
        sa.Column("confidence", sa.Float, default=0.5),  # starts uncertain
        sa.Column("confidence_history", JSONB, server_default="[]"),  # [{timestamp, value, reason}]
        # Supporting/contradicting evidence
        sa.Column("supporting_facts", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("contradicting_facts", ARRAY(UUID(as_uuid=True)), server_default="{}"),
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
    op.create_table(
        "memory_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Topic
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        # Messages in this topic
        sa.Column("message_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("message_count", sa.Integer, default=0),
        # Temporal
        sa.Column("first_discussed", sa.DateTime),
        sa.Column("last_discussed", sa.DateTime),
        # Summary
        sa.Column("summary", sa.Text),
        sa.Column("key_points", ARRAY(sa.String), server_default="{}"),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # O-MEM EPISODIC INDEX (Keyword-based)
    op.create_table(
        "memory_keyword_index",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("keyword", sa.String(100), nullable=False),
        sa.Column("message_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("fact_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("occurrence_count", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # ===========================================
    # MemOS MEMCUBE (Unified memory unit)
    # ===========================================
    op.create_table(
        "memory_cubes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        # Reference to actual memory
        sa.Column("memory_type", sa.String(50), nullable=False),  # fact, experience, entity, belief
        sa.Column("memory_id", UUID(as_uuid=True), nullable=False),
        # MemOS metadata
        sa.Column("version", sa.Integer, default=1),
        sa.Column("provenance", JSONB, server_default="{}"),  # {source, timestamp, confidence}
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
    op.create_table(
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
    op.create_table(
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
    op.create_table(
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
        sa.Column("key_points", ARRAY(sa.String), server_default="{}"),
        sa.Column("highlights", JSONB, server_default="[]"),
        # Metrics
        sa.Column("metrics", JSONB, server_default="{}"),
        # Extracted knowledge
        sa.Column("facts_extracted", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("beliefs_formed", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("entities_mentioned", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        # Sources
        sa.Column("source_messages", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("source_events", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        # Timestamps
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # Add vector column
    op.execute(
        "ALTER TABLE memory_episodes ADD COLUMN embedding_vector vector(384)"
    )

    # ===========================================
    # PROCEDURAL MEMORY (Learned skills)
    # ===========================================
    op.create_table(
        "memory_procedures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), index=True),
        # Identity
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("procedure_type", sa.String(50)),  # automation, workflow, optimization
        # The procedure
        sa.Column("trigger_conditions", JSONB, server_default="{}"),
        sa.Column("steps", JSONB, server_default="[]"),
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
        sa.Column("experience_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        # Timestamps
        sa.Column("last_used", sa.DateTime),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime),
    )

    # ===========================================
    # META-MEMORY (Self-knowledge)
    # ===========================================
    op.create_table(
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
        sa.Column("unknown_areas", ARRAY(sa.String), server_default="{}"),
        sa.Column("questions_to_explore", ARRAY(sa.String), server_default="{}"),
        # Timestamps
        sa.Column("last_updated", sa.DateTime),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
    )

    # ===========================================
    # ADDITIONAL INDEXES
    # ===========================================
    op.create_index("idx_facts_session_type", "memory_facts", ["session_id", "fact_type"])
    op.create_index("idx_facts_valid", "memory_facts", ["valid_from", "valid_to"])
    op.create_index("idx_facts_heat", "memory_facts", ["heat_score"])

    op.create_index("idx_entities_type", "memory_entities", ["entity_type"])
    op.create_index("idx_entities_name", "memory_entities", ["canonical_name"])

    op.create_index("idx_relationships_source", "memory_relationships", ["source_id"])
    op.create_index("idx_relationships_target", "memory_relationships", ["target_id"])
    op.create_index("idx_relationships_valid", "memory_relationships", ["valid_from", "valid_to"])

    op.create_index("idx_beliefs_confidence", "memory_beliefs", ["confidence"])
    op.create_index("idx_beliefs_status", "memory_beliefs", ["status"])

    op.create_index("idx_cubes_heat", "memory_cubes", ["heat_score"])
    op.create_index("idx_links_source", "memory_links", ["source_type", "source_id"])
    op.create_index("idx_links_target", "memory_links", ["target_type", "target_id"])

    op.create_index("idx_keyword_keyword", "memory_keyword_index", ["keyword"])
    op.create_index("idx_topics_topic", "memory_topics", ["topic"])


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

    op.execute("DROP EXTENSION IF EXISTS vector")
