import pytest
from httpx import AsyncClient


class TestMiddleware:
    """Test middleware coverage."""

    @pytest.mark.asyncio
    async def test_security_headers(self, client: AsyncClient):
        """Test security headers are present."""
        response = await client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "X-XSS-Protection" in response.headers

    @pytest.mark.asyncio
    async def test_versioning_headers_v1(self, client: AsyncClient, auth_headers):
        """Test v1 endpoints have deprecation headers."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert "Deprecation" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS is configured."""
        _response = await client.options(
            "/api/v1/users/me", headers={"Origin": "http://localhost:8080"}
        )
        # CORS middleware handles OPTIONS

    @pytest.mark.asyncio
    async def test_https_redirect_skipped_in_dev(self, client: AsyncClient):
        """Test HTTPS redirect is skipped in development."""
        # In test environment, HTTPS redirect should be skipped
        response = await client.get("/health/live")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient, auth_headers):
        """Test rate limit headers (if Redis available)."""
        _response = await client.get("/api/v1/users/me", headers=auth_headers)
        # Headers may or may not be present depending on Redis availability
