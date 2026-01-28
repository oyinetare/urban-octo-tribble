from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.services import services


class TestHealthCheck:
    """Test updated health check endpoints (Liveness and Readiness)."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test the general root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to urban-octo-tribble API"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """
        Test /health/live.
        It should always return 200 as long as the app is running.
        """
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    @pytest.mark.asyncio
    async def test_readiness_check_success(self, client: AsyncClient):
        """Test /health/ready when dependencies are healthy."""
        # Mock Redis ping
        with patch.object(services.redis, "ping", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = True

            # ALSO mock the Vector Store check (check your health endpoint logic for the exact method)
            # Assuming your health logic calls services.vector_store.client.get_collections() or similar
            with patch.object(
                services.vector_store.async_client, "get_collections", new_callable=AsyncMock
            ) as mock_qdrant:
                mock_qdrant.return_value = True

                response = await client.get("/health/ready")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_readiness_check_failure(self, client: AsyncClient):
        """Test /health/ready when Redis is down."""
        # 1. Patch the instance inside the services container
        with patch.object(services.redis, "ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = False

            response = await client.get("/health/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unready"
            # 2. Match your new key 'dependencies' and boolean value
            assert data["dependencies"]["redis"] is False
