"""
Centralized Redis service with integrated caching.

Provides:
- Token blacklisting (authentication)
- Rate limiting
- Response caching (RAG responses and embeddings)
- Session storage
- Metrics tracking
"""

import hashlib
import json
import logging
from collections.abc import Awaitable
from typing import Any, cast

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisService:
    """
    Centralized Redis service using Singleton pattern.

    Provides a single Redis connection pool shared across the application.
    """

    _instance: "RedisService | None" = None
    _redis_client: redis.Redis | None = None

    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """Initialize Redis connection pool."""
        if self._redis_client is not None:
            # Already initialized
            return

        try:
            # Use a connection pool explicitly to ensure reuse
            pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=0,
                decode_responses=True,
                max_connections=50,
            )

            self._redis_client = redis.Redis(connection_pool=pool)

            # Test connection
            is_connected = await cast(Awaitable[bool], self._redis_client.ping())

            if not is_connected:
                raise ConnectionError("Redis ping failed")

            logger.info("✅ Redis connected successfully")
            logger.info(f"   Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            logger.info("   Pool size: 50 connections")

        except Exception as e:
            logger.error(f"⚠️  Redis connection failed: {e}")
            logger.warning("   Redis-dependent features will be disabled")
            self._redis_client = None
            # Don't raise - allow app to continue without Redis

    async def close(self):
        """Close Redis connection pool."""
        if self._redis_client:
            await self._redis_client.aclose()
            logger.info("✅ Redis connection closed")
            self._redis_client = None

    @property
    def client(self) -> redis.Redis | None:
        """Get Redis client instance."""
        return self._redis_client

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._redis_client is not None

    async def ping(self) -> bool:
        """Actually pings Redis to verify the live connection."""
        if not self._redis_client:
            return False
        try:
            return await cast(Awaitable[bool], self._redis_client.ping())
        except Exception:
            return False

    # === Helper Methods ===

    def _generate_cache_key(self, prefix: str, *args: Any) -> str:
        """
        Generate a cache key from arguments.

        Args:
            prefix: Cache key prefix (e.g., 'rag_response', 'embedding')
            *args: Arguments to hash

        Returns:
            Cache key string
        """
        data = json.dumps(args, sort_keys=True, default=str)
        hash_value = hashlib.sha256(data.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_value}"

    # === Token Blacklist Operations ===

    async def blacklist_token(self, token: str, expires_in: int) -> bool:
        """Add token to blacklist with expiration."""
        if not self._redis_client:
            return False

        try:
            await self._redis_client.setex(f"blacklist:{token}", expires_in, "1")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        if not self._redis_client:
            return False

        try:
            result = await self._redis_client.exists(f"blacklist:{token}")
            return result > 0
        except Exception:
            return False

    # === Rate Limiting Operations ===

    async def get_rate_limit_state(self, user_id: int) -> dict | None:
        """Get current rate limit state for user."""
        if not self._redis_client:
            return None

        try:
            key = f"rate_limit:{user_id}"
            state = await cast(Awaitable[dict], self._redis_client.hgetall(key))
            return state if state else None
        except Exception as e:
            logger.error(f"Failed to get rate limit state: {e}")
            return None

    async def set_rate_limit_state(
        self, user_id: int, tokens: float, last_refill: float, ttl: int = 60
    ) -> bool:
        """Set rate limit state for user."""
        if not self._redis_client:
            return False

        try:
            key = f"rate_limit:{user_id}"
            await cast(
                Awaitable[int],
                self._redis_client.hset(
                    key, mapping={"tokens": str(tokens), "last_refill": str(last_refill)}
                ),
            )
            await self._redis_client.expire(key, ttl)
            return True

        except Exception as e:
            logger.error(f"Failed to set rate limit state: {e}")
            return False

    # === Idempotency Operations ===

    async def get_idempotent_response(self, key: str) -> dict | None:
        """Get cached idempotent response."""
        if not self._redis_client:
            return None

        try:
            result = await cast(Awaitable[dict], self._redis_client.hgetall(key))
            return result if result else None
        except Exception as e:
            logger.error(f"Failed to get idempotent response: {e}")
            return None

    async def set_idempotent_response(self, key: str, data: dict, ttl: int = 86400) -> bool:
        """Cache idempotent response."""
        if not self._redis_client:
            return False

        try:
            await cast(Awaitable[int], self._redis_client.hset(key, mapping=data))
            await self._redis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to set idempotent response: {e}")
            return False

    # === Cache Operations (RAG Responses) ===

    async def get_rag_response(
        self,
        query: str,
        document_id: int | None,
        max_chunks: int,
        min_score: float,
    ) -> dict[str, Any] | None:
        """
        Get cached RAG response.

        Args:
            query: User query
            document_id: Optional document filter
            max_chunks: Max chunks used
            min_score: Min similarity score

        Returns:
            Cached response dict or None if not found
        """
        if not self._redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(
                "rag_response",
                query.lower().strip(),
                document_id,
                max_chunks,
                min_score,
            )

            cached = await self._redis_client.get(cache_key)

            if cached:
                logger.info(f"✅ Cache HIT: RAG response for query: {query[:50]}...")
                return json.loads(cached)

            logger.debug(f"Cache MISS: RAG response for query: {query[:50]}...")
            return None

        except Exception as e:
            logger.error(f"Error reading RAG response from cache: {e}")
            return None

    async def set_rag_response(
        self,
        query: str,
        document_id: int | None,
        max_chunks: int,
        min_score: float,
        response: dict[str, Any],
        ttl: int = 3600,
    ) -> bool:
        """
        Cache RAG response.

        Args:
            query: User query
            document_id: Optional document filter
            max_chunks: Max chunks used
            min_score: Min similarity score
            response: Response to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if cached successfully
        """
        if not self._redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(
                "rag_response",
                query.lower().strip(),
                document_id,
                max_chunks,
                min_score,
            )

            await self._redis_client.setex(
                cache_key,
                ttl,
                json.dumps(response, default=str),
            )

            logger.debug(f"💾 Cached RAG response for: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error caching RAG response: {e}")
            return False

    # === Cache Operations (Embeddings) ===

    async def get_query_embedding(self, query: str) -> list[float] | None:
        """
        Get cached query embedding.

        Args:
            query: Query text

        Returns:
            Embedding vector or None if not found
        """
        if not self._redis_client:
            return None

        try:
            normalized_query = query.lower().strip()
            cache_key = self._generate_cache_key("embedding", normalized_query)

            cached = await self._redis_client.get(cache_key)

            if cached:
                logger.info(f"✅ Cache HIT: Embedding for query: {query[:50]}...")
                return json.loads(cached)

            logger.debug(f"Cache MISS: Embedding for query: {query[:50]}...")
            return None

        except Exception as e:
            logger.error(f"Error reading embedding from cache: {e}")
            return None

    async def set_query_embedding(
        self,
        query: str,
        embedding: list[float],
        ttl: int = 86400,
    ) -> bool:
        """
        Cache query embedding.

        Args:
            query: Query text
            embedding: Embedding vector
            ttl: Time to live in seconds (default: 24 hours)

        Returns:
            True if cached successfully
        """
        if not self._redis_client:
            return False

        try:
            normalized_query = query.lower().strip()
            cache_key = self._generate_cache_key("embedding", normalized_query)

            await self._redis_client.setex(
                cache_key,
                ttl,
                json.dumps(embedding),
            )

            logger.debug(f"💾 Cached embedding for: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error caching embedding: {e}")
            return False

    # === Cache Invalidation ===

    async def invalidate_document_cache(self, document_id: int) -> int:
        """
        Invalidate all cached responses for a document.

        Args:
            document_id: Document ID to invalidate

        Returns:
            Number of keys deleted
        """
        if not self._redis_client:
            return 0

        try:
            pattern = "rag_response:*"
            deleted = 0

            async for key in self._redis_client.scan_iter(match=pattern):
                try:
                    await self._redis_client.delete(key)
                    deleted += 1
                except Exception:
                    pass

            logger.info(f"🗑️  Invalidated {deleted} cache entries for document {document_id}")
            return deleted

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0

    async def clear_all_cache(self) -> int:
        """
        Clear all cached data (responses, embeddings, metrics).

        Returns:
            Number of keys deleted
        """
        if not self._redis_client:
            return 0

        try:
            deleted = 0
            async for key in self._redis_client.scan_iter():
                if key.startswith(("rag_response:", "embedding:", "metrics:")):
                    await self._redis_client.delete(key)
                    deleted += 1

            logger.info(f"🗑️  Cleared {deleted} cache entries")
            return deleted

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    # === Cache Statistics ===

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache metrics
        """
        if not self._redis_client:
            return {
                "enabled": False,
                "message": "Redis not available",
            }

        try:
            rag_responses = 0
            embeddings = 0

            async for key in self._redis_client.scan_iter():
                if key.startswith("rag_response:"):
                    rag_responses += 1
                elif key.startswith("embedding:"):
                    embeddings += 1

            return {
                "enabled": True,
                "rag_responses_cached": rag_responses,
                "embeddings_cached": embeddings,
                "response_ttl_seconds": 3600,
                "embedding_ttl_seconds": 86400,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "enabled": True,
                "error": str(e),
            }
