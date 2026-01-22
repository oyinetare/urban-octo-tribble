import pytest
from httpx import AsyncClient


class TestURLShortening:
    """Test URL shortening functionality."""

    @pytest.mark.asyncio
    async def test_create_short_url(self, client: AsyncClient, auth_headers, test_document):
        """Test creating a short URL."""
        response = await client.post(
            f"/api/documents/share/{test_document.id}", headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert data["document_id"] == test_document.id
        assert data["clicks"] == 0

    @pytest.mark.asyncio
    async def test_redirect_short_url(self, client: AsyncClient, auth_headers, test_document):
        """Test redirecting via short URL."""
        # Create short URL
        create_response = await client.post(
            f"/api/documents/share/{test_document.id}", headers=auth_headers
        )
        short_code = create_response.json()["short_code"]

        # Test redirect
        response = await client.get(f"/d/{short_code}", follow_redirects=False)
        assert response.status_code == 301
        assert f"/documents/{test_document.id}" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_short_url_analytics(self, client: AsyncClient, auth_headers, test_document):
        """Test short URL click tracking."""
        # Create short URL
        create_response = await client.post(
            f"/api/documents/share/{test_document.id}", headers=auth_headers
        )
        short_code = create_response.json()["short_code"]

        # Click the short URL multiple times
        for _ in range(3):
            await client.get(f"/d/{short_code}", follow_redirects=False)

        # Check analytics
        stats_response = await client.get(
            f"/api/documents/{short_code}/stats", headers=auth_headers
        )
        assert stats_response.status_code == 200
        data = stats_response.json()
        assert data["clicks"] == 3
