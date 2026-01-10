"""
Embedding Service for Memory System.
Uses OpenAI text-embedding-3-small API.
"""

import logging
import os
from typing import Any

import httpx
import numpy as np

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Cache for pgvector availability
_pgvector_available: bool | None = None


async def check_pgvector_available(db_session: Any) -> bool:
    """Check if pgvector extension is available in the database."""
    global _pgvector_available
    if _pgvector_available is not None:
        return _pgvector_available

    try:
        from sqlalchemy import text as sql_text

        result = await db_session.execute(
            sql_text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        _pgvector_available = result.fetchone() is not None
        if not _pgvector_available:
            logger.warning("pgvector extension not installed. Vector search unavailable.")
    except Exception as e:
        logger.warning(f"Could not check pgvector availability: {e}")
        _pgvector_available = False

    return _pgvector_available


def is_pgvector_available() -> bool:
    """Return cached pgvector availability status."""
    global _pgvector_available
    return _pgvector_available if _pgvector_available is not None else False


class EmbeddingService:
    """Embedding service using OpenAI API."""

    EMBEDDING_DIM = EMBEDDING_DIM

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def is_available(self) -> bool:
        return bool(OPENAI_API_KEY)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    def embed(self, text: str) -> list[float] | None:
        """Sync embed - for backward compatibility."""
        if not self.is_available:
            return None

        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text[:30000],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            result: list[float] = data["data"][0]["embedding"]
            return result
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None

    async def embed_async(self, text: str) -> list[float] | None:
        """Async embed via OpenAI API."""
        if not self.is_available:
            logger.warning("OpenAI API key not configured")
            return None

        try:
            client = await self._get_client()
            response = await client.post(
                "/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text[:30000],
                },
            )
            response.raise_for_status()
            data = response.json()
            result: list[float] = data["data"][0]["embedding"]
            return result
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None

    async def embed_batch_async(self, texts: list[str]) -> list[list[float] | None]:
        """Batch embed via OpenAI API."""
        if not self.is_available or not texts:
            return [None] * len(texts)

        try:
            client = await self._get_client()
            response = await client.post(
                "/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "input": [t[:30000] for t in texts],
                },
            )
            response.raise_for_status()
            data = response.json()
            embeddings_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in embeddings_data]
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            return [None] * len(texts)

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Sync batch embed."""
        if not self.is_available or not texts:
            return [None] * len(texts)

        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": [t[:30000] for t in texts],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            embeddings_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in embeddings_data]
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            return [None] * len(texts)

    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calculate cosine similarity."""
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
            logger.error(f"Similarity error: {e}")
            return 0.0

    def to_pgvector_str(self, embedding: list[float]) -> str:
        """Convert to PostgreSQL vector string."""
        return "[" + ",".join(str(x) for x in embedding) + "]"

    # Whitelist of allowed tables for embedding storage
    ALLOWED_TABLES = frozenset({
        "memory_facts",
        "memory_experiences",
        "memory_entities",
        "memory_beliefs",
        "memory_topics",
        "memory_episodes",
    })

    async def embed_and_store(
        self,
        text: str,
        table_name: str,
        record_id: str,
        db_session: Any,
    ) -> bool:
        """Generate embedding and store in database."""
        # Check pgvector availability first
        if not await check_pgvector_available(db_session):
            return False

        # Validate table name against whitelist
        if table_name not in self.ALLOWED_TABLES:
            logger.error(f"Invalid table name for embedding: {table_name}")
            return False

        embedding = await self.embed_async(text)
        if embedding is None:
            return False

        try:
            from sqlalchemy import text as sql_text

            vector_str = self.to_pgvector_str(embedding)
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
