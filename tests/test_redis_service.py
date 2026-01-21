from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from app.core.redis import RedisService


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Reset the Singleton instance before each test."""
    RedisService._instance = None
    RedisService._redis_client = None
    yield


@pytest_asyncio.fixture
async def mock_redis_service():
    """Provides a RedisService instance backed by FakeRedis."""
    service = RedisService()
    # Manually inject FakeRedis to avoid real network calls
    service._redis_client = FakeRedis(decode_responses=True)
    yield service
    await service.close()


@pytest.mark.asyncio
class TestRedisService:
    async def test_singleton_pattern(self):
        """Verify that multiple instantiations return the same object."""
        service1 = RedisService()
        service2 = RedisService()
        assert service1 is service2

    async def test_initialize_success(self):
        """Test successful initialization with a mocked ping."""
        service = RedisService()
        with patch("redis.asyncio.Redis.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True
            await service.initialize()
            assert service.is_available is True
            assert service.client is not None

    async def test_initialize_failure(self):
        """Test that failure to connect doesn't crash the app."""
        service = RedisService()
        with patch("redis.asyncio.Redis.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.side_effect = Exception("Connection Refused")
            await service.initialize()
            assert service.is_available is False
            assert service.client is None

    async def test_blacklist_token_flow(self, mock_redis_service):
        """Test blacklisting and checking token status."""
        token = "test-jwt-token"

        # Initially not blacklisted
        assert await mock_redis_service.is_token_blacklisted(token) is False

        # Blacklist it
        success = await mock_redis_service.blacklist_token(token, expires_in=10)
        assert success is True

        # Now it should be blacklisted
        assert await mock_redis_service.is_token_blacklisted(token) is True

    async def test_rate_limit_state(self, mock_redis_service):
        """Test storing and retrieving rate limit metadata."""
        user_id = 123
        tokens = 5
        last_refill = 1715600000.0

        # Set state
        success = await mock_redis_service.set_rate_limit_state(user_id, tokens, last_refill)
        assert success is True

        # Get state
        state = await mock_redis_service.get_rate_limit_state(user_id)
        assert state["tokens"] == str(tokens)  # Redis returns strings in decode_mode
        assert float(state["last_refill"]) == last_refill

    async def test_idempotency_cache(self, mock_redis_service):
        """Test idempotent response caching."""
        key = "idemp:req:001"
        data = {"status": "completed", "data": "payload"}

        # Set
        await mock_redis_service.set_idempotent_response(key, data)

        # Get
        cached = await mock_redis_service.get_idempotent_response(key)
        assert cached == data

    async def test_operations_when_redis_down(self):
        """Ensure methods return False/None gracefully if Redis is unavailable."""
        service = RedisService()  # No initialization
        assert await service.blacklist_token("abc", 10) is False
        assert await service.get_rate_limit_state(1) is None
        assert await service.is_token_blacklisted("abc") is False
