import pytest
from httpx import AsyncClient


class TestURLShorteningComprehensive:
    """Comprehensive URL shortening tests."""

    @pytest.mark.asyncio
    async def test_create_short_url(self, client: AsyncClient, auth_headers, test_document):
        """Test creating short URL."""
        response = await client.post(
            f"/api/v1/documents/share/{test_document.id}", headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert data["document_id"] == test_document.id
        assert data["clicks"] == 0
        assert "short_url" in data

    @pytest.mark.asyncio
    async def test_create_short_url_unauthorized(self, client: AsyncClient, session, test_document):
        """Test creating short URL for document you don't own."""
        from app.core import token_manager
        from app.models import User

        # Create another user
        other_user = User(
            email="other@test.com",
            username="otheruser",
            hashed_password=token_manager.get_password_hash("password"),
            role="user",
        )
        session.add(other_user)
        await session.commit()

        token = token_manager.create_access_token(
            data={"sub": other_user.username, "scopes": ["read", "write"]}
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(f"/api/v1/documents/share/{test_document.id}", headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_redirect_short_url(self, client: AsyncClient, auth_headers, test_document):
        """Test redirecting via short URL."""
        # Create short URL
        create_response = await client.post(
            f"/api/v1/documents/share/{test_document.id}", headers=auth_headers
        )
        short_code = create_response.json()["short_code"]

        # Test redirect
        response = await client.get(f"/d/{short_code}", follow_redirects=False)
        assert response.status_code == 301
        assert f"/documents/{test_document.id}" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_redirect_nonexistent_short_url(self, client: AsyncClient):
        """Test redirecting non-existent short URL."""
        response = await client.get("/d/nonexistent", follow_redirects=False)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_short_url_click_tracking(self, client: AsyncClient, auth_headers, test_document):
        """Test click tracking."""
        # Create short URL
        create_response = await client.post(
            f"/api/v1/documents/share/{test_document.id}", headers=auth_headers
        )
        short_code = create_response.json()["short_code"]

        # Click 3 times
        for _ in range(3):
            await client.get(f"/d/{short_code}", follow_redirects=False)

        # Check stats
        stats_response = await client.get(
            f"/api/v1/documents/{short_code}/stats", headers=auth_headers
        )
        assert stats_response.status_code == 200
        data = stats_response.json()
        assert data["clicks"] == 3

    @pytest.mark.asyncio
    async def test_get_stats_nonexistent(self, client: AsyncClient, auth_headers):
        """Test getting stats for non-existent short URL."""
        response = await client.get("/api/v1/documents/nonexistent/stats", headers=auth_headers)
        assert response.status_code == 404
