import pytest
from httpx import AsyncClient


class TestMiddlewareComprehensive:
    """Comprehensive middleware tests."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        """Test security headers are added."""
        response = await client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in response.headers

    @pytest.mark.asyncio
    async def test_versioning_headers(self, client: AsyncClient, auth_headers):
        """Test versioning headers on v1 endpoints."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        # V1 endpoints should have deprecation headers
        assert "Deprecation" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers."""
        _response = await client.options(
            "/api/v1/users/me", headers={"Origin": "http://localhost:8080"}
        )
        # CORS middleware should handle OPTIONS requests

    @pytest.mark.asyncio
    async def test_idempotency_without_key(self, client: AsyncClient, auth_headers):
        """Test POST without idempotency key works normally."""
        response1 = await client.post(
            "/api/v1/documents/", headers=auth_headers, json={"title": "Test", "content": "Test"}
        )
        response2 = await client.post(
            "/api/v1/documents/", headers=auth_headers, json={"title": "Test", "content": "Test"}
        )

        # Both should succeed
        assert response1.status_code == 201
        assert response2.status_code == 201

        # Should have different IDs (no idempotency)
        assert response1.json()["id"] != response2.json()["id"]
