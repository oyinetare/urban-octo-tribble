from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


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
        """
        Test /health/ready when dependencies are healthy.
        Mock redis_service.ping to return True.
        """
        with patch("app.core.redis_service.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True

            response = await client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["services"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_readiness_check_failure(self, client: AsyncClient):
        """
        Test /health/ready when Redis is down.
        Must return 503 Service Unavailable.
        """
        with patch("app.core.redis_service.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = False

            response = await client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unready"
            assert data["services"]["redis"] == "down"
