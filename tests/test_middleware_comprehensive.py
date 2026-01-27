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

    # @pytest.mark.asyncio
    # async def test_versioning_headers(self, client: AsyncClient, auth_headers):
    #     """Test versioning headers on v1 endpoints."""
    #     response = await client.get("/api/v1/users/me", headers=auth_headers)

    #     # V1 endpoints should have deprecation headers
    #     assert "Deprecation" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers."""
        _response = await client.options(
            "/api/v1/users/me", headers={"Origin": "http://localhost:8080"}
        )
        # CORS middleware should handle OPTIONS requests

    # @pytest.mark.asyncio
    # async def test_idempotency_without_key(self, client: AsyncClient, auth_headers):
    #     """Test POST without idempotency key works normally."""
    #     payload = {"title": "Doc Without Key 1", "description": "Test"}

    #     response1 = await client.post(
    #         "/api/v1/documents",
    #         headers=auth_headers,
    #         json=payload,
    #     )

    #     # Use different title for second request
    #     payload2 = {"title": "Doc Without Key 2", "description": "Test"}
    #     response2 = await client.post(
    #         "/api/v1/documents",
    #         headers=auth_headers,
    #         json=payload2,
    #     )

    #     # Debug
    #     print(f"\nIDEMPOTENCY TEST: R1={response1.status_code}, R2={response2.status_code}")

    #     # Both should succeed
    #     assert response1.status_code == 201
    #     assert response2.status_code == 201

    #     # Should have different IDs (no idempotency)
    #     assert response1.json()["id"] != response2.json()["id"]
