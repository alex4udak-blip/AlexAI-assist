"""Tests for Memory System 2026."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.memory.embeddings import EmbeddingService


class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    def test_embedding_service_initialization(self):
        """Test service initialization."""
        service = EmbeddingService()
        assert service.EMBEDDING_DIM == 384

    def test_to_pgvector_str(self):
        """Test vector string conversion for PostgreSQL."""
        service = EmbeddingService()
        embedding = [0.1, 0.2, 0.3]
        result = service.to_pgvector_str(embedding)
        assert result == "[0.1,0.2,0.3]"

    def test_to_pgvector_str_empty(self):
        """Test vector string conversion with empty list."""
        service = EmbeddingService()
        result = service.to_pgvector_str([])
        assert result == "[]"

    def test_similarity_identical_vectors(self):
        """Test similarity of identical vectors returns 1.0."""
        service = EmbeddingService()
        vec = [1.0, 0.0, 0.0]
        similarity = service.similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.01

    def test_similarity_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors returns 0.0."""
        service = EmbeddingService()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = service.similarity(vec1, vec2)
        assert abs(similarity) < 0.01

    def test_similarity_opposite_vectors(self):
        """Test similarity of opposite vectors returns -1.0."""
        service = EmbeddingService()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = service.similarity(vec1, vec2)
        assert abs(similarity + 1.0) < 0.01

    def test_similarity_zero_vector(self):
        """Test similarity with zero vector returns 0.0."""
        service = EmbeddingService()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 0.0, 0.0]
        similarity = service.similarity(vec1, vec2)
        assert similarity == 0.0

    def test_allowed_tables_whitelist(self):
        """Test that ALLOWED_TABLES contains expected tables."""
        service = EmbeddingService()
        assert "memory_facts" in service.ALLOWED_TABLES
        assert "memory_experiences" in service.ALLOWED_TABLES
        assert "memory_entities" in service.ALLOWED_TABLES
        assert "memory_beliefs" in service.ALLOWED_TABLES
        assert "memory_topics" in service.ALLOWED_TABLES


class TestFactNetworkValidation:
    """Test SQL injection prevention in FactNetwork."""

    def test_allowed_fact_types(self):
        """Test fact type whitelist."""
        from src.services.memory.fact_network import FactNetwork

        # Check whitelist contains expected types
        assert "fact" in FactNetwork.ALLOWED_FACT_TYPES
        assert "preference" in FactNetwork.ALLOWED_FACT_TYPES
        assert "habit" in FactNetwork.ALLOWED_FACT_TYPES
        assert "goal" in FactNetwork.ALLOWED_FACT_TYPES

    def test_allowed_categories(self):
        """Test category whitelist."""
        from src.services.memory.fact_network import FactNetwork

        assert "work" in FactNetwork.ALLOWED_CATEGORIES
        assert "personal" in FactNetwork.ALLOWED_CATEGORIES
        assert "health" in FactNetwork.ALLOWED_CATEGORIES


class TestObservationNetworkValidation:
    """Test SQL injection prevention in ObservationNetwork."""

    def test_allowed_entity_types(self):
        """Test entity type whitelist."""
        from src.services.memory.observation_network import ObservationNetwork

        assert "person" in ObservationNetwork.ALLOWED_ENTITY_TYPES
        assert "app" in ObservationNetwork.ALLOWED_ENTITY_TYPES
        assert "project" in ObservationNetwork.ALLOWED_ENTITY_TYPES


class TestMemSchedulerValidation:
    """Test SQL injection prevention in MemScheduler."""

    def test_type_to_table_mapping(self):
        """Test memory type to table mapping."""
        from src.services.memory.memory_scheduler import MemScheduler

        assert MemScheduler.TYPE_TO_TABLE["fact"] == "memory_facts"
        assert MemScheduler.TYPE_TO_TABLE["experience"] == "memory_experiences"
        assert MemScheduler.TYPE_TO_TABLE["entity"] == "memory_entities"
        assert MemScheduler.TYPE_TO_TABLE["belief"] == "memory_beliefs"

    def test_allowed_tables(self):
        """Test allowed tables frozenset."""
        from src.services.memory.memory_scheduler import MemScheduler

        assert "memory_facts" in MemScheduler.ALLOWED_TABLES
        assert "memory_experiences" in MemScheduler.ALLOWED_TABLES
        assert "memory_entities" in MemScheduler.ALLOWED_TABLES
        assert "memory_beliefs" in MemScheduler.ALLOWED_TABLES


class TestBeliefNetworkSanitization:
    """Test LIKE pattern sanitization in BeliefNetwork."""

    def test_sanitize_for_like_escapes_percent(self):
        """Test that % is escaped."""
        from src.services.memory.belief_network import BeliefNetwork

        db_mock = MagicMock()
        network = BeliefNetwork(db_mock, "test")
        result = network._sanitize_for_like("test%injection")
        assert "\\%" in result

    def test_sanitize_for_like_escapes_underscore(self):
        """Test that _ is escaped."""
        from src.services.memory.belief_network import BeliefNetwork

        db_mock = MagicMock()
        network = BeliefNetwork(db_mock, "test")
        result = network._sanitize_for_like("test_injection")
        assert "\\_" in result

    def test_sanitize_for_like_escapes_backslash(self):
        """Test that \\ is escaped."""
        from src.services.memory.belief_network import BeliefNetwork

        db_mock = MagicMock()
        network = BeliefNetwork(db_mock, "test")
        result = network._sanitize_for_like("test\\injection")
        assert "\\\\" in result


class TestMemoryModels:
    """Test memory database models."""

    def test_memory_fact_import(self):
        """Test MemoryFact model can be imported."""
        from src.db.models.memory import MemoryFact

        assert MemoryFact is not None

    def test_memory_experience_import(self):
        """Test MemoryExperience model can be imported."""
        from src.db.models.memory import MemoryExperience

        assert MemoryExperience is not None

    def test_memory_entity_import(self):
        """Test MemoryEntity model can be imported."""
        from src.db.models.memory import MemoryEntity

        assert MemoryEntity is not None

    def test_memory_belief_import(self):
        """Test MemoryBelief model can be imported."""
        from src.db.models.memory import MemoryBelief

        assert MemoryBelief is not None

    def test_memory_topic_import(self):
        """Test MemoryTopic model can be imported."""
        from src.db.models.memory import MemoryTopic

        assert MemoryTopic is not None

    def test_memory_link_import(self):
        """Test MemoryLink model can be imported."""
        from src.db.models.memory import MemoryLink

        assert MemoryLink is not None

    def test_memory_cube_import(self):
        """Test MemoryCube model can be imported."""
        from src.db.models.memory import MemoryCube

        assert MemoryCube is not None


class TestMemoryManagerIntegration:
    """Integration tests for MemoryManager."""

    @pytest.mark.asyncio
    async def test_memory_manager_initialization(self):
        """Test MemoryManager can be initialized."""
        from src.services.memory import MemoryManager

        db_mock = AsyncMock()
        manager = MemoryManager(db_mock, "test_session")
        assert manager.session_id == "test_session"

    @pytest.mark.asyncio
    async def test_get_memory_stats(self):
        """Test memory stats retrieval."""
        from src.services.memory import MemoryManager

        db_mock = AsyncMock()

        # Mock execute to return scalar results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        db_mock.execute = AsyncMock(return_value=mock_result)

        manager = MemoryManager(db_mock, "test_session")
        stats = await manager.get_memory_stats()

        assert "session_id" in stats
        assert stats["session_id"] == "test_session"
