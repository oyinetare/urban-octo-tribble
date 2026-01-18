import json
import time
from collections.abc import Awaitable
from typing import cast

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()


class RedisService:
    """
    Centralized Redis service using Singleton pattern.

    Provides a single Redis connection pool shared across the application.
    Used by:
    - Token blacklisting (authentication)
    - Rate limiting
    - Caching
    - Session storage
    - Webhook task queue
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
            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True,
                max_connections=50,  # Connection pool size
                socket_connect_timeout=5,
                socket_keepalive=True,
            )

            # Test connection
            is_connected = await cast(Awaitable[bool], self._redis_client.ping())

            if not is_connected:
                raise ConnectionError("Redis ping failed")

            if not is_connected:
                raise ConnectionError("Redis ping failed")

            print("✅ Redis connected successfully")
            print(f"   Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            print("   Pool size: 50 connections")

        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("   Redis-dependent features will be disabled")
            self._redis_client = None
            # Don't raise - allow app to continue without Redis

    async def close(self):
        """Close Redis connection pool."""
        if self._redis_client:
            await self._redis_client.close()
            print("✅ Redis connection closed")
            self._redis_client = None

    @property
    def client(self) -> redis.Redis | None:
        """Get Redis client instance."""
        return self._redis_client

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._redis_client is not None

    # === Token Blacklist Operations ===

    async def blacklist_token(self, token: str, expires_in: int) -> bool:
        """Add token to blacklist with expiration."""
        if not self._redis_client:
            return False

        try:
            await self._redis_client.setex(f"blacklist:{token}", expires_in, "1")
            return True
        except Exception as e:
            print(f"Failed to blacklist token: {e}")
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
            print(f"Failed to get rate limit state: {e}")
            return None

    async def set_rate_limit_state(
        self, user_id, tokens, last_refill: float, ttl: int = 60
    ) -> bool:
        if not self._redis_client:
            return False

        try:
            key = f"rate_limit:{user_id}"
            await cast(
                Awaitable[int],
                self._redis_client.hset(
                    key, mapping={"tokens": tokens, "last_refill": last_refill}
                ),
            )
            await self._redis_client.expire(key, ttl)
            return True

        except Exception as e:
            print(f"Failed to set rate limit state: {e}")
            return False

    # === Webhook Queue Operations ===

    async def enqueue_webhook(self, payload: dict) -> bool:
        """
        Add webhook to processing queue.

        Args:
            payload: Webhook payload dict

        Returns:
            True if successful
        """
        if not self._redis_client:
            return False

        try:
            payload_json = json.dumps(payload)
            await cast(Awaitable[int], self._redis_client.lpush("queue:webhooks", payload_json))
            return True
        except Exception as e:
            print(f"Failed to enqueue webhook: {e}")
            return False

    async def enqueue_webhook_delayed(self, payload: dict, delay_seconds: int) -> bool:
        """
        Add webhook to delayed queue (for retries with exponential backoff).

        Uses Redis sorted set where score = timestamp when item should be processed.

        Args:
            payload: Webhook payload dict
            delay_seconds: Delay before processing

        Returns:
            True if successful
        """
        if not self._redis_client:
            return False

        try:
            payload_json = json.dumps(payload)
            process_at = time.time() + delay_seconds
            await self._redis_client.zadd("queue:webhooks:delayed", {payload_json: process_at})
            return True
        except Exception as e:
            print(f"Failed to enqueue delayed webhook: {e}")
            return False

    async def dequeue_webhook(self, timeout: int = 1) -> str | None:
        """
        Remove and return webhook from queue (blocking with timeout).

        This first checks the delayed queue for any items ready to process,
        then falls back to the main queue.

        Args:
            timeout: Blocking timeout in seconds

        Returns:
            JSON string of webhook payload, or None if queue empty
        """
        if not self._redis_client:
            return None

        try:
            # First, check delayed queue for items ready to process
            now = time.time()
            delayed_items = await self._redis_client.zrangebyscore(
                "queue:webhooks:delayed", min=0, max=now, start=0, num=1
            )

            if delayed_items:
                # Move from delayed queue to main queue
                item = delayed_items[0]
                await self._redis_client.zrem("queue:webhooks:delayed", item)
                return item

            # Then check main queue with blocking pop
            result = await cast(
                Awaitable[list], self._redis_client.brpop(["queue:webhooks"], timeout=timeout)
            )
            if result:
                _key, payload_json = result
                return payload_json
            return None

        except Exception as e:
            print(f"Failed to dequeue webhook: {e}")
            return None

    async def get_queue_size(self) -> dict[str, int]:
        """
        Get current queue sizes.

        Returns:
            Dict with 'immediate' and 'delayed' queue sizes
        """
        if not self._redis_client:
            return {"immediate": 0, "delayed": 0}

        try:
            immediate = await cast(Awaitable[int], self._redis_client.llen("queue:webhooks"))
            delayed = await self._redis_client.zcard("queue:webhooks:delayed")
            return {"immediate": immediate, "delayed": delayed}
        except Exception:
            return {"immediate": 0, "delayed": 0}

    # === Cache Operations ===

    async def get_cache(self, key: str) -> str | None:
        """Get cached value."""
        if not self._redis_client:
            return None

        try:
            return await self._redis_client.get(f"cache:{key}")
        except Exception:
            return None

    async def set_cache(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set cached value with TTL."""
        if not self._redis_client:
            return False

        try:
            await self._redis_client.setex(f"cache:{key}", ttl, value)
            return True
        except Exception:
            return False

    async def delete_cache(self, key: str) -> bool:
        """Delete cached value."""
        if not self._redis_client:
            return False

        try:
            await self._redis_client.delete(f"cache:{key}")
            return True
        except Exception:
            return False

    # === Session Operations  ===

    async def create_session(self, session_id: str, data: dict, ttl: int = 86400) -> bool:
        """Create user session."""
        if not self._redis_client:
            return False

        try:
            key = f"session:{session_id}"
            await self._redis_client.setex(key, ttl, json.dumps(data))
            return True
        except Exception:
            return False

    async def get_session(self, session_id: str) -> dict | None:
        """Get user session."""
        if not self._redis_client:
            return None

        try:
            key = f"session:{session_id}"
            data = await self._redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None


# Global singleton instance
redis_service = RedisService()
