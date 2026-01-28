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
        # 1. Patch the instance inside the services container
        with patch.object(services.redis, "ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True

            response = await client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            # 2. Match your new key 'dependencies' and boolean value
            assert data["dependencies"]["redis"] is True

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
