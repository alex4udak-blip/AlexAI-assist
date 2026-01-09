"""Caching utilities with Redis and in-memory fallback."""

import json
import logging
import time
from typing import Any

import redis.asyncio as redis

from src.core.config import settings

logger = logging.getLogger(__name__)


class CacheEntry:
    """In-memory cache entry with TTL."""

    def __init__(self, value: Any, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expires_at


class Cache:
    """Cache with Redis backend and in-memory fallback."""

    def __init__(self) -> None:
        self._redis_client: redis.Redis | None = None
        self._memory_store: dict[str, CacheEntry] = {}
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize Redis connection if not already done."""
        if self._initialized:
            return

        try:
            self._redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis_client.ping()
            logger.info("Cache using Redis backend")
        except Exception as e:
            logger.warning(f"Redis not available for caching, using in-memory fallback: {e}")
            self._redis_client = None

        self._initialized = True

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        await self._ensure_initialized()

        if self._redis_client:
            try:
                value = await self._redis_client.get(key)
                if value is not None:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.warning(f"Redis get error, falling back to memory: {e}")
                return self._get_memory(key)
        else:
            return self._get_memory(key)

    def _get_memory(self, key: str) -> Any | None:
        """Get value from in-memory cache."""
        entry = self._memory_store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._memory_store[key]
            return None
        return entry.value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default 60)
        """
        await self._ensure_initialized()

        if self._redis_client:
            try:
                await self._redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.warning(f"Redis set error, falling back to memory: {e}")
                self._set_memory(key, value, ttl)
        else:
            self._set_memory(key, value, ttl)

    def _set_memory(self, key: str, value: Any, ttl: int) -> None:
        """Set value in in-memory cache."""
        expires_at = time.time() + ttl
        self._memory_store[key] = CacheEntry(value, expires_at)

        # Cleanup expired entries periodically (simple approach)
        self._cleanup_expired()

    def _cleanup_expired(self) -> None:
        """Remove expired entries from memory store."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._memory_store.items()
            if v.expires_at < current_time
        ]
        for key in expired_keys:
            del self._memory_store[key]

    async def delete(self, key: str) -> None:
        """Delete key from cache.

        Args:
            key: Cache key to delete
        """
        await self._ensure_initialized()

        if self._redis_client:
            try:
                await self._redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        # Always delete from memory too (in case of fallback)
        if key in self._memory_store:
            del self._memory_store[key]

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "timeline:*")
        """
        await self._ensure_initialized()

        if self._redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100,
                    )
                    if keys:
                        await self._redis_client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis delete_pattern error: {e}")

        # Delete matching keys from memory
        import fnmatch
        matching_keys = [
            k for k in self._memory_store.keys()
            if fnmatch.fnmatch(k, pattern)
        ]
        for key in matching_keys:
            del self._memory_store[key]


# Global cache instance
_cache: Cache | None = None


def get_cache() -> Cache:
    """Get global cache instance.

    Returns:
        Cache instance
    """
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
