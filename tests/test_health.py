from unittest.mock import AsyncMock, MagicMock, patch

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

        # 1. Ensure the vector_store object exists so we can patch its client
        if services.vector_store is None:
            services.vector_store = MagicMock()

        # 2. Ensure the async_client exists on that service
        if (
            not hasattr(services.vector_store, "async_client")
            or services.vector_store.async_client is None
        ):
            services.vector_store.async_client = MagicMock()

        with (
            patch.object(services.redis, "ping", AsyncMock(return_value=True)),
            patch.object(
                services.vector_store.async_client,
                "get_collections",
                AsyncMock(return_value=MagicMock()),
            ),
            patch.object(services.storage, "file_exists", AsyncMock(return_value=True)),
        ):
            response = await client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["dependencies"]["vector_store"] is True

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
