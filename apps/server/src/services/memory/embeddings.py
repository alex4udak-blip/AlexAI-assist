"""
Embedding Service for Memory System.
Uses sentence-transformers for local embeddings (MiniLM-L6-v2).
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Lazy load sentence-transformers to avoid import overhead
_model = None


def _get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            _model = "unavailable"
    return _model


class EmbeddingService:
    """
    Service for generating text embeddings.
    Uses MiniLM-L6-v2 (384 dimensions) for efficient local embeddings.
    """

    EMBEDDING_DIM = 384

    def __init__(self) -> None:
        self._model = None

    @property
    def model(self):
        """Lazy load model on first use."""
        if self._model is None:
            self._model = _get_model()
        return self._model

    @property
    def is_available(self) -> bool:
        """Check if embedding service is available."""
        return self.model != "unavailable" and self.model is not None

    def embed(self, text: str) -> list[float] | None:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats (384 dimensions) or None if unavailable
        """
        if not self.is_available:
            return None

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (or None for failed items)
        """
        if not self.is_available:
            return [None] * len(texts)

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)

    def similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            dot = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def to_pgvector_str(self, embedding: list[float]) -> str:
        """
        Convert embedding to PostgreSQL vector string format.

        Args:
            embedding: List of floats

        Returns:
            String in format '[0.1,0.2,0.3,...]'
        """
        return "[" + ",".join(str(x) for x in embedding) + "]"

    # Whitelist of allowed tables for embedding storage
    ALLOWED_TABLES = frozenset({
        "memory_facts",
        "memory_experiences",
        "memory_entities",
        "memory_beliefs",
        "memory_topics",
    })

    async def embed_and_store(
        self,
        text: str,
        table_name: str,
        record_id: str,
        db_session: Any,
    ) -> bool:
        """
        Generate embedding and store in database.

        Args:
            text: Text to embed
            table_name: Table to update (must be in ALLOWED_TABLES)
            record_id: Record ID to update
            db_session: Database session

        Returns:
            True if successful
        """
        # Validate table name against whitelist
        if table_name not in self.ALLOWED_TABLES:
            logger.error(f"Invalid table name for embedding: {table_name}")
            return False

        embedding = self.embed(text)
        if embedding is None:
            return False

        try:
            from sqlalchemy import text as sql_text

            vector_str = self.to_pgvector_str(embedding)
            # Use parameterized query - table name is safe (whitelisted)
            # record_id and vector_str are parameterized
            await db_session.execute(
                sql_text(
                    f"""
                    UPDATE {table_name}
                    SET embedding_vector = :vector::vector
                    WHERE id = :record_id::uuid
                    """
                ).bindparams(vector=vector_str, record_id=record_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False


# Global instance
embedding_service = EmbeddingService()
