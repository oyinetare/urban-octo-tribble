from collections.abc import Awaitable
from typing import cast

import redis.asyncio as redis

from app.core.config import get_settings

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


# Global singleton instance
redis_service = RedisService()
